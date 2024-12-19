from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, RedirectResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from collections import Counter
from pathlib import Path
from jose import JWTError, jwt
from uuid import uuid4
import os
import spotipy
import json
import requests
import asyncio
from spotipy.oauth2 import SpotifyOAuth
from bs4 import BeautifulSoup
import nltk

# Ensure stopwords are available
if not os.path.exists(os.path.join("nltk_data", "corpora", "stopwords")):
    nltk.download("stopwords")
from nltk.corpus import stopwords

# FastAPI app setup
app = FastAPI()

# CORS Setup
origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,https://lyricalize-419bc3d24ee4.herokuapp.com").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve React static files
app.mount("/static", StaticFiles(directory="build/static"), name="static")

# Environment variables
GENIUS_ACCESS_TOKEN = os.getenv("GENIUS_ACCESS_TOKEN")
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI", "http://localhost:8000/callback")
SECRET_KEY = os.getenv("SECRET_KEY", "default_secret_key")
ALGORITHM = "HS256"
HEADERS = {"Authorization": f"Bearer {GENIUS_ACCESS_TOKEN}"}

if not all([GENIUS_ACCESS_TOKEN, SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, REDIRECT_URI]):
    raise RuntimeError("Missing required environment variables.")

# Utility: Generate JWT Token
def create_jwt(data: dict, expires_in: int = 3600):
    from datetime import datetime, timedelta

    to_encode = data.copy()
    to_encode.update({"exp": datetime.utcnow() + timedelta(seconds=expires_in)})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# Utility: Decode JWT Token
def decode_jwt(token: str):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

# Spotify OAuth setup (per user session)
def get_spotify_oauth(user_id: str):
    return SpotifyOAuth(
        client_id=SPOTIFY_CLIENT_ID,
        client_secret=SPOTIFY_CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope="user-top-read",
        cache_path=f".spotify_cache_{user_id}"
    )

# Utility: Get Spotify Client
def get_spotify_client(user_id: str):
    sp_oauth = get_spotify_oauth(user_id)
    token_info = sp_oauth.get_cached_token()

    if not token_info:
        raise HTTPException(status_code=401, detail="Spotify token missing. Please log in.")
    if sp_oauth.is_token_expired(token_info):
        token_info = sp_oauth.refresh_access_token(token_info["refresh_token"])

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
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization header missing or invalid")

    token = auth_header.split(" ")[1]
    user = decode_jwt(token)

    try:
        sp = get_spotify_client(user["user_id"])
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
def spotify_login():
    user_id = str(uuid4())
    token = create_jwt({"user_id": user_id})

    sp_oauth = get_spotify_oauth(user_id)
    auth_url = sp_oauth.get_authorize_url()

    return {"auth_url": auth_url, "token": token}

# Spotify Callback Endpoint
@app.get("/callback")
def callback(request: Request, code: str):
    # Get the token from the frontend Authorization header
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization header missing or invalid")

    token = auth_header.split(" ")[1]
    user = decode_jwt(token)

    sp_oauth = get_spotify_oauth(user["user_id"])

    try:
        # Exchange authorization code for an access token
        sp_oauth.get_access_token(code, as_dict=True)

        # Redirect back to the frontend's loading page
        return RedirectResponse(url=f"{os.getenv('FRONTEND_URL')}/loadingpage")
    except Exception as e:
        print(f"Error in /callback: {e}")
        return JSONResponse(content={"error": f"Authentication failed: {str(e)}"}, status_code=500)

# Catch-all Route for React Router
@app.get("/{full_path:path}")
def serve_react_catchall(full_path: str):
    if not full_path.startswith("api/"):
        index_file = Path("build/index.html")
        if not index_file.exists():
            raise HTTPException(status_code=404, detail="React build/index.html not found.")
        return FileResponse(index_file)
    return {"error": f"Invalid path: {full_path}"}

if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
