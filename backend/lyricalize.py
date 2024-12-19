from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from fastapi.responses import StreamingResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from collections import Counter
from nltk.corpus import stopwords
from bs4 import BeautifulSoup
from uuid import uuid4
import nltk
import os
import spotipy
import json
import requests
import asyncio
from spotipy.oauth2 import SpotifyOAuth

nltk.download("stopwords")

# FastAPI app setup
app = FastAPI()

# Session middleware setup
app.add_middleware(SessionMiddleware, secret_key="Hx7lVQ8c1PUqNejzMXe9km5bLaZNhNT2YR0GJq9eG0o")

# Serve React static files (if applicable)
app.mount("/static", StaticFiles(directory="build/static"), name="static")

# CORS Setup
origins = [
    "http://localhost:3000",  # Local testing
    "https://lyricalize-419bc3d24ee4.herokuapp.com",  # Deployed frontend URL
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Environment variables
GENIUS_ACCESS_TOKEN = os.getenv("GENIUS_ACCESS_TOKEN")
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI", "http://localhost:8000/callback")
HEADERS = {"Authorization": f"Bearer {GENIUS_ACCESS_TOKEN}"}

# Spotify OAuth setup (per user session)
def get_spotify_oauth(session_id: str):
    return SpotifyOAuth(
        client_id=SPOTIFY_CLIENT_ID,
        client_secret=SPOTIFY_CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope="user-top-read",
        cache_path=f".spotify_cache_{session_id}"  # Separate cache per session
    )

# Utility: Get Spotify Client
def get_spotify_client(session_id: str):
    sp_oauth = get_spotify_oauth(session_id)
    token_info = sp_oauth.get_cached_token()

    if not token_info or sp_oauth.is_token_expired(token_info):
        raise Exception("Spotify token expired or missing. Please log in again.")

    return spotipy.Spotify(auth=token_info["access_token"])

# Utility: Search for Lyrics
def search_lyrics(title, artist):
    search_query = f"{title} {artist}"
    response = requests.get(
        "https://api.genius.com/search",
        headers=HEADERS,
        params={"q": search_query},
    )
    if response.status_code != 200:
        return None

    hits = response.json().get("response", {}).get("hits", [])
    for hit in hits:
        if artist.lower() in hit["result"]["primary_artist"]["name"].lower():
            song_url = hit["result"]["url"]
            return scrape_lyrics(song_url)
    return None

# Utility: Scrape Lyrics
def scrape_lyrics(song_url):
    try:
        response = requests.get(song_url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            lyrics_containers = soup.select('div[data-lyrics-container="true"]')
            return "\n".join([container.get_text() for container in lyrics_containers])
    except Exception as e:
        print(f"Error scraping lyrics: {e}")
    return None

# Utility: Filter Stopwords
def filter_stopwords(lyrics):
    stop_words = set(stopwords.words("english"))
    return [
        word.lower().strip(".,!?\"'()[]")
        for word in lyrics.split()
        if word.lower().strip(".,!?\"'()[]") not in stop_words
    ]

# Endpoint: Stream Word Frequencies
@app.post("/api/word-frequencies")
async def get_word_frequencies(request: Request):
    session_id = request.session.get("session_id", "default_user")
    try:
        sp = get_spotify_client(session_id)
        top_songs = [
            {"title": track["name"], "artist": track["artists"][0]["name"]}
            for track in sp.current_user_top_tracks(limit=50, time_range="medium_term")["items"]
        ]

        async def word_stream():
            word_count = Counter()
            for idx, song in enumerate(top_songs, start=1):
                try:
                    lyrics = search_lyrics(song["title"], song["artist"])
                    if lyrics:
                        filtered_words = filter_stopwords(lyrics)
                        word_count.update(filtered_words)
                        yield f"data: {json.dumps({'song': song['title'], 'artist': song['artist'], 'progress': idx, 'total': len(top_songs)})}\n\n"
                    else:
                        yield f"data: {json.dumps({'song': song['title'], 'artist': song['artist'], 'progress': idx, 'error': 'No lyrics'})}\n\n"
                    await asyncio.sleep(0.1)
                except Exception as e:
                    yield f"data: {json.dumps({'song': song['title'], 'error': str(e)})}\n\n"

            yield f"data: {json.dumps({'status': 'complete', 'top_words': word_count.most_common(50)})}\n\n"

        return StreamingResponse(word_stream(), media_type="text/event-stream")
    except Exception as e:
        print(f"Error in /api/word-frequencies: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

# Spotify Login Endpoint
@app.get("/api/login")
def spotify_login(request: Request):
    # Generate a unique session ID if not already present
    if "session_id" not in request.session:
        request.session["session_id"] = str(uuid4())

    session_id = request.session["session_id"]
    sp_oauth = get_spotify_oauth(session_id)
    auth_url = sp_oauth.get_authorize_url()

    return {"auth_url": auth_url}

# Spotify Callback Endpoint
@app.get("/callback")
def callback(request: Request, code: str):
    session_id = request.session.get("session_id", "default_user")
    sp_oauth = get_spotify_oauth(session_id)

    try:
        # Exchange authorization code for an access token
        token_info = sp_oauth.get_access_token(code, as_dict=True)

        # Store token info in the session
        request.session["spotify_token"] = token_info

        # Redirect back to the frontend
        return RedirectResponse(url="https://lyricalize-419bc3d24ee4.herokuapp.com/")
    except Exception as e:
        print(f"Error in /callback: {e}")
        return JSONResponse(content={"error": f"Authentication failed: {str(e)}"}, status_code=500)

# Middleware to Ensure Session ID
@app.middleware("http")
async def ensure_session_id(request: Request, call_next):
    if "session_id" not in request.session:
        request.session["session_id"] = str(uuid4())
    response = await call_next(request)
    return response

# Catch-All Route for React Router
@app.get("/{full_path:path}")
def serve_react_catchall(full_path: str):
    if not full_path.startswith("api/"):  # Ensure this doesn’t conflict with API routes
        return RedirectResponse(url="/static/index.html")
    return {"error": f"Invalid path: {full_path}"}


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))  # Default to 8000 if PORT is not set
    uvicorn.run(app, host="0.0.0.0", port=port)
