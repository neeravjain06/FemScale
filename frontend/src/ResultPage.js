import React, { useState, useEffect, useRef, useCallback } from 'react';
import { getJob, updateJob, deleteJob } from './api';

const TERMINAL_STATUSES = ['success', 'failed', 'timeout'];

export default function ResultPage({ jobId, onNavigate, addToast }) {
  const [job, setJob] = useState(null);
  const [loading, setLoading] = useState(true);
  const [polling, setPolling] = useState(true);
  const [editMode, setEditMode] = useState(false);
  const [editCode, setEditCode] = useState('');
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const intervalRef = useRef(null);

  const fetchJob = useCallback(async () => {
    try {
      const data = await getJob(jobId);
      setJob(data);
      setLoading(false);
      if (TERMINAL_STATUSES.includes(data.status)) {
        setPolling(false);
      }
    } catch (err) {
      setLoading(false);
      setPolling(false);
      addToast('Failed to fetch job', 'error');
    }
  }, [jobId, addToast]);

  useEffect(() => {
    fetchJob();
    intervalRef.current = setInterval(fetchJob, 2000);
    return () => clearInterval(intervalRef.current);
  }, [fetchJob]);

  useEffect(() => {
    if (!polling && intervalRef.current) {
      clearInterval(intervalRef.current);
    }
  }, [polling]);

  async function handleRerun() {
    setSaving(true);
    try {
      await updateJob(jobId, { code: editCode || job.code });
      setEditMode(false);
      setPolling(true);
      setLoading(true);
      addToast('Job re-queued', 'success');
      intervalRef.current = setInterval(fetchJob, 2000);
    } catch (err) {
      addToast('Update failed', 'error');
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    if (!window.confirm('Delete this job permanently?')) return;
    setDeleting(true);
    try {
      await deleteJob(jobId);
      addToast('Job deleted', 'info');
      onNavigate('submit');
    } catch (err) {
      addToast('Delete failed', 'error');
    } finally {
      setDeleting(false);
    }
  }

  if (loading && !job) {
    return (
      <div className="fade-in" style={{ textAlign: 'center', paddingTop: 80 }}>
        <div className="spinner spinner-lg spinner-accent" style={{ margin: '0 auto 16px' }}></div>
        <p className="text-muted" style={{ fontFamily: 'var(--font-mono)', textTransform: 'uppercase', letterSpacing: '0.08em', fontSize: '0.75rem' }}>Loading job data</p>
      </div>
    );
  }

  if (!job) {
    return (
      <div className="empty-state">
        <div className="empty-state-icon">[?]</div>
        <p className="empty-state-text">Job not found</p>
        <button className="btn btn-secondary mt-4" onClick={() => onNavigate('submit')}>
          Back to Submit
        </button>
      </div>
    );
  }

  const isTerminal = TERMINAL_STATUSES.includes(job.status);

  return (
    <div className="fade-in-up">
      {/* Header */}
      <div className="flex-between" style={{ marginBottom: 8 }}>
        <div>
          <div className="page-header-label">EXECUTION NODE: DELTA-9</div>
          <h1 className="page-title">
            TERMINAL <span className="accent">OUTPUT</span>
          </h1>
        </div>
        {isTerminal && (
          <div className="system-status">
            <span className="status-square"></span>
            SYSTEM STATUS: OPERATIONAL
          </div>
        )}
      </div>

      <div className="flex-row" style={{ marginBottom: 24 }}>
        <span className="mono text-muted" style={{ fontSize: '0.72rem' }}>{job.job_id}</span>
        <span className={`status-badge status-${job.status}`}>
          <span className="dot"></span>
          {job.status}
        </span>
        {polling && (
          <span className="poll-indicator">
            <span className="poll-dot"></span>
            polling
          </span>
        )}
      </div>

      {/* Action buttons */}
      <div className="flex-row" style={{ marginBottom: 20 }}>
        <button className="btn btn-secondary btn-sm" onClick={() => onNavigate('submit')}>
          Back
        </button>
        {isTerminal && (
          <>
            <button
              className="btn btn-secondary btn-sm"
              onClick={() => { setEditMode(!editMode); setEditCode(job.code || ''); }}
            >
              Edit & Rerun
            </button>
            <button className="btn btn-danger btn-sm" onClick={handleDelete} disabled={deleting}>
              {deleting ? '...' : 'Delete'}
            </button>
          </>
        )}
      </div>

      {/* Edit mode */}
      {editMode && (
        <div className="card section-gap fade-in" style={{ marginBottom: 20 }}>
          <div className="card-header">
            <span className="card-title">Edit Code</span>
            <div className="flex-row">
              <button className="btn btn-primary btn-sm" onClick={handleRerun} disabled={saving}>
                {saving ? <><span className="spinner"></span> Saving</> : 'Rerun'}
              </button>
              <button className="btn btn-secondary btn-sm" onClick={() => setEditMode(false)}>
                Cancel
              </button>
            </div>
          </div>
          <textarea
            className="code-textarea"
            style={{ borderRadius: 2, border: '1px solid var(--border-dim)', minHeight: 160 }}
            value={editCode}
            onChange={(e) => setEditCode(e.target.value)}
            spellCheck={false}
          />
        </div>
      )}

      {/* Main result layout — terminal + sidebar */}
      <div className="result-layout">
        {/* Left: Terminal output */}
        <div>
          {/* stdout */}
          <div className="card" style={{ padding: 0, overflow: 'hidden', marginBottom: 12 }}>
            <div className="code-editor-header">
              <div className="code-editor-dots">
                <span></span><span></span><span></span>
              </div>
              <span>STDOUT / STDERR</span>
            </div>
            <div style={{ padding: 20, background: 'var(--bg-terminal)', minHeight: 200 }}>
              {job.stdout ? (
                <div className="code-output" style={{ border: 'none', padding: 0 }}>{job.stdout}</div>
              ) : (
                <p style={{ fontFamily: 'var(--font-mono)', fontSize: '0.78rem', color: 'var(--text-dim)', fontStyle: 'italic' }}>No output</p>
              )}
              {job.stderr ? (
                <div className="code-output stderr" style={{ border: 'none', padding: 0, marginTop: 12 }}>{job.stderr}</div>
              ) : (
                <div className="code-output" style={{ border: 'none', padding: 0, marginTop: 12, color: 'var(--success)' }}>No Error Found</div>
              )}
            </div>
          </div>

          {/* Status bar */}
          <div className={`status-bar status-bar-${job.status}`}>
            <span className="status-bar-label">Task Status</span>
            <span className="status-bar-value">{job.status.toUpperCase()}</span>
          </div>
        </div>

        {/* Right: Process analytics sidebar */}
        <div className="result-sidebar">
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.68rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 4 }}>
            Process Analytics
          </div>

          {/* Execution Time */}
          <div className="analytics-card">
            <div className="analytics-card-label">Execution Time</div>
            <div className="analytics-card-value">{job.duration_ms}ms</div>
          </div>

          {/* Memory Peak */}
          <div className="analytics-card">
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '1rem' }}>
                {job.memory_mb < 20 ? '🟢' : job.memory_mb <= 100 ? '🟡' : '🔴'}
              </span>
              <div style={{ 
                fontFamily: 'var(--font-mono)', 
                fontSize: '0.75rem', 
                fontWeight: 600,
                color: 'var(--text-primary)',
                textTransform: 'uppercase',
                letterSpacing: '0.05em'
              }}>
                💾 Memory Usage: {job.memory_mb.toFixed(1)} MB
              </div>
            </div>
            <div style={{ 
              fontFamily: 'var(--font-mono)', 
              fontSize: '0.68rem', 
              color: job.memory_mb < 20 ? 'var(--success)' : job.memory_mb <= 100 ? 'var(--warning)' : 'var(--error)', 
              marginTop: '6px',
              marginLeft: '28px',
              textTransform: 'uppercase',
              letterSpacing: '0.06em',
              fontWeight: 600
            }}>
              {job.memory_mb < 20 ? 'Efficient' : job.memory_mb <= 100 ? 'Moderate' : 'Heavy'}
            </div>
          </div>

          {/* Compute Bill */}
          <div className="bill-card">
            <div className="analytics-card-label" style={{ marginBottom: 12 }}>Compute Bill</div>
            <div className="bill-row">
              <span>Unit Usage ({job.duration_ms}ms)</span>
              <span>${(job.cost_usd * 0.8).toFixed(4)}</span>
            </div>
            <div className="bill-row">
              <span>Network I/O</span>
              <span>${(job.cost_usd * 0.2).toFixed(4)}</span>
            </div>
            <div className="bill-row total">
              <span>Total Cost</span>
              <span>${job.cost_usd.toFixed(4)} USD</span>
            </div>
          </div>

          {/* Time Initiated */}
          <div className="analytics-card">
            <div className="analytics-card-label">Time Initiated</div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
              {new Date(job.created_at).toLocaleDateString('en-CA').replace(/-/g, '.')} {'//'} {new Date(job.created_at).toLocaleTimeString('en-GB')}
            </div>
          </div>

          {/* Complexity */}
          {job.complexity && (
            <div className="analytics-card">
              <div className="analytics-card-label">Complexity</div>
              <span className="complexity-badge">{job.complexity}</span>
              {job.complexity_note && (
                <div style={{ marginTop: 8, fontFamily: 'var(--font-mono)', fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                  {job.complexity_note}
                </div>
              )}
            </div>
          )}

          {/* Run Another CTA */}
          <button
            className="btn-cta"
            onClick={() => onNavigate('submit')}
          >
            <span>RUN ANOTHER</span>
            <span className="arrow">&rarr;</span>
          </button>

          <button
            className="footer-link"
            onClick={() => onNavigate('submit')}
            style={{ textAlign: 'center', marginTop: 4 }}
          >
            Return to Primary Command Interface
          </button>
        </div>
      </div>

      {/* Error info */}
      {job.error_info && (
        job.status === 'success' ? (
          <div className="error-info-card section-gap fade-in" style={{ backgroundColor: 'var(--success-bg)', borderColor: 'rgba(0, 230, 118, 0.15)', borderLeftColor: 'var(--success)' }}>
            <div className="error-title" style={{ color: 'var(--success)' }}>
              [INFO] NO ERROR FOUND
            </div>
            <p className="error-explanation" style={{ color: 'var(--success)' }}>No runtime errors were detected during execution.</p>
          </div>
        ) : (
          <div className="error-info-card section-gap fade-in">
            <div className="error-title">
              [ERROR] {job.error_info.title || 'Error'}
            </div>
            {job.error_info.explanation && (
              <p className="error-explanation">{job.error_info.explanation}</p>
            )}
            {job.error_info.fix && (
              <p className="error-fix"><strong>Fix:</strong> {job.error_info.fix}</p>
            )}
            {job.error_info.link && (
              <a className="error-learn-link" href={job.error_info.link} target="_blank" rel="noopener noreferrer">
                Learn more &rarr;
              </a>
            )}
          </div>
        )
      )}

      {/* Platform error */}
      {job.error && !job.error_info && (
        <div className="card section-gap" style={{ borderColor: 'rgba(255,61,61,0.2)' }}>
          <div className="card-title" style={{ color: 'var(--error)' }}>[ERROR]</div>
          <p className="text-sm" style={{ marginTop: 8, color: '#FF6B6B', fontFamily: 'var(--font-mono)' }}>{job.error}</p>
        </div>
      )}

      {/* Insights */}
      {job.insights && job.insights.length > 0 && (
        <div className="card section-gap">
          <div className="card-header">
            <span className="card-title">Code Insights</span>
          </div>
          <div className="insight-list">
            {job.insights.map((ins, i) => (
              <div className="insight-item" key={i}>
                <span className="insight-icon">&gt;</span>
                <div className="insight-body">
                  <div className="insight-msg">{ins.message}</div>
                  {ins.link && (
                    <a className="insight-link" href={ins.link} target="_blank" rel="noopener noreferrer">
                      Learn about {ins.topic} &rarr;
                    </a>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
