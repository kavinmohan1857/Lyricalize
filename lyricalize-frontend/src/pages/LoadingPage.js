import React, { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import queryString from "query-string";

function LoadingPage() {
  const navigate = useNavigate();

  useEffect(() => {
    const fetchData = async () => {
      try {
        // Extract access token from URL query params
        const { access_token } = queryString.parse(window.location.search);

        if (!access_token) {
          throw new Error("Access token not found");
        }

        // Fetch word frequencies from the backend
        const response = await axios.post("http://localhost:8000/api/word-frequencies", null, {
          headers: { Authorization: `Bearer ${access_token}` },
        });

        // Save data and redirect to the word map page
        localStorage.setItem("wordData", JSON.stringify(response.data.top_words));
        navigate("/wordmap");
      } catch (error) {
        console.error("Error fetching word frequencies:", error);
      }
    };

    fetchData();
  }, [navigate]);

  return (
    <div style={{ textAlign: "center", marginTop: "20%" }}>
      <h2>Generating your Word Map...</h2>
      <div style={{ fontSize: "2em" }}>⏳</div>
    </div>
  );
}

export default LoadingPage;
