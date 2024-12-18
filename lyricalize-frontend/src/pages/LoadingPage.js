import React, { useState, useEffect } from "react";
import axios from "axios";
import API_URL from "../config"; // Make sure API_URL points to the correct backend

function LoadingPage() {
  const [status, setStatus] = useState("Starting word map generation...");
  const [error, setError] = useState(null);
  const [topWords, setTopWords] = useState([]);

  useEffect(() => {
    const fetchWordFrequencies = async () => {
      try {
        // Update the status step-by-step
        setStatus("Fetching top songs from Spotify...");
        const response = await axios.post(`${API_URL}/api/word-frequencies`);

        // Process API response
        if (response.data && response.data.top_words) {
          setTopWords(response.data.top_words);
          setStatus("Word map successfully generated!");
        } else {
          throw new Error("No word data received from server.");
        }
      } catch (err) {
        console.error("Error fetching word frequencies:", err);
        setError("Failed to generate word map. Please try again.");
      }
    };

    fetchWordFrequencies();
  }, []);

  return (
    <div style={{ textAlign: "center", marginTop: "20%" }}>
      <h2>Generating your Word Map...</h2>
      {error ? (
        <div>
          <p style={{ color: "red" }}>{error}</p>
        </div>
      ) : (
        <div>
          <p>{status}</p>
          <div
            style={{
              margin: "20px auto",
              width: "50px",
              height: "50px",
              border: "5px solid #ccc",
              borderTop: "5px solid #1db954",
              borderRadius: "50%",
              animation: "spin 1s linear infinite",
            }}
          ></div>
        </div>
      )}

      {/* Display top words if ready */}
      {topWords.length > 0 && (
        <div>
          <h3>Top Words:</h3>
          <ul>
            {topWords.map(([word, freq], index) => (
              <li key={index}>
                {word}: {freq}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Loading animation styles */}
      <style>
        {`
          @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }
        `}
      </style>
    </div>
  );
}

export default LoadingPage;
