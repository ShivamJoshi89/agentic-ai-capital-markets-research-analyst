import { useState } from "react";
import { AnimatePresence } from "framer-motion";
import Home from "./pages/Home.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import LoadingPipeline from "./components/LoadingPipeline.jsx";
import { analyzeTicker } from "./api/client.js";

export default function App() {
  const [phase, setPhase] = useState("idle"); // idle | loading | ready
  const [analysis, setAnalysis] = useState(null);
  const [lastTicker, setLastTicker] = useState(null);
  const [error, setError] = useState(null);

  // Used for both the initial Home-page search and dashboard ticker switches.
  // Keeping `analysis` around (rather than clearing it while loading) is what
  // lets the dashboard stay visible under the loading overlay during a switch.
  const handleAnalyze = async (ticker) => {
    setError(null);
    setPhase("loading");
    try {
      const data = await analyzeTicker(ticker);
      setAnalysis(data);
      setLastTicker(data.ticker);
      setPhase("ready");
    } catch (err) {
      setError(err.message);
      setPhase("idle");
    }
  };

  const handleReset = () => {
    setAnalysis(null);
    setError(null);
    setPhase("idle");
  };

  // Dashboard renders whenever we have data to show - independent of `phase` -
  // so a ticker switch keeps the previous results visible behind the overlay
  // instead of bouncing back to the Home page.
  const showDashboard = analysis !== null;

  return (
    <div className="min-h-screen bg-navy-900 text-white font-sans">
      <AnimatePresence mode="wait">
        {showDashboard ? (
          <Dashboard
            key="dashboard"
            data={analysis}
            onReset={handleReset}
            onChangeTicker={handleAnalyze}
            error={error}
            busy={phase === "loading"}
          />
        ) : (
          <Home
            key="home"
            onAnalyze={handleAnalyze}
            error={error}
            busy={phase === "loading"}
            lastTicker={lastTicker}
          />
        )}
      </AnimatePresence>
      <AnimatePresence>{phase === "loading" && <LoadingPipeline key="loader" />}</AnimatePresence>
    </div>
  );
}
