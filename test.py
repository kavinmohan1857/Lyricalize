# Import necessary libraries
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from collections import Counter
import nltk
nltk.download('stopwords')
from nltk.corpus import stopwords
from configparser import ConfigParser
import os
import spotipy
import webbrowser
import requests
from spotipy.oauth2 import SpotifyOAuth
import uvicorn
from bs4 import BeautifulSoup

# FastAPI app setup
app = FastAPI()

# Allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend origin
    allow_methods=["*"],
    allow_headers=["*"],
)

# Genius and Spotify Setup using Config
config = ConfigParser()
config.read('config.cfg')

GENIUS_ACCESS_TOKEN = config.get('genius', 'client_access_token')
SPOTIFY_CLIENT_ID = config.get('spotify', 'client_id')
SPOTIFY_CLIENT_SECRET = config.get('spotify', 'client_secret')
REDIRECT_URI = "http://localhost:8000/callback"

HEADERS = {"Authorization": f"Bearer {GENIUS_ACCESS_TOKEN}"}

# Spotify OAuth setup
scope = "user-top-read"
sp_oauth = SpotifyOAuth(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scope=scope
)

# Function to search for lyrics using Genius API
def search_lyrics(title, artist):
    search_query = f"{title} {artist}"
    response = requests.get(
        "https://api.genius.com/search",
        headers=HEADERS,
        params={"q": search_query}
    )
    if response.status_code != 200:
        print(f"Error: {response.status_code}")
        return None

    hits = response.json()["response"]["hits"]
    for hit in hits:
        if artist.lower() in hit["result"]["primary_artist"]["name"].lower():
            song_url = hit["result"]["url"]
            lyrics = scrape_lyrics(song_url)
            return lyrics
    return None

# Function to scrape lyrics from a Genius song URL
def scrape_lyrics(song_url):
    try:
        response = requests.get(song_url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            lyrics_containers = soup.select('div[data-lyrics-container="true"]')
            lyrics = "\n".join([container.get_text() for container in lyrics_containers])
            return lyrics
    except Exception as e:
        print(f"Error scraping lyrics from {song_url}: {e}")
    return None

# Function to print word frequencies at startup
def print_word_frequencies():
    word_count = Counter()

    # Fetch top songs
    top_songs = [
        {"title": track["name"], "artist": track["artists"][0]["name"]}
        for track in sp.current_user_top_tracks(limit=50, time_range="long_term")["items"]
    ]

    def filter_stopwords(lyrics):
        stop_words = set(stopwords.words('english'))
        filtered_words = [
            word.lower().strip(".,!?\"'()[]") 
            for word in lyrics.split() 
            if word.lower().strip(".,!?\"'()[]") not in stop_words
        ]
        return filtered_words

    # Generate the word frequency map
    for song in top_songs:
        try:
            lyrics = search_lyrics(song["title"], song["artist"])
            if lyrics:
                filtered_words = filter_stopwords(lyrics)
                word_count.update(filtered_words)
                print(f"Processed: {song['title']} by {song['artist']}")
            else:
                print(f"Lyrics not found for: {song['title']} by {song['artist']}")
        except Exception as e:
            print(f"Error processing {song['title']} by {song['artist']}: {e}")

    # Print the top 10 words
    print("\nTop 10 Words in the Word Map:")
    for word, freq in word_count.most_common(100):
        print(f"{word}: {freq}")

# Function to reset and refresh Spotify OAuth token
def refresh_spotify_auth():
    global sp, sp_oauth

    # Get cached token or prompt for login
    token_info = sp_oauth.get_cached_token()

    # If no cached token exists, prompt user to log in
    if not token_info:
        print("No cached token found. Redirecting to Spotify login...")
        auth_url = sp_oauth.get_authorize_url()
        print(f"Opening the following URL in your browser: {auth_url}")
        webbrowser.open(auth_url)

        # Wait for user to paste the redirected URL
        response_url = input("Paste the URL you were redirected to here: ").strip()
        code = sp_oauth.parse_response_code(response_url)
        token_info = sp_oauth.get_access_token(code)

    # Set the new Spotify client
    sp = spotipy.Spotify(auth=token_info['access_token'])
    print("Spotify authentication refreshed.")

# Default root endpoint
@app.get("/")
def read_root():
    return {"message": "Welcome to the Lyricalize API! Use the /api endpoints to interact."}

if __name__ == "__main__":
    print("Please log in to Spotify...")

    # Refresh Spotify OAuth token if expired
    refresh_spotify_auth()

    # Print word frequencies at startup
    print("\nGenerating Word Frequency Map...")
    print_word_frequencies()

    # Start the server
    print("\nStarting the backend server...")
    uvicorn.run(app, host="127.0.0.1", port=8000)

# # Import necessary libraries
# from fastapi import FastAPI
# from fastapi.middleware.cors import CORSMiddleware
# from fastapi.responses import JSONResponse
# from collections import Counter
# import nltk
# nltk.download('stopwords')
# from nltk.corpus import stopwords
# from configparser import ConfigParser
# import os
# import spotipy
# import webbrowser
# import requests
# from spotipy.oauth2 import SpotifyOAuth
# import uvicorn
# from bs4 import BeautifulSoup

# # FastAPI app setup
# app = FastAPI()

# # Allow frontend requests
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["http://localhost:3000"],  # Frontend origin
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # Genius and Spotify Setup using Config
# config = ConfigParser()
# config.read('config.cfg')

# GENIUS_ACCESS_TOKEN = config.get('genius', 'client_access_token')
# SPOTIFY_CLIENT_ID = config.get('spotify', 'client_id')
# SPOTIFY_CLIENT_SECRET = config.get('spotify', 'client_secret')
# REDIRECT_URI = "http://localhost:8000/callback"

# HEADERS = {"Authorization": f"Bearer {GENIUS_ACCESS_TOKEN}"}

# # Spotify OAuth setup
# scope = "user-top-read"
# sp_oauth = SpotifyOAuth(
#     client_id=SPOTIFY_CLIENT_ID,
#     client_secret=SPOTIFY_CLIENT_SECRET,
#     redirect_uri=REDIRECT_URI,
#     scope=scope
# )
# sp = spotipy.Spotify(auth_manager=sp_oauth)

# # Function to search for lyrics using Genius API
# def search_lyrics(title, artist):
#     search_query = f"{title} {artist}"
#     response = requests.get(
#         "https://api.genius.com/search",
#         headers=HEADERS,
#         params={"q": search_query}
#     )
#     if response.status_code != 200:
#         print(f"Error: {response.status_code}")
#         return None

#     hits = response.json()["response"]["hits"]
#     for hit in hits:
#         if artist.lower() in hit["result"]["primary_artist"]["name"].lower():
#             song_url = hit["result"]["url"]
#             lyrics = scrape_lyrics(song_url)
#             return lyrics
#     return None

# # Function to scrape lyrics from a Genius song URL
# def scrape_lyrics(song_url):
#     try:
#         response = requests.get(song_url)
#         if response.status_code == 200:
#             soup = BeautifulSoup(response.text, "html.parser")
#             lyrics_containers = soup.select('div[data-lyrics-container="true"]')
#             lyrics = "\n".join([container.get_text() for container in lyrics_containers])
#             return lyrics
#     except Exception as e:
#         print(f"Error scraping lyrics from {song_url}: {e}")
#     return None

# # Function to print word frequencies at startup
# def print_word_frequencies():
#     word_count = Counter()

#     # Fetch top songs
#     top_songs = [
#         {"title": track["name"], "artist": track["artists"][0]["name"]}
#         for track in sp.current_user_top_tracks(limit=50, time_range="medium_term")["items"]
#     ]

#     def filter_stopwords(lyrics):
#         stop_words = set(stopwords.words('english'))
#         filtered_words = [
#             word.lower().strip(".,!?\"'()[]") 
#             for word in lyrics.split() 
#             if word.lower().strip(".,!?\"'()[]") not in stop_words
#         ]
#         return filtered_words

#     # Generate the word frequency map
#     for song in top_songs:
#         try:
#             lyrics = search_lyrics(song["title"], song["artist"])
#             if lyrics:
#                 filtered_words = filter_stopwords(lyrics)
#                 word_count.update(filtered_words)
#                 print(f"Processed: {song['title']} by {song['artist']}")
#             else:
#                 print(f"Lyrics not found for: {song['title']} by {song['artist']}")
#         except Exception as e:
#             print(f"Error processing {song['title']} by {song['artist']}: {e}")


#     # Print the top 10 words
#     print("\nTop 10 Words in the Word Map:")
#     for word, freq in word_count.most_common(100):
#         print(f"{word}: {freq}")

# # Default root endpoint
# @app.get("/")
# def read_root():
#     return {"message": "Welcome to the Lyricalize API! Use the /api endpoints to interact."}

# if __name__ == "__main__":
#     print("Please log in to Spotify...")

#     # Spotify OAuth login
#     auth_url = sp_oauth.get_authorize_url()
#     print(f"Opening the following URL in your browser: {auth_url}")
#     webbrowser.open(auth_url)

#     # Print word frequencies at startup
#     print("\nGenerating Word Frequency Map...")
#     print_word_frequencies()

#     # Start the server
#     print("\nStarting the backend server...")
#     uvicorn.run(app, host="127.0.0.1", port=8000)
