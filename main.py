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
# Load environment variables FIRST
# --------------------------------------------------

load_dotenv(dotenv_path=Path(__file__).parent / ".env")
FRONTEND_URL = os.getenv(
    "FRONTEND_URL",
    "http://localhost:5173"  # fallback for local dev
)


# AI roast logic
from roaster import generate_spotify_roast

# --------------------------------------------------
# App setup
# --------------------------------------------------

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
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
    scope="user-top-read user-read-recently-played playlist-read-private user-library-read",
)

# --------------------------------------------------
# Temporary in-memory roast store
# (Replace with Redis / DB in production)
# --------------------------------------------------

ROAST_STORE: dict[str, dict] = {}

# --------------------------------------------------
# Routes
# --------------------------------------------------

@app.get("/")
async def root():
    return RedirectResponse(url="/login")


@app.get("/login")
async def login():
    auth_url = sp_oauth.get_authorize_url()
    return RedirectResponse(auth_url)


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
        # Exchange code for token
        token_info = sp_oauth.get_access_token(code, as_dict=True)
        access_token = token_info["access_token"]

        sp = spotipy.Spotify(auth=access_token)

        # --------------------------------------------------
        # Fetch Spotify Data
        # --------------------------------------------------

        # Top tracks
        # Top tracks
top_tracks_data = sp.current_user_top_tracks(
    limit=10, time_range="medium_term"
)
tracks = top_tracks_data.get("items", [])

# Artist IDs (safe)
artist_ids = list({
    t["artists"][0]["id"]
    for t in tracks
    if t.get("artists")
})

artists_data = []
if artist_ids:
    artists_data = sp.artists(artist_ids).get("artists", [])

top_artists = []
for artist in artists_data[:5]:
    top_artists.append({
        "name": artist["name"],
        "image": artist["images"][0]["url"]
        if artist.get("images") else None,
    })


        # Genres
        all_genres = []
        for artist in artists_data:
            all_genres.extend(artist.get("genres", []))
        unique_genres = list(dict.fromkeys(all_genres))[:5]

        # Recently played tracks (with images)
        recent_data = sp.current_user_recently_played(limit=5)
        recent_tracks = []

        for r in recent_data["items"]:
            track = r["track"]
            recent_tracks.append({
                "name": track["name"],
                "image": track["album"]["images"][0]["url"]
                if track["album"]["images"] else None,
            })

        # Library size
        library_data = sp.current_user_saved_tracks(limit=1)
        total_saved = library_data["total"]

        # --------------------------------------------------
        # Build stats object
        # --------------------------------------------------

        stats = {
            "top_artists": top_artists,
            "recent_tracks": recent_tracks,
            "genres": unique_genres,
            "total_saved": total_saved,
        }

        # --------------------------------------------------
        # Generate AI Roast
        # --------------------------------------------------

        roast_text = generate_spotify_roast(stats)

        # --------------------------------------------------
        # Store roast (temporary)
        # --------------------------------------------------

        roast_id = str(uuid.uuid4())

        ROAST_STORE[roast_id] = {
            "roast": roast_text,
            "stats": stats,
        }

        # Redirect to frontend
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
# Local dev entry
# --------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        reload=True,
    )

