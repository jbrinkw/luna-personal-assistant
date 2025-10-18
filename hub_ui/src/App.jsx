import React, { useState, useEffect } from 'react';

const AGENT_API = 'http://127.0.0.1:8080';
const MCP_API = 'http://127.0.0.1:8765';

export default function App() {
  const [agentApiStatus, setAgentApiStatus] = useState('checking');
  const [mcpStatus, setMcpStatus] = useState('checking');
  const [extensions, setExtensions] = useState([]);
  const [agents, setAgents] = useState([]);
  const [currentView, setCurrentView] = useState('home');
  const [selectedExtension, setSelectedExtension] = useState(null);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    checkServices();
    loadAgents();
    loadExtensions();
    
    // Refresh extensions every 10 seconds
    const interval = setInterval(() => {
      loadExtensions();
    }, 10000);
    
    return () => clearInterval(interval);
  }, []);

  const checkServices = async () => {
    // Check Agent API first (needed for MCP fallback)
    let agentOnline = false;
    try {
      const res = await fetch(`${AGENT_API}/healthz`);
      agentOnline = res.ok;
      setAgentApiStatus(res.ok ? 'online' : 'offline');
    } catch (e) {
      setAgentApiStatus('offline');
    }

    // Check MCP Server (with GitHub OAuth)
    try {
      const res = await fetch(`${MCP_API}/`);
      // GitHub OAuth MCP: 401 = auth required (server is up), 200 = authenticated
      if (res.status === 401 || res.ok) {
        setMcpStatus('online');
      } else {
        setMcpStatus('offline');
      }
    } catch (e) {
      // CORS or network error - if Agent API is up, assume MCP is too
      setMcpStatus(agentOnline ? 'online' : 'offline');
    }
  };

  const loadExtensions = async () => {
    try {
      const res = await fetch(`${AGENT_API}/extensions`);
      const data = await res.json();
      setExtensions(Array.isArray(data.extensions) ? data.extensions : []);
    } catch (e) {
      setExtensions([]);
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

  const openExtensionFullscreen = (ext) => {
    setSelectedExtension(ext);
    setCurrentView('extension-iframe');
    setMenuOpen(false);
  };

  const openExtensionNewTab = (ext) => {
    if (ext.ui?.url) {
      window.open(ext.ui.url, '_blank');
    }
  };

  const navigateToHome = () => {
    setCurrentView('home');
    setSelectedExtension(null);
    setMenuOpen(false);
  };

  const restartUI = async (name) => {
    try {
      await fetch(`${AGENT_API}/extensions/${name}/ui/restart`, { method: 'POST' });
      loadExtensions();
    } catch {}
  };

  const restartService = async (name, service) => {
    try {
      await fetch(`${AGENT_API}/extensions/${name}/services/${service}/restart`, { method: 'POST' });
      loadExtensions();
    } catch {}
  };

  const extensionsWithUI = extensions.filter(ext => ext.ui?.url);

  return (
    <div className="app">
      {/* Hamburger Menu Button */}
      <button 
        className="hamburger-btn" 
        onClick={() => setMenuOpen(!menuOpen)}
        aria-label="Toggle menu"
      >
        <div className="hamburger-icon">
          <span></span>
          <span></span>
          <span></span>
        </div>
      </button>

      {/* Slide-out Menu */}
      {menuOpen && <div className="menu-overlay" onClick={() => setMenuOpen(false)}></div>}
      <div className={`slide-menu ${menuOpen ? 'open' : ''}`}>
        <div className="menu-header">Navigation</div>
        <div className="menu-item" onClick={navigateToHome}>
          <span className="menu-icon">🏠</span>
          Home
        </div>
        <div className="menu-divider"></div>
        <div className="menu-section-title">Extensions</div>
        {extensionsWithUI.length === 0 && (
          <div className="menu-item disabled">No extension UIs</div>
        )}
        {extensionsWithUI.map(ext => (
          <div 
            key={ext.name} 
            className="menu-item" 
            onClick={() => openExtensionFullscreen(ext)}
          >
            <span className="menu-icon">📦</span>
            {ext.name}
          </div>
        ))}
      </div>

      {/* Main Content */}
      {currentView === 'home' ? (
        <>
          <div className="header">
            <h1>🌙 Luna Hub</h1>
            <p>AI Agent Platform - Control Center</p>
          </div>

          <div className="dashboard">
            {/* Core Services */}
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
                  Status: <strong>{mcpStatus}</strong>
                </p>
                <p style={{ marginTop: 4, fontSize: 12, color: '#666' }}>
                  GitHub OAuth • Streamable HTTP
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

          {/* Extensions Health Section */}
          <div className="extensions-health-section">
            <h2>Extensions Health</h2>
            {extensions.length === 0 && (
              <p className="no-extensions">No extensions discovered</p>
            )}
            <div className="extension-blocks">
              {extensions.map(ext => (
                <div key={ext.name} className="extension-block">
                  <div className="extension-block-header">
                    <h3>{ext.name}</h3>
                  </div>
                  
                  <div className="extension-block-content">
                    {/* UI Status */}
                    <div className="health-row">
                      <span className={`status-indicator ${ext.ui?.status || 'offline'}`}></span>
                      <span className="health-label">UI:</span>
                      <span className="health-value">
                        {ext.ui?.url ? (
                          <>
                            {ext.ui.status || 'unknown'}
                            <span className="health-detail"> | {ext.ui.url}</span>
                          </>
                        ) : (
                          'none'
                        )}
                      </span>
                      {ext.ui?.url && (
                        <button 
                          className="btn-icon" 
                          onClick={() => restartUI(ext.name)}
                          title="Restart UI"
                        >
                          🔄
                        </button>
                      )}
                    </div>

                    {/* Services Status */}
                    {ext.services && ext.services.length > 0 && (
                      <div className="services-section">
                        <div className="health-label">Services:</div>
                        {ext.services.map(svc => (
                          <div key={svc.name} className="service-row">
                            <span className={`status-indicator ${svc.status || 'unknown'}`}></span>
                            <span className="service-name">{svc.name}</span>
                            <span className="service-detail">
                              {svc.status || 'unknown'}
                              {svc.port && ` | 127.0.0.1:${svc.port}`}
                            </span>
                            <button 
                              className="btn-icon" 
                              onClick={() => restartService(ext.name, svc.name)}
                              title="Restart Service"
                            >
                              🔄
                            </button>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Tool Count */}
                    <div className="tools-count">
                      🛠️ {ext.tool_count || 0} tools loaded
                    </div>

                    {/* Action Buttons */}
                    {ext.ui?.url && (
                      <div className="extension-actions">
                        <button 
                          className="btn btn-secondary" 
                          onClick={() => openExtensionNewTab(ext)}
                        >
                          Open in New Tab
                        </button>
                        <button 
                          className="btn btn-primary" 
                          onClick={() => openExtensionFullscreen(ext)}
                        >
                          View Fullscreen
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </>
      ) : (
        /* Fullscreen Iframe View */
        <div className="fullscreen-iframe-container">
          {selectedExtension?.ui?.url ? (
            <iframe 
              className="fullscreen-iframe" 
              src={selectedExtension.ui.url} 
              title={`${selectedExtension.name} UI`}
            />
          ) : (
            <div className="iframe-error">
              <p>No UI available for this extension</p>
              <button className="btn btn-primary" onClick={navigateToHome}>
                Back to Home
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
