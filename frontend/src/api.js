/**
 * FemScale API client — connects to all backend endpoints.
 * Backend runs on http://localhost:8000
 */

import axios from 'axios';

const API = axios.create({
  baseURL: '',
  headers: { 'Content-Type': 'application/json' },
  timeout: 15000,
});

// ─── POST /v1/jobs — Submit a new job ───
export async function submitJob({ code, timeout_sec = 30, input = {} }) {
  const res = await API.post('/v1/jobs', { code, timeout_sec, input });
  return res.data; // { job_id, status }
}

// ─── GET /v1/jobs/:id — Poll job result ───
export async function getJob(jobId) {
  const res = await API.get(`/v1/jobs/${jobId}`);
  return res.data;
}

// ─── GET /v1/jobs — List all jobs ───
export async function listJobs() {
  const res = await API.get('/v1/jobs');
  return res.data; // { jobs: [...] }
}

// ─── PUT /v1/jobs/:id — Update & rerun ───
export async function updateJob(jobId, newData) {
  const res = await API.put(`/v1/jobs/${jobId}`, newData);
  return res.data;
}

// ─── DELETE /v1/jobs/:id — Delete job ───
export async function deleteJob(jobId) {
  const res = await API.delete(`/v1/jobs/${jobId}`);
  return res.data;
}

// ─── GET /v1/metrics — Live platform metrics ───
export async function getMetrics() {
  const res = await API.get('/v1/metrics');
  return res.data;
}

// ─── GET /health — Health check ───
export async function healthCheck() {
  const res = await API.get('/health');
  return res.data;
}

// ═══════════════════════════════════════
// 🤖 AI TUTOR — CHAT API
// ═══════════════════════════════════════

// ─── POST /v1/chat — Non-streaming chat ───
export async function sendChatMessage({ message, code = '', session_id = null }) {
  const res = await API.post('/v1/chat', { message, code, session_id }, { timeout: 60000 });
  return res.data; // { session_id, response }
}

// ─── POST /v1/chat/stream — Streaming chat via SSE ───
export async function sendChatMessageStream({ message, code = '', session_id = null }, onChunk, onDone, onError) {
  try {
    const response = await fetch('/v1/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, code, session_id }),
    });

    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      throw new Error(errData.detail || `HTTP ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6).trim();
          if (data === '[DONE]') {
            if (onDone) onDone();
            return;
          }
          try {
            const text = JSON.parse(data);
            if (onChunk) onChunk(text);
          } catch (e) {
            // Skip malformed chunks
          }
        }
      }
    }

    if (onDone) onDone();
  } catch (err) {
    if (onError) onError(err);
  }
}

// ─── GET /v1/chat/sessions — List all sessions ───
export async function listChatSessions() {
  const res = await API.get('/v1/chat/sessions');
  return res.data; // { sessions: [...] }
}

// ─── GET /v1/chat/sessions/:id — Get session messages ───
export async function getChatSession(sessionId) {
  const res = await API.get(`/v1/chat/sessions/${sessionId}`);
  return res.data; // { session_id, title, messages }
}

// ─── DELETE /v1/chat/sessions/:id — Delete session ───
export async function deleteChatSession(sessionId) {
  const res = await API.delete(`/v1/chat/sessions/${sessionId}`);
  return res.data;
}
