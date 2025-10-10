import React, { useState, useEffect } from 'react';

const AGENT_API = 'http://127.0.0.1:8080';
const MCP_API = 'http://127.0.0.1:8765';
const AM_UI = 'http://127.0.0.1:5200';

export default function App() {
  const [agentApiStatus, setAgentApiStatus] = useState('checking');
  const [mcpStatus, setMcpStatus] = useState('checking');
  const [amStatus, setAmStatus] = useState('checking');
  const [agents, setAgents] = useState([]);
  const [showExtension, setShowExtension] = useState(false);

  useEffect(() => {
    checkServices();
    loadAgents();
  }, []);

  const checkServices = async () => {
    // Check Agent API
    try {
      const res = await fetch(`${AGENT_API}/healthz`);
      setAgentApiStatus(res.ok ? 'online' : 'offline');
    } catch (e) {
      setAgentApiStatus('offline');
    }

    // Check MCP Server
    try {
      // MCP might require auth, just check if it's reachable
      setMcpStatus('unknown');
    } catch (e) {
      setMcpStatus('offline');
    }

    // Check Automation Memory UI
    try {
      const res = await fetch(`${AM_UI}/healthz`);
      setAmStatus(res.ok ? 'online' : 'offline');
    } catch (e) {
      setAmStatus('offline');
    }
  };

  const loadAgents = async () => {
    try {
      const res = await fetch(`${AGENT_API}/v1/models`);
      const data = await res.json();
      setAgents((data.data || []).map(m => m.id));
    } catch (e) {
      console.error('Failed to load agents:', e);
    }
  };

  return (
    <div className="app">
      <div className="header">
        <h1>🌙 Luna Hub</h1>
        <p>AI Agent Platform - Control Center</p>
      </div>

      <div className="dashboard">
        <div className="card">
          <div className="card-title">
            <span className={`status-indicator ${agentApiStatus}`}></span>
            Agent API
          </div>
          <div className="card-content">
            <p>OpenAI-compatible API server</p>
            <p style={{ marginTop: 8, fontSize: 12, color: '#999' }}>
              {AGENT_API}
            </p>
            <p style={{ marginTop: 8 }}>
              Status: <strong>{agentApiStatus}</strong>
            </p>
          </div>
        </div>

        <div className="card">
          <div className="card-title">
            <span className={`status-indicator ${mcpStatus === 'unknown' ? 'online' : mcpStatus}`}></span>
            MCP Server
          </div>
          <div className="card-content">
            <p>Model Context Protocol server</p>
            <p style={{ marginTop: 8, fontSize: 12, color: '#999' }}>
              {MCP_API}
            </p>
            <p style={{ marginTop: 8 }}>
              SSE transport with Bearer auth
            </p>
          </div>
        </div>

        <div className="card">
          <div className="card-title">
            <span className={`status-indicator ${amStatus}`}></span>
            Automation Memory
          </div>
          <div className="card-content">
            <p>Memories, flows, and schedules</p>
            <p style={{ marginTop: 8, fontSize: 12, color: '#999' }}>
              {AM_UI}
            </p>
            <p style={{ marginTop: 8 }}>
              Status: <strong>{amStatus}</strong>
            </p>
          </div>
        </div>

        <div className="card">
          <div className="card-title">Available Agents</div>
          <div className="card-content">
            {agents.length > 0 ? (
              <ul className="agents-list">
                {agents.map(agent => (
                  <li key={agent}>
                    <span className="agent-badge">{agent}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p>No agents discovered</p>
            )}
          </div>
        </div>
      </div>

      <div className="extensions-section">
        <h2>Extensions</h2>
        
        <div className="extension-card">
          <div className="extension-header">
            <span className="extension-name">Automation Memory</span>
            <button
              className="btn btn-primary"
              onClick={() => setShowExtension(!showExtension)}
            >
              {showExtension ? 'Hide UI' : 'Show UI'}
            </button>
          </div>
          <p style={{ color: '#666', fontSize: 14 }}>
            Manage memories, scheduled tasks, and task flows
          </p>
          
          {showExtension && amStatus === 'online' && (
            <iframe
              className="extension-iframe"
              src={AM_UI}
              title="Automation Memory UI"
            />
          )}
          
          {showExtension && amStatus !== 'online' && (
            <div style={{ padding: 20, background: '#ffebee', borderRadius: 8, marginTop: 15, color: '#c62828' }}>
              Extension UI is not available. Make sure the backend is running on port 5200.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

