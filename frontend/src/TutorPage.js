import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  sendChatMessageStream,
  listChatSessions,
  getChatSession,
  deleteChatSession,
  listJobs,
} from './api';

// ─── Minimal Markdown Renderer ───
function renderMarkdown(text) {
  if (!text) return '';

  let html = text
    // Code blocks: ```lang\ncode\n```
    .replace(/```(\w*)\n([\s\S]*?)```/g, (_, lang, code) => {
      return `<div class="chat-code-block"><div class="chat-code-header">${lang || 'code'}</div><pre><code>${escapeHtml(code.trim())}</code></pre></div>`;
    })
    // Inline code: `code`
    .replace(/`([^`]+)`/g, '<code class="chat-inline-code">$1</code>')
    // Bold: **text**
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    // Italic: *text*
    .replace(/(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)/g, '<em>$1</em>')
    // Headers
    .replace(/^### (.+)$/gm, '<h4 class="chat-h4">$1</h4>')
    .replace(/^## (.+)$/gm, '<h3 class="chat-h3">$1</h3>')
    .replace(/^# (.+)$/gm, '<h2 class="chat-h2">$1</h2>')
    // Numbered lists
    .replace(/^(\d+)\. (.+)$/gm, '<div class="chat-list-item"><span class="chat-list-num">$1.</span> $2</div>')
    // Bullet lists
    .replace(/^[-•] (.+)$/gm, '<div class="chat-list-item"><span class="chat-list-bullet">•</span> $1</div>')
    // Line breaks
    .replace(/\n/g, '<br/>');

  return html;
}

function escapeHtml(str) {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}


export default function TutorPage({ addToast }) {
  // ─── Chat State ───
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [codeInput, setCodeInput] = useState('');
  const [showCodeInput, setShowCodeInput] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [sessionId, setSessionId] = useState(null);

  // ─── Sidebar State ───
  const [sessions, setSessions] = useState([]);
  const [sidebarTab, setSidebarTab] = useState('history'); // 'history' | 'jobs'
  const [jobs, setJobs] = useState([]);
  const [loadingJobs, setLoadingJobs] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const streamingRef = useRef('');

  // ─── Load sessions on mount ───
  const loadSessions = useCallback(async () => {
    try {
      const data = await listChatSessions();
      setSessions(data.sessions || []);
    } catch {
      // Silently fail
    }
  }, []);

  useEffect(() => {
    loadSessions();
  }, [loadSessions]);

  // ─── Auto-scroll ───
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // ─── Load jobs for code picker ───
  const loadJobs = useCallback(async () => {
    setLoadingJobs(true);
    try {
      const data = await listJobs();
      setJobs(data.jobs || []);
    } catch {
      // Silently fail
    } finally {
      setLoadingJobs(false);
    }
  }, []);

  useEffect(() => {
    if (sidebarTab === 'jobs') {
      loadJobs();
    }
  }, [sidebarTab, loadJobs]);

  // ─── Send Message ───
  async function handleSend() {
    const msg = input.trim();
    if (!msg && !codeInput.trim()) return;
    if (isStreaming) return;

    const userMessage = {
      role: 'user',
      content: msg,
      code: codeInput.trim() || null,
      timestamp: Date.now(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsStreaming(true);
    streamingRef.current = '';

    // Add placeholder for AI response
    const aiPlaceholder = {
      role: 'assistant',
      content: '',
      timestamp: Date.now(),
      streaming: true,
    };
    setMessages((prev) => [...prev, aiPlaceholder]);

    await sendChatMessageStream(
      {
        message: msg,
        code: codeInput.trim(),
        session_id: sessionId,
      },
      // onChunk
      (chunk) => {
        streamingRef.current += chunk;
        setMessages((prev) => {
          const updated = [...prev];
          const lastIdx = updated.length - 1;
          updated[lastIdx] = {
            ...updated[lastIdx],
            content: streamingRef.current,
          };
          return updated;
        });
      },
      // onDone
      () => {
        setMessages((prev) => {
          const updated = [...prev];
          const lastIdx = updated.length - 1;
          updated[lastIdx] = {
            ...updated[lastIdx],
            streaming: false,
          };
          return updated;
        });
        setIsStreaming(false);
        setShowCodeInput(false);
        setCodeInput('');
        loadSessions();

        // Grab session_id from the first response if we don't have one
        // (it's set server-side, we need to refresh sessions to get it)
      },
      // onError
      (err) => {
        setMessages((prev) => {
          const updated = [...prev];
          const lastIdx = updated.length - 1;
          updated[lastIdx] = {
            ...updated[lastIdx],
            content: `⚠️ Error: ${err.message || 'Failed to connect'}`,
            streaming: false,
            error: true,
          };
          return updated;
        });
        setIsStreaming(false);
        addToast('Failed to get AI response', 'error');
      }
    );
  }

  // ─── Load a session from history ───
  async function loadSession(sid) {
    try {
      const data = await getChatSession(sid);
      setSessionId(sid);
      setMessages(
        (data.messages || []).map((m, i) => ({
          role: m.role,
          content: m.content,
          timestamp: Date.now() - (data.messages.length - i) * 1000,
        }))
      );
    } catch {
      addToast('Failed to load session', 'error');
    }
  }

  // ─── Delete a session ───
  async function handleDeleteSession(sid, e) {
    e.stopPropagation();
    try {
      await deleteChatSession(sid);
      setSessions((prev) => prev.filter((s) => s.session_id !== sid));
      if (sessionId === sid) {
        handleNewChat();
      }
      addToast('Session deleted', 'info');
    } catch {
      addToast('Failed to delete session', 'error');
    }
  }

  // ─── New Chat ───
  function handleNewChat() {
    setSessionId(null);
    setMessages([]);
    setCodeInput('');
    setShowCodeInput(false);
    inputRef.current?.focus();
  }

  // ─── Select job code ───
  function handleSelectJobCode(job) {
    setCodeInput(job.code);
    setShowCodeInput(true);
    setSidebarTab('history');
    addToast(`Code loaded from job ${job.job_id.slice(0, 8)}`, 'success');
  }

  // ─── Quick Actions ───
  function handleQuickAction(action) {
    if (action === 'explain') {
      setInput('Explain this code step by step — what does each part do?');
      setShowCodeInput(true);
      inputRef.current?.focus();
    } else if (action === 'debug') {
      setInput('I have an error. Help me understand what went wrong and how to fix it.');
      setShowCodeInput(true);
      inputRef.current?.focus();
    } else if (action === 'optimize') {
      setInput('How can I optimize this code for better performance?');
      setShowCodeInput(true);
      inputRef.current?.focus();
    } else if (action === 'concept') {
      setInput('');
      inputRef.current?.focus();
    }
  }

  // ─── Key handler ───
  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  return (
    <div className="tutor-layout">
      {/* ═══ Sidebar ═══ */}
      <aside className={`tutor-sidebar ${sidebarOpen ? 'open' : 'collapsed'}`}>
        <div className="sidebar-header">
          <button
            className="sidebar-toggle"
            onClick={() => setSidebarOpen(!sidebarOpen)}
            title={sidebarOpen ? 'Collapse' : 'Expand'}
          >
            {sidebarOpen ? '◂' : '▸'}
          </button>
          {sidebarOpen && (
            <>
              <span className="sidebar-title">SESSIONS</span>
              <button className="sidebar-new-btn" onClick={handleNewChat} title="New Chat">
                +
              </button>
            </>
          )}
        </div>

        {sidebarOpen && (
          <>
            {/* Tab switcher */}
            <div className="sidebar-tabs">
              <button
                className={`sidebar-tab ${sidebarTab === 'history' ? 'active' : ''}`}
                onClick={() => setSidebarTab('history')}
              >
                History
              </button>
              <button
                className={`sidebar-tab ${sidebarTab === 'jobs' ? 'active' : ''}`}
                onClick={() => setSidebarTab('jobs')}
              >
                Job Code
              </button>
            </div>

            {/* Tab content */}
            <div className="sidebar-content">
              {sidebarTab === 'history' ? (
                sessions.length === 0 ? (
                  <div className="sidebar-empty">
                    <span className="sidebar-empty-icon">[~]</span>
                    <span>No conversations yet</span>
                  </div>
                ) : (
                  sessions.map((s) => (
                    <div
                      key={s.session_id}
                      className={`sidebar-item ${sessionId === s.session_id ? 'active' : ''}`}
                      onClick={() => loadSession(s.session_id)}
                    >
                      <div className="sidebar-item-title">{s.title}</div>
                      <div className="sidebar-item-meta">
                        {s.message_count} msgs
                        <button
                          className="sidebar-item-delete"
                          onClick={(e) => handleDeleteSession(s.session_id, e)}
                          title="Delete"
                        >
                          ×
                        </button>
                      </div>
                    </div>
                  ))
                )
              ) : (
                /* Jobs tab */
                loadingJobs ? (
                  <div className="sidebar-empty">
                    <div className="spinner spinner-accent" style={{ width: 14, height: 14 }}></div>
                    <span>Loading jobs...</span>
                  </div>
                ) : jobs.length === 0 ? (
                  <div className="sidebar-empty">
                    <span className="sidebar-empty-icon">[--]</span>
                    <span>No jobs found</span>
                  </div>
                ) : (
                  jobs.map((job) => (
                    <div
                      key={job.job_id}
                      className="sidebar-item job-item"
                      onClick={() => handleSelectJobCode(job)}
                    >
                      <div className="sidebar-item-title">
                        <span className={`sidebar-status-dot ${job.status}`}></span>
                        {job.job_id.slice(0, 8)}
                      </div>
                      <div className="sidebar-item-code-preview">
                        {job.code_preview}
                      </div>
                    </div>
                  ))
                )
              )}
            </div>
          </>
        )}
      </aside>

      {/* ═══ Main Chat Area ═══ */}
      <div className="tutor-main">
        {/* Header */}
        <div className="tutor-header">
          <div>
            <div className="page-header-label">NEURAL INTERFACE: ACTIVE</div>
            <h1 className="page-title" style={{ fontSize: '1.8rem' }}>
              AI <span className="accent">TUTOR</span>
            </h1>
          </div>
          <div className="tutor-header-actions">
            {sessionId && (
              <span className="tutor-session-badge">
                SESSION: {sessionId.slice(0, 8)}
              </span>
            )}
          </div>
        </div>

        {/* Messages */}
        <div className="chat-messages" id="chat-messages">
          {messages.length === 0 ? (
            <div className="chat-welcome fade-in">
              <div className="chat-welcome-icon">⚡</div>
              <h2 className="chat-welcome-title">
                FEM<span className="accent">SCALE</span> AI TUTOR
              </h2>
              <p className="chat-welcome-subtitle">
                Your personal coding mentor. Paste code, ask questions, debug errors.
              </p>

              {/* Quick Actions */}
              <div className="quick-actions">
                <button className="quick-action-btn" onClick={() => handleQuickAction('explain')}>
                  <span className="quick-action-icon">📖</span>
                  <span className="quick-action-label">Explain Code</span>
                  <span className="quick-action-desc">Break down what code does</span>
                </button>
                <button className="quick-action-btn" onClick={() => handleQuickAction('debug')}>
                  <span className="quick-action-icon">🔴</span>
                  <span className="quick-action-label">Debug Error</span>
                  <span className="quick-action-desc">Fix and understand errors</span>
                </button>
                <button className="quick-action-btn" onClick={() => handleQuickAction('optimize')}>
                  <span className="quick-action-icon">⚡</span>
                  <span className="quick-action-label">Optimize</span>
                  <span className="quick-action-desc">Improve performance</span>
                </button>
                <button className="quick-action-btn" onClick={() => handleQuickAction('concept')}>
                  <span className="quick-action-icon">💡</span>
                  <span className="quick-action-label">Learn Concept</span>
                  <span className="quick-action-desc">Ask about any topic</span>
                </button>
              </div>

              <p className="chat-welcome-hint">
                💡 Tip: Load code from your past jobs using the <strong>Job Code</strong> tab in the sidebar
              </p>
            </div>
          ) : (
            messages.map((msg, i) => (
              <div
                key={i}
                className={`chat-message ${msg.role === 'user' ? 'chat-message-user' : 'chat-message-ai'} ${msg.error ? 'chat-message-error' : ''} fade-in-up`}
              >
                <div className="chat-message-avatar">
                  {msg.role === 'user' ? '>' : '◆'}
                </div>
                <div className="chat-message-body">
                  <div className="chat-message-role">
                    {msg.role === 'user' ? 'YOU' : 'AI TUTOR'}
                    {msg.streaming && (
                      <span className="chat-typing-dot">●</span>
                    )}
                  </div>
                  {msg.role === 'user' && msg.code && (
                    <div className="chat-attached-code">
                      <div className="chat-attached-code-header">📎 Attached Code</div>
                      <pre><code>{msg.code}</code></pre>
                    </div>
                  )}
                  <div
                    className="chat-message-content"
                    dangerouslySetInnerHTML={{
                      __html: renderMarkdown(msg.content) || (msg.streaming ? '<span class="chat-cursor">▌</span>' : ''),
                    }}
                  />
                </div>
              </div>
            ))
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Code Input (expandable) */}
        {showCodeInput && (
          <div className="chat-code-input-area fade-in">
            <div className="chat-code-input-header">
              <span>📎 Code Context</span>
              <button
                className="chat-code-close"
                onClick={() => { setShowCodeInput(false); setCodeInput(''); }}
              >
                ×
              </button>
            </div>
            <textarea
              className="chat-code-textarea"
              value={codeInput}
              onChange={(e) => setCodeInput(e.target.value)}
              placeholder="Paste your code here..."
              spellCheck={false}
              rows={6}
            />
          </div>
        )}

        {/* Input Area */}
        <div className="chat-input-area">
          <div className="chat-input-actions">
            <button
              className={`chat-attach-btn ${showCodeInput ? 'active' : ''}`}
              onClick={() => setShowCodeInput(!showCodeInput)}
              title="Attach code"
            >
              {showCodeInput ? '◆' : '+'} Code
            </button>
          </div>
          <div className="chat-input-row">
            <textarea
              ref={inputRef}
              className="chat-input"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={isStreaming ? 'AI is thinking...' : 'Ask me anything about code...'}
              disabled={isStreaming}
              rows={1}
            />
            <button
              className="chat-send-btn"
              onClick={handleSend}
              disabled={isStreaming || (!input.trim() && !codeInput.trim())}
            >
              {isStreaming ? (
                <span className="spinner" style={{ width: 14, height: 14 }}></span>
              ) : (
                '→'
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
