import os
import uuid
from typing import Optional

from fastapi import FastAPI, Query
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware

from dotenv import load_dotenv
from pathlib import Path

import spotipy
from spotipy.oauth2 import SpotifyOAuth

# --------------------------------------------------
# Load environment variables
# --------------------------------------------------

load_dotenv(dotenv_path=Path(__file__).parent / ".env")

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

# --------------------------------------------------
# App setup
# --------------------------------------------------

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        FRONTEND_URL,
        "http://localhost:3000",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------------------------
# Spotify OAuth
# --------------------------------------------------

sp_oauth = SpotifyOAuth(
    client_id=os.getenv("SPOTIPY_CLIENT_ID"),
    client_secret=os.getenv("SPOTIPY_CLIENT_SECRET"),
    redirect_uri=os.getenv("SPOTIPY_REDIRECT_URI"),
    scope="user-top-read user-read-recently-played user-library-read",
    cache_path=None,   
    show_dialog=True,
)

# --------------------------------------------------
# Roast logic
# --------------------------------------------------

from roaster import generate_spotify_roast

# --------------------------------------------------
# Temporary in-memory store
# NOTE: resets on backend restart (OK for MVP)
# --------------------------------------------------

ROAST_STORE: dict[str, dict] = {}

# --------------------------------------------------
# Routes
# --------------------------------------------------

@app.get("/")
async def root():
    return RedirectResponse("/login")


@app.get("/login")
async def login():
    return RedirectResponse(sp_oauth.get_authorize_url())


@app.get("/callback")
async def callback(
    code: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
):
    if error:
        return {"error": error}

    if not code:
        return {"error": "No authorization code provided"}

    try:
        # ---------------- AUTH ----------------
        token_info = sp_oauth.get_access_token(code, as_dict=True)
        sp = spotipy.Spotify(auth=token_info["access_token"])

        # ---------------- TOP ARTISTS (REAL DATA) ----------------
        top_artists_data = sp.current_user_top_artists(
            limit=10,
            time_range="medium_term"
        )

        artists_data = top_artists_data.get("items", [])

        top_artists = [
            {
                "name": artist["name"],
                "image": artist["images"][0]["url"]
                if artist.get("images") else None,
            }
            for artist in artists_data[:5]
        ]

        # ---------------- GENRES ----------------
        all_genres = []
        for artist in artists_data:
            all_genres.extend(artist.get("genres", []))

        unique_genres = list(dict.fromkeys(all_genres))[:5]

        # ---------------- RECENTLY PLAYED ----------------
        recent_data = sp.current_user_recently_played(limit=5)

        recent_tracks = []
        for item in recent_data.get("items", []):
            track = item.get("track")
            if track:
                recent_tracks.append({
                    "name": track["name"],
                    "image": track["album"]["images"][0]["url"]
                    if track.get("album") and track["album"].get("images")
                    else None,
                })

        # ---------------- LIBRARY SIZE ----------------
        library_data = sp.current_user_saved_tracks(limit=1)
        total_saved = library_data.get("total", 0)

        # ---------------- BUILD STATS ----------------
        stats = {
            "top_artists": top_artists,
            "recent_tracks": recent_tracks,
            "genres": unique_genres,
            "total_saved": total_saved,
        }

        # ---------------- AI ROAST ----------------
        roast_text = generate_spotify_roast(stats)

        roast_id = str(uuid.uuid4())
        ROAST_STORE[roast_id] = {
            "roast": roast_text,
            "stats": stats,
        }

        # ---------------- REDIRECT ----------------
        return RedirectResponse(
            url=f"{FRONTEND_URL}/result?rid={roast_id}"
        )

    except Exception as e:
        print("Callback error:", e)
        return {"error": "Something went wrong while generating the roast"}


@app.get("/api/roast/{roast_id}")
async def get_roast(roast_id: str):
    data = ROAST_STORE.get(roast_id)
    if not data:
        return {"error": "Roast not found or expired"}
    return data


# --------------------------------------------------
# Local dev
# --------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        reload=True,
    )

