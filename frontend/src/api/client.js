import axios from "axios";

// Backend base URL. Set VITE_API_URL in the deployment environment (Vercel)
// to the production API origin (the Railway URL); falls back to the local
// dev server otherwise. It is a URL, not a secret - safe to ship in the
// client bundle.
const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 180000, // full pipeline takes ~30-60s including the LLM memo
});

export async function analyzeTicker(ticker) {
  try {
    const { data } = await api.post("/api/analyze", { ticker });
    return data;
  } catch (err) {
    const detail = err.response?.data?.detail;
    if (detail) throw new Error(detail);
    if (err.code === "ECONNABORTED") throw new Error("Analysis timed out. Please try again.");
    if (err.request && !err.response) {
      throw new Error(`Cannot reach the API at ${API_BASE_URL} — is the backend running and reachable?`);
    }
    throw new Error(err.message || "Analysis failed");
  }
}

export async function checkHealth() {
  const { data } = await api.get("/api/health");
  return data;
}
