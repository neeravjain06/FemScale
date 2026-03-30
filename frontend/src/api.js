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
