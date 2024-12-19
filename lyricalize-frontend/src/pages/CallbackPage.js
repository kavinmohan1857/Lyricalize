import React, { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import API_URL from "../config";

function CallbackPage() {
  const navigate = useNavigate();

  useEffect(() => {
    const processCallback = async () => {
      const params = new URLSearchParams(window.location.search);
      const code = params.get("code");
      const token = localStorage.getItem("jwt_token"); // Retrieve stored JWT token

      if (code && token) {
        try {
          // Pass the code and token to your backend
          const response = await axios.get(`${API_URL}/callback`, {
            params: { code, token },
          });

          if (response.status === 200) {
            navigate("/loadingpage"); // Redirect to LoadingPage
          } else {
            console.error("Error processing callback:", response.data);
          }
        } catch (error) {
          console.error("Error in callback:", error);
        }
      } else {
        console.error("Authorization code or JWT token is missing");
      }
    };

    processCallback();
  }, [navigate]);

  return (
    <div style={{ textAlign: "center", marginTop: "20%" }}>
      <h2>Processing your login...</h2>
      <p>Please wait while we authenticate you with Spotify.</p>
    </div>
  );
}

export default CallbackPage;
