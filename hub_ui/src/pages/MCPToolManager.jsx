import React, { useState, useEffect } from 'react';
import { MCPApi } from '../lib/mcpApi';
import { ConfigAPI } from '../lib/api';
import Button from '../components/common/Button';
import LoadingSpinner from '../components/common/LoadingSpinner';

function MCPToolManager() {
  const [tools, setTools] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [newServerUrl, setNewServerUrl] = useState('');
  const [addingServer, setAddingServer] = useState(false);
  const [expandedServers, setExpandedServers] = useState({});
  const [expandedExtensions, setExpandedExtensions] = useState({});
  const [toast, setToast] = useState(null);

  useEffect(() => {
    loadTools();
  }, []);

  const loadTools = async () => {
    try {
      setLoading(true);
      const data = await MCPApi.getAllTools();
      setTools(data);
      setError(null);
    } catch (err) {
      setError(`Failed to load tools: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const showToast = (message, type = 'success') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 5000);
  };

  const handleAddServer = async () => {
    if (!newServerUrl.trim()) {
      showToast('Please enter a valid URL', 'error');
      return;
    }

    setAddingServer(true);
    try {
      const result = await MCPApi.addServer(newServerUrl);
      showToast(result.message || 'Server added successfully');
      setNewServerUrl('');
      await loadTools();
    } catch (err) {
      showToast(`Failed to add server: ${err.message}`, 'error');
    } finally {
      setAddingServer(false);
    }
  };

  const handleDeleteServer = async (serverId) => {
    if (!confirm(`Are you sure you want to remove server "${serverId}"?`)) {
      return;
    }

    try {
      const result = await MCPApi.deleteServer(serverId);
      showToast(result.message || 'Server removed successfully');
      await loadTools();
    } catch (err) {
      showToast(`Failed to remove server: ${err.message}`, 'error');
    }
  };

  const handleToggleServer = async (serverId, currentlyEnabled) => {
    try {
      await MCPApi.updateServer(serverId, { enabled: !currentlyEnabled });
      showToast(`Server ${!currentlyEnabled ? 'enabled' : 'disabled'}`);
      await loadTools();
    } catch (err) {
      showToast(`Failed to update server: ${err.message}`, 'error');
    }
  };

  const handleToggleRemoteTool = async (serverId, toolName, currentlyEnabled) => {
    try {
      await MCPApi.updateServer(serverId, {
        tool_updates: {
          [toolName]: { enabled: !currentlyEnabled }
        }
      });
      showToast(`Tool ${!currentlyEnabled ? 'enabled' : 'disabled'}`);
      await loadTools();
    } catch (err) {
      showToast(`Failed to update tool: ${err.message}`, 'error');
    }
  };

  const handleToggleExtension = async (extName, currentlyEnabled) => {
    try {
      await ConfigAPI.updateExtension(extName, { enabled: !currentlyEnabled });
      showToast(`Extension ${!currentlyEnabled ? 'enabled' : 'disabled'}`);
      await loadTools();
    } catch (err) {
      showToast(`Failed to update extension: ${err.message}`, 'error');
    }
  };

  const handleToggleLocalTool = async (toolName, currentConfig) => {
    try {
      await ConfigAPI.updateTool(toolName, {
        ...currentConfig,
        enabled_in_mcp: !currentConfig.enabled_in_mcp
      });
      showToast(`Tool ${!currentConfig.enabled_in_mcp ? 'enabled' : 'disabled'} in MCP`);
      await loadTools();
    } catch (err) {
      showToast(`Failed to update tool: ${err.message}`, 'error');
    }
  };

  const toggleServer = (serverId) => {
    setExpandedServers(prev => ({ ...prev, [serverId]: !prev[serverId] }));
  };

  const toggleExtension = (extName) => {
    setExpandedExtensions(prev => ({ ...prev, [extName]: !prev[extName] }));
  };

  if (loading) {
    return (
      <div className="page-container">
        <LoadingSpinner message="Loading MCP tools..." />
      </div>
    );
  }

  if (error) {
    return (
      <div className="page-container">
        <div className="page-header">
          <div>
            <h1>🔧 MCP Tool Manager</h1>
            <p className="page-subtitle">Manage remote MCP servers and local extension tools</p>
          </div>
        </div>
        <div className="error-message">
          {error}
        </div>
        <Button onClick={loadTools}>Retry</Button>
      </div>
    );
  }

  const remoteServers = tools?.remote_mcp_servers || [];
  const extensions = tools?.extensions || [];

  return (
    <div className="page-container">
      {toast && (
        <div className={`toast toast-${toast.type}`}>
          {toast.message}
        </div>
      )}

      <div className="page-header">
        <div>
          <h1>🔧 MCP Tool Manager</h1>
          <p className="page-subtitle">Manage remote MCP servers and local extension tools</p>
        </div>
      </div>

      <div className="warning-banner" style={{ marginBottom: '24px', padding: '16px', background: 'rgba(255, 193, 7, 0.1)', border: '1px solid rgba(255, 193, 7, 0.3)', borderRadius: '8px', color: '#ffc107' }}>
        <strong>⚠️ Note:</strong> Changes require Luna restart to take effect
      </div>

      {/* Add Remote MCP Server */}
      <div className="extension-card" style={{ marginBottom: '24px' }}>
        <h2 style={{ margin: '0 0 16px 0', fontSize: '20px', color: '#e8eaed' }}>Add Remote MCP Server</h2>
        <div style={{ display: 'flex', gap: '12px' }}>
          <input
            type="text"
            value={newServerUrl}
            onChange={(e) => setNewServerUrl(e.target.value)}
            placeholder="Paste Smithery MCP URL here..."
            disabled={addingServer}
            className="form-input"
            style={{ flex: 1 }}
            onKeyPress={(e) => {
              if (e.key === 'Enter' && newServerUrl.trim()) handleAddServer();
            }}
          />
          <Button
            onClick={handleAddServer}
            disabled={addingServer || !newServerUrl.trim()}
          >
            {addingServer ? 'Adding...' : 'Add Server'}
          </Button>
        </div>
      </div>

      {/* Remote MCP Servers */}
      <div style={{ marginBottom: '32px' }}>
        <h2 style={{ fontSize: '24px', color: '#e8eaed', marginBottom: '16px' }}>Remote MCP Servers ({remoteServers.length})</h2>
        {remoteServers.length === 0 ? (
          <div className="empty-state" style={{ padding: '40px 20px' }}>
            <div className="empty-state-icon" style={{ fontSize: '48px' }}>🌐</div>
            <h3 style={{ fontSize: '18px', color: '#9aa0a6', margin: '0' }}>No remote MCP servers configured</h3>
            <p style={{ color: '#9aa0a6', fontSize: '14px', marginTop: '8px' }}>Add a Smithery MCP server URL above to get started</p>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {remoteServers.map(server => (
              <div key={server.server_id} className="extension-card">
                <div className="extension-card-header">
                  <div className="extension-card-title" style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <button
                      onClick={() => toggleServer(server.server_id)}
                      style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '18px', color: '#8ab4f8', padding: 0 }}
                    >
                      {expandedServers[server.server_id] ? '▼' : '▶'}
                    </button>
                    <div>
                      <h3>{server.server_id}</h3>
                      <div className="extension-stats">
                        <div className="stat">
                          <span className="stat-icon">🛠️</span>
                          <span>{server.tool_count} tools</span>
                        </div>
                      </div>
                    </div>
                  </div>
                  <label className="toggle-switch">
                    <input
                      type="checkbox"
                      checked={server.enabled}
                      onChange={() => handleToggleServer(server.server_id, server.enabled)}
                    />
                    <span className="toggle-slider"></span>
                  </label>
                </div>

                <div className="extension-card-actions">
                  <Button 
                    variant="danger" 
                    onClick={() => handleDeleteServer(server.server_id)}
                    size="sm"
                  >
                    Delete Server
                  </Button>
                </div>

                {expandedServers[server.server_id] && (
                  <div style={{ marginTop: '20px', paddingTop: '20px', borderTop: '1px solid #3c4043' }}>
                    <div className="tools-list">
                      {Object.entries(server.tools || {}).map(([toolName, toolConfig]) => (
                        <div key={toolName} className="tool-card">
                          <div className="tool-header">
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                              <div style={{ flex: 1 }}>
                                <h3>{toolName}</h3>
                                {toolConfig.docstring && (
                                  <p className="tool-description">
                                    {toolConfig.docstring.substring(0, 200)}
                                    {toolConfig.docstring.length > 200 ? '...' : ''}
                                  </p>
                                )}
                              </div>
                              <label className="checkbox-label">
                                <input
                                  type="checkbox"
                                  checked={toolConfig.enabled}
                                  onChange={() => handleToggleRemoteTool(server.server_id, toolName, toolConfig.enabled)}
                                />
                                <span>Enabled</span>
                              </label>
                            </div>
                          </div>
                          {toolConfig.input_schema && (
                            <details style={{ marginTop: '12px' }}>
                              <summary style={{ cursor: 'pointer', color: '#8ab4f8', fontSize: '14px' }}>View Schema</summary>
                              <pre style={{ background: '#28292c', padding: '12px', borderRadius: '4px', overflow: 'auto', maxHeight: '200px', fontSize: '12px', marginTop: '8px' }}>
                                {JSON.stringify(toolConfig.input_schema, null, 2)}
                              </pre>
                            </details>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Local Extension Tools */}
      <div>
        <h2 style={{ fontSize: '24px', color: '#e8eaed', marginBottom: '16px' }}>Local Extension Tools ({extensions.length})</h2>
        {extensions.length === 0 ? (
          <div className="empty-state" style={{ padding: '40px 20px' }}>
            <div className="empty-state-icon" style={{ fontSize: '48px' }}>🔧</div>
            <h3 style={{ fontSize: '18px', color: '#9aa0a6', margin: '0' }}>No extensions with tools found</h3>
            <p style={{ color: '#9aa0a6', fontSize: '14px', marginTop: '8px' }}>Install extensions from the Extension Manager to see their tools here</p>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {extensions.map(ext => (
              <div key={ext.name} className="extension-card">
                <div className="extension-card-header">
                  <div className="extension-card-title" style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <button
                      onClick={() => toggleExtension(ext.name)}
                      style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '18px', color: '#8ab4f8', padding: 0 }}
                    >
                      {expandedExtensions[ext.name] ? '▼' : '▶'}
                    </button>
                    <div>
                      <h3>{ext.name}</h3>
                      <div className="extension-stats">
                        <div className="stat">
                          <span className="stat-icon">🛠️</span>
                          <span>{ext.tool_count} tools</span>
                        </div>
                      </div>
                    </div>
                  </div>
                  <label className="toggle-switch">
                    <input
                      type="checkbox"
                      checked={ext.enabled}
                      onChange={() => handleToggleExtension(ext.name, ext.enabled)}
                    />
                    <span className="toggle-slider"></span>
                  </label>
                </div>

                {expandedExtensions[ext.name] && (
                  <div style={{ marginTop: '20px', paddingTop: '20px', borderTop: '1px solid #3c4043' }}>
                    <div className="tools-list">
                      {ext.tools.map(tool => (
                        <div key={tool.name} className="tool-card">
                          <div className="tool-header">
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '16px' }}>
                              <div style={{ flex: 1 }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap', marginBottom: '4px' }}>
                                  <h3 style={{ margin: 0 }}>{tool.name}</h3>
                                  {tool.passthrough && (
                                    <span className="version-tag" style={{ background: 'rgba(76, 175, 80, 0.15)', color: '#4caf50' }}>
                                      Passthrough
                                    </span>
                                  )}
                                </div>
                                {tool.docstring && (
                                  <p className="tool-description">
                                    {tool.docstring.split('\n')[0].substring(0, 150)}
                                    {tool.docstring.length > 150 ? '...' : ''}
                                  </p>
                                )}
                              </div>
                              <label className="checkbox-label">
                                <input
                                  type="checkbox"
                                  checked={tool.enabled_in_mcp}
                                  onChange={() => handleToggleLocalTool(tool.name, tool)}
                                />
                                <span>MCP Enabled</span>
                              </label>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default MCPToolManager;

