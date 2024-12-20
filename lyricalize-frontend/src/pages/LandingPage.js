import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import API_URL from "../config"; // Import the API URL

function LandingPage() {
  const [spotifyAuthUrl, setSpotifyAuthUrl] = useState("");
  const navigate = useNavigate(); // Hook for navigation

  // Fetch the Spotify login URL and JWT token from the backend
  useEffect(() => {
    const fetchAuthUrl = async () => {
      try {
        const response = await axios.get(`${API_URL}/api/login`);
        setSpotifyAuthUrl(response.data.auth_url);

        // Store the JWT token in localStorage
        if (response.data.token) {
          localStorage.setItem("jwt_token", response.data.token);
          console.log("JWT token saved to localStorage:", response.data.token);
        } else {
          console.error("JWT token not received from backend");
        }
      } catch (error) {
        console.error("Error fetching Spotify auth URL:", error);
      }
    };
    fetchAuthUrl();
  }, []);

  const handleLogin = () => {
    if (spotifyAuthUrl) {
      window.location.href = spotifyAuthUrl; // Redirects user to the Spotify OAuth page
    } else {
      console.error("Spotify auth URL not available");
    }
  };

  return (
    <div style={{ textAlign: "center", marginTop: "20%" }}>
      <h2>Welcome to Lyricalize!</h2>
      <p>Analyze your most common words from Spotify song lyrics.</p>
      <button
        style={{
          padding: "10px 20px",
          fontSize: "1.2em",
          color: "#fff",
          backgroundColor: "#1db954",
          border: "none",
          borderRadius: "5px",
          cursor: "pointer",
          marginRight: "10px",
        }}
        onClick={handleLogin}
      >
        Login with Spotify
      </button>
      <button
        style={{
          padding: "10px 20px",
          fontSize: "1.2em",
          color: "#fff",
          backgroundColor: "#555",
          border: "none",
          borderRadius: "5px",
          cursor: "pointer",
        }}
        onClick={() => navigate("/details")} // Navigate to /details
      >
        About
      </button>
    </div>
  );
}

export default LandingPage;
