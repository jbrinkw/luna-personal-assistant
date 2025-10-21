import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useSystem } from '../context/SystemContext';
import { useServices } from '../context/ServicesContext';
import { SystemAPI } from '../lib/api';
import Card, { CardTitle, CardContent } from '../components/common/Card';
import StatusIndicator from '../components/common/StatusIndicator';
import Button from '../components/common/Button';
import { formatRelativeTime, getActivities } from '../lib/utils';

// Use relative paths through Caddy reverse proxy
const AGENT_API = '/api/agent';
const MCP_API = '/api/mcp';

export default function Dashboard() {
  const navigate = useNavigate();
  const { health } = useSystem();
  const { extensions, restartUI, restartService } = useServices();
  
  const [agentApiStatus, setAgentApiStatus] = useState('checking');
  const [mcpStatus, setMcpStatus] = useState('checking');
  const [agents, setAgents] = useState([]);
  const [recentActivities, setRecentActivities] = useState([]);

  useEffect(() => {
    checkServices();
    loadAgents();
    setRecentActivities(getActivities(10));
  }, []);

  const checkServices = async () => {
    let agentOnline = false;
    try {
      const res = await fetch(`${AGENT_API}/healthz`);
      agentOnline = res.ok;
      setAgentApiStatus(res.ok ? 'online' : 'offline');
    } catch (e) {
      setAgentApiStatus('offline');
    }

    try {
      const res = await fetch(`${MCP_API}/`);
      if (res.status === 401 || res.ok) {
        setMcpStatus('online');
      } else {
        setMcpStatus('offline');
      }
    } catch (e) {
      setMcpStatus(agentOnline ? 'online' : 'offline');
    }
  };

  const loadAgents = async () => {
    try {
      const res = await SystemAPI.getModels();
      setAgents((res.data || []).map(m => m.id));
    } catch (e) {
      console.error('Failed to load agents:', e);
    }
  };

  const handleRestartUI = async (name) => {
    try {
      await restartUI(name);
    } catch (error) {
      console.error('Restart failed:', error);
    }
  };

  const handleRestartService = async (extName, serviceName) => {
    try {
      await restartService(extName, serviceName);
    } catch (error) {
      console.error('Restart failed:', error);
    }
  };

  return (
    <div className="dashboard-page">
      {/* Core Services Section */}
      <div className="dashboard">
        <Card>
          <CardTitle>
            <StatusIndicator status={agentApiStatus} />
            Agent API
          </CardTitle>
          <CardContent>
            <p>OpenAI-compatible API server</p>
            <p style={{ marginTop: 8, fontSize: 12, color: '#999' }}>
              {AGENT_API}
            </p>
            <p style={{ marginTop: 8 }}>
              Status: <strong>{agentApiStatus}</strong>
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardTitle>
            <StatusIndicator status={mcpStatus === 'unknown' ? 'online' : mcpStatus} />
            MCP Server
          </CardTitle>
          <CardContent>
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
          </CardContent>
        </Card>

        <Card>
          <CardTitle>Available Agents</CardTitle>
          <CardContent>
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
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions */}
      <div className="quick-actions-section">
        <h2>Quick Actions</h2>
        <div className="quick-actions">
          <Card className="action-card" onClick={() => navigate('/store')}>
            <div className="action-icon">📦</div>
            <div className="action-label">Browse Store</div>
          </Card>
          <Card className="action-card" onClick={() => navigate('/queue')}>
            <div className="action-icon">📋</div>
            <div className="action-label">Manage Queue</div>
          </Card>
          <Card className="action-card" onClick={() => navigate('/secrets')}>
            <div className="action-icon">🔑</div>
            <div className="action-label">Manage Secrets</div>
          </Card>
          <Card className="action-card" onClick={() => navigate('/extensions')}>
            <div className="action-icon">⚙️</div>
            <div className="action-label">Extensions</div>
          </Card>
        </div>
      </div>

      {/* Extensions Health Section */}
      <div className="extensions-health-section">
        <h2>Extensions Health</h2>
        {extensions.length === 0 ? (
          <p className="no-extensions">No extensions discovered</p>
        ) : (
          <div className="extension-blocks">
            {extensions.map(ext => (
              <div key={ext.name} className="extension-block">
                <div className="extension-block-header">
                  <h3>{ext.name}</h3>
                </div>
                
                <div className="extension-block-content">
                  {/* UI Status */}
                  <div className="health-row">
                    <StatusIndicator status={ext.ui?.status || 'offline'} />
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
                        onClick={() => handleRestartUI(ext.name)}
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
                          <StatusIndicator status={svc.status || 'unknown'} />
                          <span className="service-name">{svc.name}</span>
                          <span className="service-detail">
                            {svc.status || 'unknown'}
                            {svc.port && ` | 127.0.0.1:${svc.port}`}
                          </span>
                          <button 
                            className="btn-icon" 
                            onClick={() => handleRestartService(ext.name, svc.name)}
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
                  <div className="extension-actions">
                    <Button variant="secondary" onClick={() => navigate(`/extensions/${ext.name}`)}>
                      Details
                    </Button>
                    {ext.ui?.url && (
                      <Button onClick={() => navigate(`/ext/${ext.name}`)}>
                        View UI
                      </Button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Recent Activity */}
      {recentActivities.length > 0 && (
        <div className="recent-activity-section">
          <h2>Recent Activity</h2>
          <div className="activity-list">
            {recentActivities.map(activity => (
              <div key={activity.id} className="activity-item">
                <span className="activity-message">{activity.message}</span>
                <span className="activity-time">{formatRelativeTime(activity.timestamp)}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}




