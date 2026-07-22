import { useState } from "react";
import { AnimatePresence } from "framer-motion";
import Home from "./pages/Home.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import LoadingPipeline from "./components/LoadingPipeline.jsx";
import { analyzeTicker } from "./api/client.js";

export default function App() {
  const [phase, setPhase] = useState("idle"); // idle | loading | ready
  const [analysis, setAnalysis] = useState(null);
  const [error, setError] = useState(null);

  const handleAnalyze = async (ticker) => {
    setError(null);
    setPhase("loading");
    try {
      const data = await analyzeTicker(ticker);
      setAnalysis(data);
      setPhase("ready");
    } catch (err) {
      setError(err.message);
      setPhase("idle");
    }
  };

  const handleReset = () => {
    setAnalysis(null);
    setPhase("idle");
  };

  return (
    <div className="min-h-screen bg-navy-900 text-white font-sans">
      <AnimatePresence mode="wait">
        {phase === "ready" && analysis ? (
          <Dashboard key="dashboard" data={analysis} onReset={handleReset} />
        ) : (
          <Home key="home" onAnalyze={handleAnalyze} error={error} busy={phase === "loading"} />
        )}
      </AnimatePresence>
      <AnimatePresence>{phase === "loading" && <LoadingPipeline key="loader" />}</AnimatePresence>
    </div>
  );
}
