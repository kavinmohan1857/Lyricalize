from flask import Flask, request, jsonify
import requests
import os
from lyricalize import lyricalize  # Make sure you have your 'lyricalize.py' file ready to import

app = Flask(__name__)

@app.route('/api/lyricalize', methods=['GET'])
def get_lyrical_data():
    # Here you would have your Spotify API logic
    access_token = request.args.get('access_token')  # Make sure you are getting this token securely

    if not access_token:
        return jsonify({"error": "Access token is required"}), 400

    try:
        # Use your `lyricalize` function from 'lyricalize.py'
        lyrical_data = lyricalize(access_token)
        return jsonify(lyrical_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
