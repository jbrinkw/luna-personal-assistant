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
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '30px' }}>
        
        {/* Left Column */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '30px' }}>
          
          {/* Active UIs */}
          <Card>
            <CardTitle>ACTIVE UIs</CardTitle>
            <CardContent>
              {activeUIs.length === 0 ? (
                <p style={{ color: '#9aa0a6' }}>No UIs available</p>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  {activeUIs.map(item => (
                    <div key={`${item.type}-${item.name}`} style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                      <StatusIndicator status={item.status} />
                      <span style={{ color: '#e8eaed', flex: 1 }}>{item.name}</span>
                      <Button 
                        variant="secondary" 
                        onClick={() => {
                          if (item.type === 'extension') {
                            navigate(`/ext/${item.name}`);
                          } else {
                            window.open(item.url, '_blank');
                          }
                        }}
                        style={{ padding: '4px 12px', fontSize: '12px' }}
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
                <p style={{ color: '#9aa0a6' }}>No agents discovered</p>
              ) : (
                <>
                  <p style={{ color: '#9aa0a6', marginBottom: '12px' }}>Available Agents:</p>
                  <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
                    {agents.map(agent => (
                      <li key={agent} style={{ padding: '6px 0', color: '#e8eaed' }}>
                        • {agent}
                      </li>
                    ))}
                  </ul>
                  <p style={{ color: '#9aa0a6', marginTop: '12px', fontSize: '14px' }}>
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
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                
                {/* System Status */}
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                    <span style={{ color: '#81c995' }}>✓</span>
                    <span style={{ color: '#e8eaed', fontWeight: 600 }}>System Status</span>
                  </div>
                  <div style={{ paddingLeft: '24px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <StatusIndicator status={agentApiStatus} />
                      <span style={{ color: '#e8eaed' }}>Agent API</span>
                      <span style={{ color: '#9aa0a6', fontSize: '12px' }}>{AGENT_API}</span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <StatusIndicator status={mcpStatus} />
                      <span style={{ color: '#e8eaed' }}>MCP Server</span>
                      <span style={{ color: '#9aa0a6', fontSize: '12px' }}>{MCP_API}</span>
                    </div>
                    <div style={{ color: '#9aa0a6', fontSize: '14px', marginTop: '4px' }}>
                      {agents.length} Active Agents
                    </div>
                  </div>
                </div>

                {/* Extensions */}
                {relevantExtensions.length > 0 && (
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                      <span style={{ color: totalToolCount > 0 ? '#ff9800' : '#81c995' }}>
                        {totalToolCount > 0 ? '⚠️' : '✓'}
                      </span>
                      <span style={{ color: '#e8eaed', fontWeight: 600 }}>
                        Extensions {totalToolCount > 0 && `(${totalToolCount} tools)`}
                      </span>
                    </div>
                    <div style={{ paddingLeft: '24px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                      {relevantExtensions.map(ext => {
                        const hasNested = (ext.ui?.url) || (ext.services && ext.services.length > 0);
                        
                        return (
                          <div key={ext.name} style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                              <StatusIndicator status={ext.ui?.status || (ext.tool_count > 0 ? 'online' : 'unknown')} />
                              <span style={{ color: '#e8eaed' }}>{ext.name}</span>
                              {ext.tool_count > 0 && (
                                <span style={{ color: '#9aa0a6', fontSize: '12px' }}>
                                  ({ext.tool_count} tool{ext.tool_count > 1 ? 's' : ''})
                                </span>
                              )}
                            </div>
                            
                            {/* Nested items for UI and Services */}
                            {hasNested && (
                              <div style={{ paddingLeft: '24px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                                {ext.ui?.url && (
                                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                    <StatusIndicator status={ext.ui.status || 'unknown'} />
                                    <span style={{ color: '#9aa0a6', fontSize: '13px' }}>UI</span>
                                  </div>
                                )}
                                {ext.services && ext.services.map(svc => (
                                  <div key={svc.name} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                    <StatusIndicator status={svc.status || 'unknown'} />
                                    <span style={{ color: '#9aa0a6', fontSize: '13px' }}>{svc.name}</span>
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
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                      <span style={{ color: '#81c995' }}>✓</span>
                      <span style={{ color: '#e8eaed', fontWeight: 600 }}>External</span>
                    </div>
                    <div style={{ paddingLeft: '24px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                      {Object.entries(externalServices).map(([name, service]) => (
                        <div key={name} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <StatusIndicator status={service.status || 'unknown'} />
                          <span style={{ color: '#e8eaed' }}>{name}</span>
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
