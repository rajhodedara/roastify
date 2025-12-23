import os
import requests

# --------------------------------------------------
# Config
# --------------------------------------------------

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# Best balance of humor + creativity
MODEL_NAME = "llama-3.3-70b-versatile"

if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY is not set")

# --------------------------------------------------
# Fallback
# --------------------------------------------------

def fallback_roast() -> str:
    return (
        "**Your Spotify is too powerful to be roasted right now.**\n\n"
        "- Even the AI needed a moment.\n"
        "- Consider this a temporary win.\n\n"
        "Final Verdict: Try again and face the music."
    )

# --------------------------------------------------
# Main Roast Generator
# --------------------------------------------------

def generate_spotify_roast(stats: dict) -> str:
    prompt = f"""
You are a ruthless, judgemental, and sarcastic music critic with a Gen-Z sense of humor. 
    Your job is to roast the user based on their Spotify listening habits.
    
    **Instructions for Analysis:**
    1. **Identify the Vibe:** Are they a "Sad Boi," an "NPC" (basic taste), a "Music Snob," or "Stuck in 2010"? 
    2. **Find the Hypocrisy:** Look at their 'Top Artists' vs. 'Recently Played'. Do they claim to like indie cool stuff but actually just binge Taylor Swift? Call it out.
    3. **The "Red Flag" Check:** If they listen to too much Drake, Radiohead, or obscure noise, diagnose their red flags.
    4. **Obsession Meter:** Look at 'Total Saved Tracks'. If low, they have commitment issues. If high, they are a hoarder.

    **Tone Guidelines:**
    - Use internet slang naturally (e.g., "Main Character Energy," "Touch grass," "Cringe," "Who hurt you?").
    - Be specific. Don't just say "Your music is bad." Say "This playlist smells like burnt vape juice and regret."
    - No emojis unless it adds comedic timing.

    **Required Output Format:**
    - **A brutal, bold one-liner summary of their existence.**
    - 3-5 bullet points starting with "-" that specifically roast the artists and genres provided.
    - A "Final Verdict" rating (e.g., "Final Verdict: 2/10 - You are banned from the aux cord forever.")
    Do NOT repeat ideas, sentences, or paragraphs.
    If you feel done, STOP writing.

    **Input Data:**
    - Top Artists (The evidence): {stats['top_artists']}
    - Top Genres (The personality): {stats['genres']}
    - Recently Played (The crime scene): {stats['recent_tracks']}
    - Total Saved (The baggage): {stats['total_saved']}
"""

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "system",
                "content": "You are a confident, witty roast comedian with great comedic timing."
            },
            {
                "role": "user",
                "content": prompt
            },
        ],
        # Slightly higher creativity for better jokes
        "temperature": 0.9,
        # Enough room for quality without looping
        "max_tokens":400 ,
    }

    try:
        response = requests.post(
            GROQ_API_URL,
            headers=headers,
            json=payload,
            timeout=15,
        )
        response.raise_for_status()

        return response.json()["choices"][0]["message"]["content"]

    except Exception as e:
        print("Groq error:", e)
        return fallback_roast()
