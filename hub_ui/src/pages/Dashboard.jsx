import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useSystem } from '../context/SystemContext';
import { useServices } from '../context/ServicesContext';
import { SystemAPI } from '../lib/api';
import { getInstalledServices } from '../lib/externalServicesApi';
import Card, { CardTitle, CardContent } from '../components/common/Card';
import StatusIndicator from '../components/common/StatusIndicator';
import Button from '../components/common/Button';

// Use relative paths through Caddy reverse proxy
const AGENT_API = '/api/agent';
const MCP_API = '/api/mcp';

export default function Dashboard() {
  const navigate = useNavigate();
  const { health } = useSystem();
  const { extensions } = useServices();
  
  const [agentApiStatus, setAgentApiStatus] = useState('checking');
  const [mcpStatus, setMcpStatus] = useState('checking');
  const [agents, setAgents] = useState([]);
  const [externalServices, setExternalServices] = useState({});

  useEffect(() => {
    checkServices();
    loadAgents();
    loadExternalServices();
  }, []);

  const checkServices = async () => {
    try {
      const res = await fetch(`${AGENT_API}/healthz`);
      setAgentApiStatus(res.ok ? 'online' : 'offline');
    } catch (e) {
      setAgentApiStatus('offline');
    }

    try {
      const res = await fetch('/api/supervisor/services/status');
      if (res.ok) {
        const data = await res.json();
        const mcpService = data.services?.mcp_server;
        if (mcpService && mcpService.status === 'running') {
          setMcpStatus('online');
        } else {
          setMcpStatus('offline');
        }
      } else {
        setMcpStatus('offline');
      }
    } catch (e) {
      setMcpStatus('offline');
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

  const loadExternalServices = async () => {
    try {
      const data = await getInstalledServices();
      setExternalServices(data || {});
    } catch (e) {
      console.error('Failed to load external services:', e);
    }
  };

  // Get all items with UIs (extensions + external services)
  const getActiveUIs = () => {
    const items = [];
    
    // Add extensions with UIs
    extensions.forEach(ext => {
      if (ext.ui?.url) {
        items.push({
          name: ext.name,
          url: ext.ui.url,
          status: ext.ui.status || 'unknown',
          type: 'extension'
        });
      }
    });

    // Add external services with UIs
    Object.entries(externalServices).forEach(([name, service]) => {
      if (service.ui) {
        items.push({
          name: name,
          url: service.ui.url || `/ext_service/${name}`,
          status: service.status || 'unknown',
          type: 'external_service'
        });
      }
    });

    return items;
  };

  // Calculate total tool count across all extensions
  const getTotalToolCount = () => {
    return extensions.reduce((sum, ext) => sum + (ext.tool_count || 0), 0);
  };

  // Get relevant extensions (those with tools, services, or UIs)
  const getRelevantExtensions = () => {
    return extensions.filter(ext => 
      (ext.tool_count && ext.tool_count > 0) ||
      (ext.services && ext.services.length > 0) ||
      (ext.ui?.url)
    );
  };

  const activeUIs = getActiveUIs();
  const totalToolCount = getTotalToolCount();
  const relevantExtensions = getRelevantExtensions();
  const totalToolsIconClass = totalToolCount > 0 ? 'icon-warning' : 'icon-success';

  return (
    <div className="dashboard-page">
      {/* Quick Actions */}
      <div className="quick-actions-section">
        <h2>QUICK ACTIONS</h2>
        <div className="quick-actions">
          <Card className="action-card" onClick={() => navigate('/store')}>
            <div className="action-icon">📦</div>
            <div className="action-label">Browse Store</div>
          </Card>
          <Card className="action-card" onClick={() => navigate('/queue')}>
            <div className="action-icon">📋</div>
            <div className="action-label">Update Manager</div>
          </Card>
          <Card className="action-card" onClick={() => navigate('/secrets')}>
            <div className="action-icon">🔑</div>
            <div className="action-label">Manage Secrets</div>
          </Card>
          <Card className="action-card" onClick={() => navigate('/infrastructure')}>
            <div className="action-icon">🏗️</div>
            <div className="action-label">Infrastructure</div>
          </Card>
          <Card className="action-card" onClick={() => navigate('/extensions')}>
            <div className="action-icon">⚙️</div>
            <div className="action-label">Extensions</div>
          </Card>
        </div>
      </div>

      {/* Main Content: Two Column Layout */}
      <div className="dashboard-main-grid">
        
        {/* Left Column */}
        <div className="dashboard-column">
          
          {/* Active UIs */}
          <Card>
            <CardTitle>ACTIVE UIs</CardTitle>
            <CardContent>
              {activeUIs.length === 0 ? (
                <p className="text-muted">No UIs available</p>
              ) : (
                <div className="dashboard-stack">
                  {activeUIs.map(item => (
                    <div key={`${item.type}-${item.name}`} className="dashboard-row">
                      <StatusIndicator status={item.status} />
                      <span className="text-strong flex-1">{item.name}</span>
                      <Button 
                        variant="secondary" 
                        onClick={() => {
                          if (item.type === 'extension') {
                            navigate(`/ext/${item.name}`);
                          } else {
                            window.open(item.url, '_blank');
                          }
                        }}
                        size="sm"
                      >
                        View UI
                      </Button>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Discovered Agents */}
          <Card>
            <CardTitle>DISCOVERED AGENTS</CardTitle>
            <CardContent>
              {agents.length === 0 ? (
                <p className="text-muted">No agents discovered</p>
              ) : (
                <>
                  <p className="dashboard-section-note">Available Agents:</p>
                  <ul className="list-unstyled">
                    {agents.map(agent => (
                      <li key={agent} className="list-item">
                        • {agent}
                      </li>
                    ))}
                  </ul>
                  <p className="text-muted text-sm mt-sm">
                    Total: {agents.length} Active
                  </p>
                </>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Right Column */}
        <div>
          <Card>
            <CardTitle>HEALTH MONITOR</CardTitle>
            <CardContent>
              <div className="dashboard-stack-lg">
                
                {/* System Status */}
                <div>
                  <div className="dashboard-row-tight mb-xs">
                    <span className="icon-success">✓</span>
                    <span className="text-strong fw-semibold">System Status</span>
                  </div>
                  <div className="dashboard-indented">
                    <div className="dashboard-row-tight">
                      <StatusIndicator status={agentApiStatus} />
                      <span className="text-strong">Agent API</span>
                      <span className="text-muted text-xs">{AGENT_API}</span>
                    </div>
                    <div className="dashboard-row-tight">
                      <StatusIndicator status={mcpStatus} />
                      <span className="text-strong">MCP Server</span>
                      <span className="text-muted text-xs">{MCP_API}</span>
                    </div>
                    <div className="text-muted text-sm mt-xs">
                      {agents.length} Active Agents
                    </div>
                  </div>
                </div>

                {/* Extensions */}
                {relevantExtensions.length > 0 && (
                  <div>
                    <div className="dashboard-row-tight mb-xs">
                      <span className={totalToolsIconClass}>
                        {totalToolCount > 0 ? '⚠️' : '✓'}
                      </span>
                      <span className="text-strong fw-semibold">
                        Extensions {totalToolCount > 0 && `(${totalToolCount} tools)`}
                      </span>
                    </div>
                    <div className="dashboard-indented-lg">
                      {relevantExtensions.map(ext => {
                        const hasNested = (ext.ui?.url) || (ext.services && ext.services.length > 0);
                        
                        return (
                          <div key={ext.name} className="dashboard-stack-tight">
                            <div className="dashboard-row-tight">
                              <StatusIndicator status={ext.ui?.status || (ext.tool_count > 0 ? 'online' : 'unknown')} />
                              <span className="text-strong">{ext.name}</span>
                              {ext.tool_count > 0 && (
                                <span className="text-muted text-xs">
                                  ({ext.tool_count} tool{ext.tool_count > 1 ? 's' : ''})
                                </span>
                              )}
                            </div>
                            
                            {/* Nested items for UI and Services */}
                            {hasNested && (
                              <div className="dashboard-indented-tight">
                                {ext.ui?.url && (
                                  <div className="dashboard-row-tight">
                                    <StatusIndicator status={ext.ui.status || 'unknown'} />
                                    <span className="dashboard-secondary-text">UI</span>
                                  </div>
                                )}
                                {ext.services && ext.services.map(svc => (
                                  <div key={svc.name} className="dashboard-row-tight">
                                    <StatusIndicator status={svc.status || 'unknown'} />
                                    <span className="dashboard-secondary-text">{svc.name}</span>
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* External Services */}
                {Object.keys(externalServices).length > 0 && (
                  <div>
                    <div className="dashboard-row-tight mb-xs">
                      <span className="icon-success">✓</span>
                      <span className="text-strong fw-semibold">External</span>
                    </div>
                    <div className="dashboard-indented">
                      {Object.entries(externalServices).map(([name, service]) => (
                        <div key={name} className="dashboard-row-tight">
                          <StatusIndicator status={service.status || 'unknown'} />
                          <span className="text-strong">{name}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
