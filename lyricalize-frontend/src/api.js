// src/api.js

// Example API call for getting lyrical data
export const getLyricalData = async () => {
    try {
      const response = await fetch('YOUR_SPOTIFY_API_ENDPOINT_HERE'); // Replace with your Spotify API endpoint
      const data = await response.json();
      return data;
    } catch (error) {
      console.error('Error fetching lyrical data:', error);
    }
  };
  