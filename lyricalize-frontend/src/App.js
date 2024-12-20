import React from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import LandingPage from "./pages/LandingPage";
import CallbackPage from "./pages/CallbackPage";
import LoadingPage from "./pages/LoadingPage";
import DetailsPage from "./pages/DetailsPage"; // Import DetailsPage

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/callback" element={<CallbackPage />} />
        <Route path="/loadingpage" element={<LoadingPage />} />
        <Route path="/details" element={<DetailsPage />} /> {/* New route */}
      </Routes>
    </Router>
  );
}

export default App;

