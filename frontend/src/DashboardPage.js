import React, { useState, useEffect, useRef, useCallback } from 'react';
import { getMetrics } from './api';

export default function DashboardPage({ onNavigate, addToast }) {
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);
  const intervalRef = useRef(null);

  const fetchMetrics = useCallback(async () => {
    try {
      const data = await getMetrics();
      setMetrics(data);
      setLoading(false);
    } catch (err) {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchMetrics();
    intervalRef.current = setInterval(fetchMetrics, 2000);
    return () => clearInterval(intervalRef.current);
  }, [fetchMetrics]);

  if (loading && !metrics) {
    return (
      <div className="fade-in" style={{ textAlign: 'center', paddingTop: 80 }}>
        <div className="spinner spinner-lg spinner-accent" style={{ margin: '0 auto 16px' }}></div>
        <p className="text-muted" style={{ fontFamily: 'var(--font-mono)', textTransform: 'uppercase', letterSpacing: '0.08em', fontSize: '0.75rem' }}>Loading metrics</p>
      </div>
    );
  }

  if (!metrics) {
    return (
      <div className="empty-state">
        <div className="empty-state-icon">[!]</div>
        <p className="empty-state-text">Could not load metrics -- is the backend running?</p>
      </div>
    );
  }

  // Parse events for the event log and recent jobs
  const events = metrics.events || [];
  const jobEvents = events
    .filter((e) => e.event === 'job_completed' || e.type === 'job_completed')
    .slice(-10)
    .reverse();

  return (
    <div className="fade-in-up">
      <div className="flex-between" style={{ marginBottom: 24 }}>
        <div>
          <div className="page-header-label">INFRASTRUCTURE MONITOR</div>
          <h1 className="page-title">
            LIVE <span className="accent">DASHBOARD</span>
          </h1>
          <p className="page-subtitle" style={{ marginBottom: 0 }}>
            Real-time platform metrics. <strong>Auto-refreshing every 2s.</strong>
          </p>
        </div>
        <span className="poll-indicator">
          <span className="poll-dot"></span>
          live
        </span>
      </div>

      {/* Metric Cards */}
      <div className="metrics-grid">
        <div className="metric-card purple">
          <div className="metric-label">Queue Depth</div>
          <div className="metric-value" id="metric-queue">{metrics.queue_depth}</div>
        </div>
        <div className="metric-card blue">
          <div className="metric-label">Active Workers</div>
          <div className="metric-value" id="metric-workers">
            {metrics.workers_active}
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', fontWeight: 500, color: 'var(--text-muted)', marginLeft: 6 }}>
              / {metrics.workers_target} target
            </span>
          </div>
        </div>
        <div className="metric-card green">
          <div className="metric-label">Jobs Running</div>
          <div className="metric-value" id="metric-running">{metrics.jobs_running}</div>
        </div>
        <div className="metric-card amber">
          <div className="metric-label">Session Cost</div>
          <div className="metric-value" id="metric-cost">
            ${metrics.total_cost_session_usd.toFixed(10)}
          </div>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.65rem', color: 'var(--text-muted)', marginTop: 4, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
            {metrics.jobs_completed_session} jobs completed
          </div>
        </div>
      </div>

      {/* Two-column: Recent Jobs + Event Log */}
      <div className="result-grid">
        {/* Recent Executions */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">Recent Executions</span>
            <span className="card-subtitle">{jobEvents.length} job{jobEvents.length !== 1 ? 's' : ''}</span>
          </div>
          {jobEvents.length === 0 ? (
            <div className="empty-state" style={{ padding: '32px 16px' }}>
              <div className="empty-state-icon">[--]</div>
              <p className="empty-state-text">No completed jobs yet</p>
            </div>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Job ID</th>
                    <th>Status</th>
                    <th>Duration</th>
                    <th>Cost</th>
                  </tr>
                </thead>
                <tbody>
                  {jobEvents.map((ev, i) => (
                    <tr
                      key={i}
                      style={{ cursor: 'pointer' }}
                      onClick={() => {
                        if (ev.job_id) onNavigate('result', ev.job_id);
                      }}
                    >
                      <td className="mono">{(ev.job_id || '--').slice(0, 8)}</td>
                      <td>
                        <span className={`status-badge status-${ev.status || 'success'}`}>
                          <span className="dot"></span>
                          {ev.status || 'success'}
                        </span>
                      </td>
                      <td className="mono">{ev.duration_ms != null ? `${ev.duration_ms}ms` : '--'}</td>
                      <td className="mono">{ev.cost_usd != null ? `$${ev.cost_usd.toFixed(10)}` : '--'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Event Log */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">Event Log</span>
            <span className="card-subtitle">{events.length} event{events.length !== 1 ? 's' : ''}</span>
          </div>
          {events.length === 0 ? (
            <div className="empty-state" style={{ padding: '32px 16px' }}>
              <div className="empty-state-icon">[--]</div>
              <p className="empty-state-text">No events yet</p>
            </div>
          ) : (
            <div className="event-log">
              {[...events].reverse().map((ev, i) => {
                const time = ev.ts || ev.timestamp || '';
                const label = ev.event || ev.type || 'event';
                const shortTime = time ? new Date(time).toLocaleTimeString() : '';
                return (
                  <div className="event-item" key={i}>
                    <span className="event-dot"></span>
                    <span className="event-time">{shortTime}</span>
                    <span className="event-text">
                      <strong>{formatEventLabel(label)}</strong>
                      {ev.job_id && (
                        <span className="mono" style={{ marginLeft: 6, opacity: 0.7 }}>
                          {ev.job_id.slice(0, 8)}
                        </span>
                      )}
                    </span>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function formatEventLabel(label) {
  return label
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
}
