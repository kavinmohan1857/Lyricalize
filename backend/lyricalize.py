from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse, RedirectResponse
from collections import Counter
from nltk.corpus import stopwords
from bs4 import BeautifulSoup
from fastapi.staticfiles import StaticFiles
import nltk
import os
import spotipy
import json
import requests
from spotipy.oauth2 import SpotifyOAuth
import uvicorn
import asyncio

nltk.download("stopwords")

# FastAPI app setup
app = FastAPI()

# Serve React static files
app.mount("/static", StaticFiles(directory="build/static"), name="static")

# CORS Setup
origins = [
    "http://localhost:3000",  # For local testing
    "https://lyricalize-419bc3d24ee4.herokuapp.com",  # Deployed frontend
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Type"],
)

# Environment variables
GENIUS_ACCESS_TOKEN = os.getenv("GENIUS_ACCESS_TOKEN")
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI", "http://localhost:8000/callback")
HEADERS = {"Authorization": f"Bearer {GENIUS_ACCESS_TOKEN}"}

# Spotify OAuth setup
scope = "user-top-read"
sp_oauth = SpotifyOAuth(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scope=scope,
    cache_path=".spotify_cache",
)

# Utility: Get Spotify Client
def get_spotify_client():
    token_info = sp_oauth.get_cached_token()
    if not token_info or sp_oauth.is_token_expired(token_info):
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

    hits = response.json()["response"]["hits"]
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
@app.get("/api/word-frequencies")
async def get_word_frequencies_get():
    return await get_word_frequencies()

# Endpoint: Stream Word Frequencies
@app.post("/api/word-frequencies")
async def get_word_frequencies():
    sp = get_spotify_client()
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
                    yield f"data: {json.dumps({'song': song['title'], 'progress': idx, 'total': len(top_songs)})}\n\n"
                else:
                    yield f"data: {json.dumps({'song': song['title'], 'progress': idx, 'error': 'No lyrics'})}\n\n"
                await asyncio.sleep(0.1)
            except Exception as e:
                yield f"data: {json.dumps({'song': song['title'], 'error': str(e)})}\n\n"

        yield f"data: {json.dumps({'status': 'complete', 'top_words': word_count.most_common(50)})}\n\n"

    return StreamingResponse(word_stream(), media_type="text/event-stream")

# Spotify Login Endpoint
@app.get("/api/login")
def spotify_login():
    auth_url = sp_oauth.get_authorize_url()
    return {"auth_url": auth_url}

# Spotify Callback Endpoint
@app.get("/callback")
def callback(code: str):
    try:
        token_info = sp_oauth.get_access_token(code, as_dict=True)
        access_token = token_info["access_token"]
        redirect_url = f"{os.getenv('FRONTEND_URL', 'http://localhost:3000')}/loading?access_token={access_token}"
        return RedirectResponse(url=redirect_url)
    except Exception as e:
        return {"error": f"Authentication failed: {str(e)}"}

# Catch-All Route for React Router
@app.get("/{full_path:path}")
def serve_react_catchall(full_path: str):
    if full_path.startswith("api/"):
        return {"detail": "Not Found"}
    return FileResponse("build/index.html")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))  # Default to 8000 if PORT is not set
    uvicorn.run(app, host="0.0.0.0", port=port)