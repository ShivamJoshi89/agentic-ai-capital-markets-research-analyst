import axios from "axios";

const api = axios.create({
  baseURL: "http://localhost:8000",
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
      throw new Error("Cannot reach the API at localhost:8000 — is the backend running? (python api.py)");
    }
    throw new Error(err.message || "Analysis failed");
  }
}

export async function checkHealth() {
  const { data } = await api.get("/api/health");
  return data;
}
