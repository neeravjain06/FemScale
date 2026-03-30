import React, { useState } from 'react';
import { submitJob } from './api';

const DEFAULT_CODE = `def handler(event):
    """Your function here — receives 'event' dict, returns result."""
    name = event.get("name", "World")
    return f"Hello, {name}!"
`;

export default function SubmitPage({ onNavigate, addToast }) {
  const [code, setCode] = useState(DEFAULT_CODE);
  const [timeout, setTimeout_] = useState(30);
  const [inputJson, setInputJson] = useState('{}');
  const [submitting, setSubmitting] = useState(false);

  const lineCount = code.split('\n').length;

  async function handleSubmit() {
    if (!code.trim()) {
      addToast('Code cannot be empty', 'error');
      return;
    }

    let parsedInput = {};
    try {
      parsedInput = JSON.parse(inputJson);
    } catch {
      addToast('Invalid JSON in input field', 'error');
      return;
    }

    setSubmitting(true);
    try {
      const res = await submitJob({ code, timeout_sec: timeout, input: parsedInput });
      addToast(`Job submitted: ${res.job_id.slice(0, 8)}`, 'success');
      onNavigate('result', res.job_id);
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || 'Submission failed';
      addToast(msg, 'error');
    } finally {
      setSubmitting(false);
    }
  }

  function handleKeyDown(e) {
    if (e.key === 'Tab') {
      e.preventDefault();
      const start = e.target.selectionStart;
      const end = e.target.selectionEnd;
      const val = e.target.value;
      setCode(val.substring(0, start) + '    ' + val.substring(end));
      window.requestAnimationFrame(() => {
        e.target.selectionStart = e.target.selectionEnd = start + 4;
      });
    }
  }

  return (
    <div className="fade-in-up">
      <div className="page-header-label">SYSTEM STATUS: ACTIVE</div>
      <h1 className="page-title">
        SUBMIT <span className="accent">FUNCTION</span>
      </h1>
      <p className="page-subtitle">
        Serverless Python. <strong>Beautifully Executed.</strong>
      </p>

      {/* Code Editor */}
      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        <div className="code-editor-wrap" style={{ border: 'none' }}>
          <div className="code-editor-header">
            <div className="code-editor-dots">
              <span></span><span></span><span></span>
            </div>
            <span>main.py // {lineCount} line{lineCount !== 1 ? 's' : ''}</span>
          </div>
          <textarea
            id="code-editor"
            className="code-textarea"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="# Write your Python code here..."
            spellCheck={false}
          />
        </div>
      </div>

      {/* Options row */}
      <div className="section-gap" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
        <div className="form-group" style={{ marginBottom: 0 }}>
          <label className="form-label" htmlFor="timeout-select">Timeout (seconds)</label>
          <select
            id="timeout-select"
            className="form-select"
            value={timeout}
            onChange={(e) => setTimeout_(Number(e.target.value))}
          >
            <option value={5}>5 seconds</option>
            <option value={10}>10 seconds</option>
            <option value={30}>30 seconds</option>
          </select>
        </div>

        <div className="form-group" style={{ marginBottom: 0 }}>
          <label className="form-label" htmlFor="input-json">Input JSON (optional)</label>
          <input
            id="input-json"
            className="form-input"
            type="text"
            value={inputJson}
            onChange={(e) => setInputJson(e.target.value)}
            placeholder='{"key": "value"}'
          />
        </div>
      </div>

      {/* Submit */}
      <div className="section-gap" style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        <button
          id="submit-btn"
          className="btn btn-outline-accent"
          onClick={handleSubmit}
          disabled={submitting || !code.trim()}
          style={{ minWidth: 200 }}
        >
          {submitting ? (
            <>
              <span className="spinner"></span>
              Submitting
            </>
          ) : (
            <>EXECUTE JOB</>
          )}
        </button>
        <span className="text-sm" style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
          {(code.length / 1024).toFixed(1)} KB / 50 KB
        </span>
      </div>
    </div>
  );
}
