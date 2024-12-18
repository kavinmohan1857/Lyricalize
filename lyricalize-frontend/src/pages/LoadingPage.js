import React, { useState, useEffect } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom"; // Use for navigation
import API_URL from "../config";

function LoadingPage() {
  const [status, setStatus] = useState("Starting word map generation...");
  const [error, setError] = useState(null);
  const navigate = useNavigate(); // React Router hook for navigation

  useEffect(() => {
    const fetchWordFrequencies = async () => {
      try {
        setStatus("Fetching top songs from Spotify...");

        const response = await axios.post(`${API_URL}/api/word-frequencies`);

        if (response.data && response.data.top_words) {
          setStatus("Word map successfully generated!");

          // Redirect to the word map page after a delay
          setTimeout(() => {
            navigate("/word-map", { state: { data: response.data.top_words } });
          }, 1000); // Delay for better UX
        } else {
          throw new Error("No word data received from server.");
        }
      } catch (err) {
        console.error("Error fetching word frequencies:", err);
        setError("Failed to generate word map. Please try again.");
      }
    };

    fetchWordFrequencies();
  }, [navigate]);

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
