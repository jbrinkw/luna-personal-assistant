import React, { useState, useEffect } from 'react';
import { MCPApi } from '../lib/mcpApi';
import { ConfigAPI } from '../lib/api';
import Button from '../components/common/Button';
import LoadingSpinner from '../components/common/LoadingSpinner';

function MCPToolManager() {
  // Mode toggle ('mcp' or 'agent')
  const [mode, setMode] = useState('mcp');
  
  // MCP mode state
  const [tools, setTools] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [newServerUrl, setNewServerUrl] = useState('');
  const [addingServer, setAddingServer] = useState(false);
  const [expandedServers, setExpandedServers] = useState({});
  const [expandedExtensions, setExpandedExtensions] = useState({});
  const [toast, setToast] = useState(null);
  
  // Local multi-MCP servers
  const [localServers, setLocalServers] = useState([]);
  const [activeServer, setActiveServer] = useState(null);
  const [serverTools, setServerTools] = useState([]);
  const [creatingLocal, setCreatingLocal] = useState(false);
  const [newLocalName, setNewLocalName] = useState('');
  const [renameDraft, setRenameDraft] = useState('');
  const [showMCPApiKey, setShowMCPApiKey] = useState(false);
  const activeServerInfo = localServers.find(s => s.name === activeServer) || null;
  
  // Agent Presets mode state
  const [builtInAgents, setBuiltInAgents] = useState([]);
  const [agentPresets, setAgentPresets] = useState([]);
  const [activePreset, setActivePreset] = useState(null);
  const [presetTools, setPresetTools] = useState([]);
  const [newPresetName, setNewPresetName] = useState('');
  const [newPresetBase, setNewPresetBase] = useState('');
  const [creatingPreset, setCreatingPreset] = useState(false);
  const [sharedApiKey, setSharedApiKey] = useState('');
  const [showApiKey, setShowApiKey] = useState(false);
  const [presetRenameDraft, setPresetRenameDraft] = useState('');
  const activePresetInfo = agentPresets.find(p => p.name === activePreset) || null;

  useEffect(() => {
    loadTools();
    loadLocalServers();
  }, []);

  useEffect(() => {
    if (activeServer) {
      loadServerTools(activeServer);
    }
  }, [activeServer]);

  // Keep renameDraft synced with the selected server
  useEffect(() => {
    const s = localServers.find(x => x.name === activeServer);
    setRenameDraft(s ? s.name : '');
  }, [activeServer, localServers]);
  
  // Load agent data when switching to agent mode
  useEffect(() => {
    if (mode === 'agent') {
      loadBuiltInAgents();
      loadAgentPresets();
      loadSharedApiKey();
    }
  }, [mode]);
  
  // Load preset tools when active preset changes
  useEffect(() => {
    if (mode === 'agent' && activePreset) {
      loadPresetTools(activePreset);
    }
  }, [mode, activePreset]);
  
  // Keep presetRenameDraft synced with active preset
  useEffect(() => {
    const p = agentPresets.find(x => x.name === activePreset);
    setPresetRenameDraft(p ? p.name : '');
  }, [activePreset, agentPresets]);

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

  // Local server helpers
  const loadLocalServers = async () => {
    try {
      const data = MCPApi.listLocalServers
        ? await MCPApi.listLocalServers()
        : await (await fetch('/api/supervisor/mcp-servers/list')).json();
      const list = data.servers || [];
      setLocalServers(list);
      if (!activeServer && list.length > 0) {
        const mainEntry = list.find(s => s.name === 'main');
        setActiveServer((mainEntry && mainEntry.name) || list[0].name);
      }
      // Keep rename input in sync with active server
      const current = list.find(s => s.name === activeServer);
      setRenameDraft(current ? current.name : '');
    } catch (err) {
      console.error('Failed to load local servers', err);
    }
  };

  const loadServerTools = async (name) => {
    try {
      const data = MCPApi.getServerTools
        ? await MCPApi.getServerTools(name)
        : await (await fetch(`/api/supervisor/mcp-servers/${encodeURIComponent(name)}/tools`)).json();
      setServerTools(data.tools || []);
    } catch (err) {
      console.error('Failed to load server tools', err);
    }
  };

  const createLocalServer = async () => {
    const name = newLocalName.trim();
    if (!name) {
      showToast('Enter a server name', 'error');
      return;
    }
    setCreatingLocal(true);
    try {
      let result;
      if (MCPApi.createLocalServer) {
        result = await MCPApi.createLocalServer(name);
      } else {
        const res = await fetch('/api/supervisor/mcp-servers/create', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name })
        });
        if (!res.ok) {
          const text = await res.text();
          throw new Error(text || `HTTP ${res.status}`);
        }
        result = await res.json();
      }
      setNewLocalName('');
      await loadLocalServers();
      setActiveServer(name);
      const keyText = result?.server?.api_key ? ` API Key: ${result.server.api_key}` : '';
      showToast(`Server created.${keyText ? ` ${keyText}` : ''}`);
    } catch (err) {
      showToast(`Failed to create server: ${err.message}`, 'error');
    } finally {
      setCreatingLocal(false);
    }
  };

  const deleteLocalServer = async (name) => {
    if (!confirm(`Delete server ${name}?`)) return;
    try {
      if (MCPApi.deleteLocalServer) {
        await MCPApi.deleteLocalServer(name);
      } else {
        await fetch(`/api/supervisor/mcp-servers/${encodeURIComponent(name)}`, { method: 'DELETE' });
      }
      await loadLocalServers();
      if (activeServer === name) setActiveServer(null);
      setServerTools([]);
      showToast('Server deleted');
    } catch (err) {
      showToast(`Failed to delete: ${err.message}`, 'error');
    }
  };

  const toggleLocalServer = async (name, enabled) => {
    try {
      if (MCPApi.updateLocalServer) {
        await MCPApi.updateLocalServer(name, { enabled: !enabled });
      } else {
        await fetch(`/api/supervisor/mcp-servers/${encodeURIComponent(name)}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ enabled: !enabled }) });
      }
      await loadLocalServers();
      showToast(`Server ${!enabled ? 'enabled' : 'disabled'}`);
    } catch (err) {
      showToast(`Failed to update: ${err.message}`, 'error');
    }
  };

  const toggleServerTool = async (toolName, currentlyEnabled) => {
    if (!activeServer) return;
    try {
      const payload = { tool_updates: { [toolName]: { enabled_in_mcp: !currentlyEnabled } } };
      if (MCPApi.updateLocalServer) {
        await MCPApi.updateLocalServer(activeServer, payload);
      } else {
        await fetch(`/api/supervisor/mcp-servers/${encodeURIComponent(activeServer)}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
      }
      await loadServerTools(activeServer);
    } catch (err) {
      showToast(`Failed to update tool: ${err.message}`, 'error');
    }
  };

  const copyApiKey = async (key) => {
    try {
      await navigator.clipboard.writeText(key);
      showToast('API key copied');
    } catch (err) {
      showToast(`Failed to copy: ${err.message}`, 'error');
    }
  };

  const regenerateApiKey = async () => {
    if (!activeServerInfo || activeServerInfo.name === 'main') return;
    try {
      if (MCPApi.regenerateLocalServerKey) {
        await MCPApi.regenerateLocalServerKey(activeServerInfo.name);
      } else {
        const res = await fetch(`/api/supervisor/mcp-servers/${encodeURIComponent(activeServerInfo.name)}/regenerate-key`, { method: 'POST' });
        if (!res.ok) {
          const text = await res.text();
          throw new Error(text || `HTTP ${res.status}`);
        }
      }
      await loadLocalServers();
      showToast('API key regenerated');
    } catch (err) {
      showToast(`Failed to regenerate key: ${err.message}`, 'error');
    }
  };

  // Bulk enable/disable operations
  const toggleAllExtensionTools = async (enabled) => {
    if (!activeServer) return;
    try {
      const toolUpdates = {};
      extensions.forEach(ext => {
        ext.tools.forEach(tool => {
          toolUpdates[tool.name] = { enabled_in_mcp: enabled };
        });
      });
      
      const payload = { tool_updates: toolUpdates };
      if (MCPApi.updateLocalServer) {
        await MCPApi.updateLocalServer(activeServer, payload);
      } else {
        await fetch(`/api/supervisor/mcp-servers/${encodeURIComponent(activeServer)}`, { 
          method: 'PATCH', 
          headers: { 'Content-Type': 'application/json' }, 
          body: JSON.stringify(payload) 
        });
      }
      await loadServerTools(activeServer);
      showToast(`${enabled ? 'Enabled' : 'Disabled'} all extension tools`);
    } catch (err) {
      showToast(`Failed to update tools: ${err.message}`, 'error');
    }
  };

  const toggleAllRemoteMCPTools = async (enabled) => {
    if (!activeServer) return;
    try {
      const toolUpdates = {};
      remoteServers.forEach(server => {
        Object.keys(server.tools || {}).forEach(toolName => {
          toolUpdates[toolName] = { enabled_in_mcp: enabled };
        });
      });
      
      const payload = { tool_updates: toolUpdates };
      if (MCPApi.updateLocalServer) {
        await MCPApi.updateLocalServer(activeServer, payload);
      } else {
        await fetch(`/api/supervisor/mcp-servers/${encodeURIComponent(activeServer)}`, { 
          method: 'PATCH', 
          headers: { 'Content-Type': 'application/json' }, 
          body: JSON.stringify(payload) 
        });
      }
      await loadServerTools(activeServer);
      showToast(`${enabled ? 'Enabled' : 'Disabled'} all remote MCP tools`);
    } catch (err) {
      showToast(`Failed to update tools: ${err.message}`, 'error');
    }
  };

  const toggleAllToolsGlobal = async (enabled) => {
    if (!activeServer) return;
    try {
      const toolUpdates = {};
      
      // Add all extension tools
      extensions.forEach(ext => {
        ext.tools.forEach(tool => {
          toolUpdates[tool.name] = { enabled_in_mcp: enabled };
        });
      });
      
      // Add all remote MCP tools
      remoteServers.forEach(server => {
        Object.keys(server.tools || {}).forEach(toolName => {
          toolUpdates[toolName] = { enabled_in_mcp: enabled };
        });
      });
      
      const payload = { tool_updates: toolUpdates };
      if (MCPApi.updateLocalServer) {
        await MCPApi.updateLocalServer(activeServer, payload);
      } else {
        await fetch(`/api/supervisor/mcp-servers/${encodeURIComponent(activeServer)}`, { 
          method: 'PATCH', 
          headers: { 'Content-Type': 'application/json' }, 
          body: JSON.stringify(payload) 
        });
      }
      await loadServerTools(activeServer);
      showToast(`${enabled ? 'Enabled' : 'Disabled'} all tools globally`);
    } catch (err) {
      showToast(`Failed to update tools: ${err.message}`, 'error');
    }
  };

  const toggleAllToolsInExtension = async (extName, enabled) => {
    if (!activeServer) return;
    try {
      const ext = extensions.find(e => e.name === extName);
      if (!ext) return;
      
      const toolUpdates = {};
      ext.tools.forEach(tool => {
        toolUpdates[tool.name] = { enabled_in_mcp: enabled };
      });
      
      const payload = { tool_updates: toolUpdates };
      if (MCPApi.updateLocalServer) {
        await MCPApi.updateLocalServer(activeServer, payload);
      } else {
        await fetch(`/api/supervisor/mcp-servers/${encodeURIComponent(activeServer)}`, { 
          method: 'PATCH', 
          headers: { 'Content-Type': 'application/json' }, 
          body: JSON.stringify(payload) 
        });
      }
      await loadServerTools(activeServer);
      showToast(`${enabled ? 'Enabled' : 'Disabled'} all tools in ${extName}`);
    } catch (err) {
      showToast(`Failed to update tools: ${err.message}`, 'error');
    }
  };

  const toggleAllToolsInRemoteServer = async (serverId, enabled) => {
    if (!activeServer) return;
    try {
      const server = remoteServers.find(s => s.server_id === serverId);
      if (!server) return;
      
      const toolUpdates = {};
      Object.keys(server.tools || {}).forEach(toolName => {
        toolUpdates[toolName] = { enabled_in_mcp: enabled };
      });
      
      const payload = { tool_updates: toolUpdates };
      if (MCPApi.updateLocalServer) {
        await MCPApi.updateLocalServer(activeServer, payload);
      } else {
        await fetch(`/api/supervisor/mcp-servers/${encodeURIComponent(activeServer)}`, { 
          method: 'PATCH', 
          headers: { 'Content-Type': 'application/json' }, 
          body: JSON.stringify(payload) 
        });
      }
      await loadServerTools(activeServer);
      showToast(`${enabled ? 'Enabled' : 'Disabled'} all tools in ${serverId}`);
    } catch (err) {
      showToast(`Failed to update tools: ${err.message}`, 'error');
    }
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

  const handleToggleExtension = async (extName, currentlyEnabled) => {
    try {
      await ConfigAPI.updateExtension(extName, { enabled: !currentlyEnabled });
      showToast(`Extension ${!currentlyEnabled ? 'enabled' : 'disabled'}`);
      await loadTools();
      if (activeServer) {
        await loadServerTools(activeServer);
      }
    } catch (err) {
      showToast(`Failed to update extension: ${err.message}`, 'error');
    }
  };

  // ----------------------------
  // Agent Preset API Functions
  // ----------------------------
  
  const loadBuiltInAgents = async () => {
    try {
      const data = await fetch('/api/supervisor/agents/built-in').then(r => r.json());
      setBuiltInAgents(data.agents || []);
      if (!newPresetBase && data.agents.length > 0) {
        setNewPresetBase(data.agents[0]);
      }
    } catch (err) {
      console.error('Failed to load built-in agents', err);
    }
  };
  
  const loadAgentPresets = async () => {
    try {
      const data = await fetch('/api/supervisor/agents/list').then(r => r.json());
      setAgentPresets(data.agents || []);
      if (!activePreset && data.agents.length > 0) {
        setActivePreset(data.agents[0].name);
      }
    } catch (err) {
      console.error('Failed to load agent presets', err);
    }
  };
  
  const loadPresetTools = async (name) => {
    try {
      const data = await fetch(`/api/supervisor/agents/${encodeURIComponent(name)}/tools`).then(r => r.json());
      setPresetTools(data.tools || []);
    } catch (err) {
      console.error('Failed to load preset tools', err);
    }
  };
  
  const loadSharedApiKey = async () => {
    try {
      const data = await fetch('/api/supervisor/agents/api-key').then(r => r.json());
      setSharedApiKey(data.api_key || '');
    } catch (err) {
      console.error('Failed to load shared API key', err);
    }
  };
  
  const createAgentPreset = async () => {
    const name = newPresetName.trim();
    if (!name) {
      showToast('Enter an agent preset name', 'error');
      return;
    }
    if (!newPresetBase) {
      showToast('Select a base agent', 'error');
      return;
    }
    setCreatingPreset(true);
    try {
      await fetch('/api/supervisor/agents/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, base_agent: newPresetBase })
      });
      setNewPresetName('');
      await loadAgentPresets();
      setActivePreset(name);
      showToast('Agent preset created');
    } catch (err) {
      showToast(`Failed to create preset: ${err.message}`, 'error');
    } finally {
      setCreatingPreset(false);
    }
  };
  
  const deleteAgentPreset = async (name) => {
    if (!confirm(`Delete agent preset ${name}?`)) return;
    try {
      await fetch(`/api/supervisor/agents/${encodeURIComponent(name)}`, { method: 'DELETE' });
      await loadAgentPresets();
      if (activePreset === name) setActivePreset(null);
      setPresetTools([]);
      showToast('Preset deleted');
    } catch (err) {
      showToast(`Failed to delete: ${err.message}`, 'error');
    }
  };
  
  const updateAgentPreset = async (name, updates) => {
    try {
      await fetch(`/api/supervisor/agents/${encodeURIComponent(name)}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates)
      });
    } catch (err) {
      showToast(`Failed to update: ${err.message}`, 'error');
      throw err;
    }
  };
  
  const togglePresetTool = async (toolName, currentlyEnabled) => {
    if (!activePreset) return;
    try {
      await updateAgentPreset(activePreset, {
        tool_updates: { [toolName]: { enabled: !currentlyEnabled } }
      });
      await loadPresetTools(activePreset);
    } catch (err) {
      showToast(`Failed to update tool: ${err.message}`, 'error');
    }
  };
  
  const regenerateSharedKey = async () => {
    if (!confirm('Regenerate shared agent API key? This will affect all agents.')) return;
    try {
      const data = await fetch('/api/supervisor/agents/regenerate-key', { method: 'POST' }).then(r => r.json());
      setSharedApiKey(data.api_key);
      showToast('API key regenerated');
    } catch (err) {
      showToast(`Failed to regenerate key: ${err.message}`, 'error');
    }
  };

  // Old global toggle removed; we now toggle per active server

  const toggleServer = (serverId) => {
    setExpandedServers(prev => ({ ...prev, [serverId]: !prev[serverId] }));
  };

  const toggleExtension = (extName) => {
    setExpandedExtensions(prev => ({ ...prev, [extName]: !prev[extName] }));
  };

  const isToolEnabledForActive = (toolName) => {
    if (mode === 'agent') {
      return !!(presetTools.find(t => t.name === toolName)?.enabled);
    }
    return !!(serverTools.find(t => t.name === toolName)?.enabled_in_mcp);
  };

  // Helper to count active tools in a remote server
  const getRemoteServerActiveCount = (server) => {
    if (!server.tools) return 0;
    const toolNames = Object.keys(server.tools);
    return toolNames.filter(toolName => isToolEnabledForActive(toolName)).length;
  };

  // Helper to count active tools in an extension
  const getExtensionActiveCount = (ext) => {
    if (!ext.tools) return 0;
    return ext.tools.filter(tool => isToolEnabledForActive(tool.name)).length;
  };

  // Helper to get total active/total counts for all remote servers
  const getRemoteTotalCounts = () => {
    let active = 0;
    let total = 0;
    remoteServers.forEach(server => {
      active += getRemoteServerActiveCount(server);
      total += server.tool_count || 0;
    });
    return { active, total };
  };

  // Helper to get total active/total counts for all extensions
  const getExtensionTotalCounts = () => {
    let active = 0;
    let total = 0;
    extensions.forEach(ext => {
      active += getExtensionActiveCount(ext);
      total += ext.tool_count || 0;
    });
    return { active, total };
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
            <h1>🔧 Tool/MCP Manager</h1>
            <p className="page-subtitle">Manage local MCP servers, remote MCP servers, and extension tools</p>
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
            <h1>🔧 Tool/MCP Manager</h1>
            <p className="page-subtitle">
              {mode === 'mcp' 
                ? 'Manage local MCP servers, remote MCP servers, and extension tools'
                : 'Create and manage agent presets with custom tool access'}
            </p>
          </div>
          <div className="mode-toggle-buttons">
            <Button 
              variant={mode === 'mcp' ? 'primary' : 'secondary'}
              onClick={() => setMode('mcp')}
            >
              MCP
            </Button>
            <Button 
              variant={mode === 'agent' ? 'primary' : 'secondary'}
              onClick={() => setMode('agent')}
            >
              Agent Presets
            </Button>
          </div>
        </div>

      <div className="warning-banner">
        <strong>⚠️ Note:</strong> Changes require Luna restart to take effect
      </div>

      {/* Selector pills - shared structure, conditional content */}
      <div className="mcp-servers-section">
        <div className="mcp-server-selector">
          <div className="server-pills">
            {mode === 'mcp' ? (
              // MCP Server pills
              localServers.map(s => {
                const path = `/api/mcp-${s.name}`;
                const count = typeof s.tool_count === 'number' ? s.tool_count : null;
                return (
                  <Button
                    key={s.name}
                    variant={s.name === activeServer ? 'primary' : 'secondary'}
                    onClick={() => setActiveServer(s.name)}
                    className="server-pill"
                    title={`${path}`}
                  >
                    <span className="server-pill-name">{s.name}</span>
                    <span className="server-pill-path">{path}</span>
                    {count !== null && <span className="server-pill-count">• {count} tools</span>}
                    {!s.enabled && <span className="server-pill-disabled">(disabled)</span>}
                  </Button>
                );
              })
            ) : (
              // Agent Preset pills
              agentPresets.map(preset => (
                <Button
                  key={preset.name}
                  variant={preset.name === activePreset ? 'primary' : 'secondary'}
                  onClick={() => setActivePreset(preset.name)}
                  className="server-pill"
                >
                  <span className="server-pill-name">{preset.name}</span>
                  <span className="server-pill-base">based on {preset.base_agent}</span>
                  {preset.tool_count !== null && <span className="server-pill-count">• {preset.tool_count} tools</span>}
                </Button>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Quick Actions - shared */}
      {(mode === 'mcp' ? activeServer : activePreset) && (
        <div className="bulk-actions-bar">
          <span className="bulk-actions-label">
            Quick Actions for {mode === 'mcp' ? activeServer : activePreset}:
          </span>
          <div className="bulk-actions-buttons">
            <Button 
              variant="secondary" 
              size="sm"
              onClick={() => toggleAllToolsGlobal(true)}
            >
              Enable All Tools
            </Button>
            <Button 
              variant="secondary" 
              size="sm"
              onClick={() => toggleAllToolsGlobal(false)}
            >
              Disable All Tools
            </Button>
          </div>
        </div>
      )}

      {/* Management Cards - shared structure, conditional content */}
      <div className="server-management-grid">
        {mode === 'mcp' ? (
          <>
            {/* MCP: Active Server Management */}
            {activeServerInfo && (
            <div className="extension-card">
              <h3 className="server-management-title">
                {activeServerInfo.name === 'main' ? 'Main MCP Server' : `Manage ${activeServerInfo.name}`}
              </h3>
              {activeServerInfo.name === 'main' ? (
                <p className="text-muted">GitHub OAuth is used for authentication on the main MCP server.</p>
              ) : (
                <>
                  <div className="server-management-section">
                    <label className="input-label">Server Name</label>
                    <div className="input-button-group">
                      <input
                        className="mcp-input"
                        value={renameDraft}
                        onChange={(e) => setRenameDraft(e.target.value)}
                        placeholder="Server name"
                      />
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={async () => {
                          const newName = (renameDraft || '').trim();
                          if (!activeServerInfo || !newName || newName === activeServerInfo.name) return;
                          try {
                            if (MCPApi.updateLocalServer) {
                              await MCPApi.updateLocalServer(activeServerInfo.name, { name: newName });
                            } else {
                              await fetch(`/api/supervisor/mcp-servers/${encodeURIComponent(activeServerInfo.name)}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name: newName }) });
                            }
                            setActiveServer(newName);
                            await loadLocalServers();
                            showToast('Server renamed');
                          } catch (err) {
                            showToast(`Rename failed: ${err.message}`, 'error');
                          }
                        }}
                      >
                        Save
                      </Button>
                      <Button
                        variant="danger"
                        size="sm"
                        onClick={() => deleteLocalServer(activeServerInfo.name)}
                      >
                        Delete
                      </Button>
                    </div>
                  </div>

                  <div className="server-management-section">
                    <label className="input-label">
                      API Key
                      <button 
                        onClick={() => setShowMCPApiKey(!showMCPApiKey)}
                        style={{ 
                          marginLeft: '8px', 
                          background: 'none', 
                          border: 'none', 
                          cursor: 'pointer', 
                          fontSize: '1.2rem' 
                        }}
                        title={showMCPApiKey ? 'Hide API key' : 'Show API key'}
                      >
                        {showMCPApiKey ? '🙈' : '👁️'}
                      </button>
                    </label>
                    <div className="api-key-display">
                      <code className="api-key-code">
                        {activeServerInfo.api_key 
                          ? (showMCPApiKey ? activeServerInfo.api_key : '••••••••••••••••••••••••••••••••')
                          : '—'}
                      </code>
                      <div className="api-key-actions">
                        <Button 
                          variant="secondary" 
                          size="sm"
                          onClick={() => copyApiKey(activeServerInfo.api_key || '')} 
                          disabled={!activeServerInfo.api_key}
                        >
                          Copy
                        </Button>
                        <Button 
                          variant="secondary" 
                          size="sm"
                          onClick={regenerateApiKey}
                        >
                          Regenerate
                        </Button>
                      </div>
                    </div>
                  </div>
                </>
              )}
            </div>
          )}

          {/* Create New Server */}
          <div className="extension-card">
            <h3 className="server-management-title">Create New MCP Server</h3>
            <div className="server-management-section">
              <label className="input-label">Server Name</label>
              <div className="input-button-group">
                <input
                  className="mcp-input"
                  placeholder="e.g., research, smarthome"
                  value={newLocalName}
                  onChange={e => setNewLocalName(e.target.value)}
                />
                <Button 
                  onClick={createLocalServer} 
                  disabled={creatingLocal}
                  size="sm"
                >
                  {creatingLocal ? 'Creating...' : 'Create'}
                </Button>
              </div>
              <p className="input-help-text">
                Each MCP server gets its own API endpoint and authentication
              </p>
            </div>
          </div>
          </>
        ) : (
          <>
            {/* Agent: Active Preset Management */}
            {activePresetInfo && (
              <div className="extension-card">
                <h3 className="server-management-title">Manage {activePresetInfo.name}</h3>
                
                <div className="server-management-section">
                  <label className="input-label">Preset Name</label>
                  <div className="input-button-group">
                    <input
                      className="mcp-input"
                      value={presetRenameDraft}
                      onChange={(e) => setPresetRenameDraft(e.target.value)}
                      placeholder="Preset name"
                    />
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={async () => {
                        const newName = (presetRenameDraft || '').trim();
                        if (!activePresetInfo || !newName || newName === activePresetInfo.name) return;
                        try {
                          await updateAgentPreset(activePresetInfo.name, { name: newName });
                          setActivePreset(newName);
                          await loadAgentPresets();
                          showToast('Preset renamed');
                        } catch (err) {
                          showToast(`Rename failed: ${err.message}`, 'error');
                        }
                      }}
                    >
                      Save
                    </Button>
                    <Button
                      variant="danger"
                      size="sm"
                      onClick={() => deleteAgentPreset(activePresetInfo.name)}
                    >
                      Delete
                    </Button>
                  </div>
                </div>

                <div className="server-management-section">
                  <label className="input-label">Base Agent</label>
                  <select 
                    className="mcp-input"
                    value={activePresetInfo.base_agent}
                    onChange={(e) => updateAgentPreset(activePresetInfo.name, { base_agent: e.target.value }).then(() => {
                      loadAgentPresets();
                      showToast('Base agent updated');
                    })}
                  >
                    {builtInAgents.map(ba => (
                      <option key={ba} value={ba}>{ba}</option>
                    ))}
                  </select>
                  <p className="input-help-text">The underlying agent implementation this preset uses</p>
                </div>

                <div className="server-management-section">
                  <label className="input-label">
                    Shared API Key
                    <button 
                      onClick={() => setShowApiKey(!showApiKey)}
                      style={{ 
                        marginLeft: '8px', 
                        background: 'none', 
                        border: 'none', 
                        cursor: 'pointer', 
                        fontSize: '1.2rem' 
                      }}
                      title={showApiKey ? 'Hide API key' : 'Show API key'}
                    >
                      {showApiKey ? '🙈' : '👁️'}
                    </button>
                  </label>
                  <div className="api-key-display">
                    <code className="api-key-code">
                      {showApiKey ? sharedApiKey : '••••••••••••••••••••••••••••••••'}
                    </code>
                    <div className="api-key-actions">
                      <Button 
                        variant="secondary" 
                        size="sm"
                        onClick={() => copyApiKey(sharedApiKey)} 
                        disabled={!sharedApiKey}
                      >
                        Copy
                      </Button>
                      <Button 
                        variant="secondary" 
                        size="sm"
                        onClick={regenerateSharedKey}
                      >
                        Regenerate
                      </Button>
                    </div>
                  </div>
                  <p className="input-help-text">All agents share this API key for authentication</p>
                </div>
              </div>
            )}

            {/* Agent: Create New Preset */}
            <div className="extension-card">
              <h3 className="server-management-title">Create New Agent Preset</h3>
              
              <div className="server-management-section">
                <label className="input-label">Preset Name</label>
                <input
                  className="mcp-input"
                  placeholder="e.g., smart_home_assistant"
                  value={newPresetName}
                  onChange={e => setNewPresetName(e.target.value)}
                />
              </div>

              <div className="server-management-section">
                <label className="input-label">Base Agent</label>
                <select 
                  className="mcp-input"
                  value={newPresetBase}
                  onChange={e => setNewPresetBase(e.target.value)}
                >
                  {builtInAgents.map(ba => (
                    <option key={ba} value={ba}>{ba}</option>
                  ))}
                </select>
                <p className="input-help-text">Select the underlying agent implementation</p>
              </div>

              <Button onClick={createAgentPreset} disabled={creatingPreset}>
                {creatingPreset ? 'Creating...' : 'Create Preset'}
              </Button>
            </div>
          </>
        )}
      </div>

      {/* Add Remote MCP Server - shared */}
      <div className="extension-card mcp-section-card">
        <h3 className="server-management-title">Add Remote MCP Server</h3>
        <div className="server-management-section">
          <label className="input-label">Smithery MCP Server URL</label>
          <div className="input-button-group">
            <input
              type="text"
              value={newServerUrl}
              onChange={(e) => setNewServerUrl(e.target.value)}
              placeholder="https://mcp.example.com/..."
              disabled={addingServer}
              className="mcp-input"
              onKeyPress={(e) => {
                if (e.key === 'Enter' && newServerUrl.trim()) handleAddServer();
              }}
            />
            <Button
              onClick={handleAddServer}
              disabled={addingServer || !newServerUrl.trim()}
              size="sm"
            >
              {addingServer ? 'Adding...' : 'Add Server'}
            </Button>
          </div>
          <p className="input-help-text">
            Connect to external MCP servers like Exa, Context7, and more
          </p>
        </div>
      </div>

      {/* Remote MCP Servers - Shared between both modes */}
      <div className="mcp-section">
        <div className="section-header">
          <h2 className="section-title">
            Remote MCP Servers ({remoteServers.length})
            {(mode === 'mcp' ? activeServer : activePreset) && remoteServers.length > 0 && (
              <span className="section-tool-count">
                {' • '}
                <span className="stat-active">{getRemoteTotalCounts().active}</span>
                <span className="stat-separator"> / </span>
                <span className="stat-total">{getRemoteTotalCounts().total}</span>
                {' tools active'}
              </span>
            )}
          </h2>
          {remoteServers.length > 0 && (mode === 'mcp' ? activeServer : activePreset) && (
            <div className="bulk-actions-buttons">
              <Button 
                variant="secondary" 
                size="sm"
                onClick={() => toggleAllRemoteMCPTools(true)}
              >
                Enable All
              </Button>
              <Button 
                variant="secondary" 
                size="sm"
                onClick={() => toggleAllRemoteMCPTools(false)}
              >
                Disable All
              </Button>
            </div>
          )}
        </div>
        {remoteServers.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon">🌐</div>
            <h3>No remote MCP servers configured</h3>
            <p>{mode === 'mcp' ? 'Add a Smithery MCP server URL above to get started' : 'Switch to MCP mode to add remote MCP servers'}</p>
          </div>
        ) : (
          <div className="cards-list">
            {remoteServers.map(server => (
              <div key={server.server_id} className="extension-card">
                <div className="extension-card-header">
                  <div className="extension-card-title-with-toggle">
                    <button
                      onClick={() => toggleServer(server.server_id)}
                      className="expand-toggle-btn"
                    >
                      {expandedServers[server.server_id] ? '▼' : '▶'}
                    </button>
                    <div>
                      <h3>{server.server_id}</h3>
                      <div className="extension-stats">
                        <div className="stat">
                          <span className="stat-icon">🛠️</span>
                          <span>
                            {(mode === 'mcp' ? activeServer : activePreset) ? (
                              <>
                                <span className="stat-active">{getRemoteServerActiveCount(server)}</span>
                                <span className="stat-separator"> / </span>
                                <span className="stat-total">{server.tool_count}</span>
                                <span> tools active</span>
                              </>
                            ) : (
                              <>{server.tool_count} tools</>
                            )}
                          </span>
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
                  {(mode === 'mcp' ? activeServer : activePreset) && (
                    <>
                      <Button 
                        variant="secondary" 
                        onClick={() => toggleAllToolsInRemoteServer(server.server_id, true)}
                        size="sm"
                      >
                        Enable All Tools
                      </Button>
                      <Button 
                        variant="secondary" 
                        onClick={() => toggleAllToolsInRemoteServer(server.server_id, false)}
                        size="sm"
                      >
                        Disable All Tools
                      </Button>
                    </>
                  )}
                  <Button 
                    variant="danger" 
                    onClick={() => handleDeleteServer(server.server_id)}
                    size="sm"
                  >
                    Delete Server
                  </Button>
                </div>

                {expandedServers[server.server_id] && (
                  <div className="expanded-content">
                    <div className="tools-list">
                      {Object.entries(server.tools || {}).map(([toolName, toolConfig]) => {
                        const enabledForActive = isToolEnabledForActive(toolName);
                        return (
                          <div key={toolName} className="tool-card">
                            <div className="tool-header">
                              <div className="tool-header-content">
                                <div className="tool-header-left">
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
                                    checked={enabledForActive}
                                    onChange={() => mode === 'mcp' ? toggleServerTool(toolName, enabledForActive) : togglePresetTool(toolName, enabledForActive)}
                                    disabled={mode === 'mcp' ? !activeServer : !activePreset}
                                  />
                                  <span>Enabled</span>
                                </label>
                              </div>
                            </div>
                            {toolConfig.input_schema && (
                              <details className="schema-details">
                                <summary className="schema-summary">View Schema</summary>
                                <pre className="schema-pre">
                                  {JSON.stringify(toolConfig.input_schema, null, 2)}
                                </pre>
                              </details>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* All Available Tools (local + remote) with per-server selection */}
      <div className="mcp-section">
        <div className="section-header">
          <div>
            <h2 className="section-title">
              Local Extension Tools ({extensions.length})
              {(mode === 'mcp' ? activeServer : activePreset) && extensions.length > 0 && (
                <span className="section-tool-count">
                  {' • '}
                  <span className="stat-active">{getExtensionTotalCounts().active}</span>
                  <span className="stat-separator"> / </span>
                  <span className="stat-total">{getExtensionTotalCounts().total}</span>
                  {' tools active'}
                </span>
              )}
            </h2>
            <span className="section-subtitle">
              {mode === 'mcp' 
                ? (activeServer ? `Active MCP: ${activeServer}` : 'Select an MCP server above')
                : (activePreset ? `Active Preset: ${activePreset}` : 'Select a preset above')
              }
            </span>
          </div>
          {extensions.length > 0 && (mode === 'mcp' ? activeServer : activePreset) && (
            <div className="bulk-actions-buttons">
              <Button 
                variant="secondary" 
                size="sm"
                onClick={() => toggleAllExtensionTools(true)}
              >
                Enable All
              </Button>
              <Button 
                variant="secondary" 
                size="sm"
                onClick={() => toggleAllExtensionTools(false)}
              >
                Disable All
              </Button>
            </div>
          )}
        </div>
        {extensions.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon">🔧</div>
            <h3>No extensions with tools found</h3>
            <p>Install extensions from the Extension Manager to see their tools here</p>
          </div>
        ) : (
          <div className="cards-list">
            {extensions.map(ext => (
              <div key={ext.name} className="extension-card">
                <div className="extension-card-header">
                  <div className="extension-card-title-with-toggle">
                    <button
                      onClick={() => toggleExtension(ext.name)}
                      className="expand-toggle-btn"
                    >
                      {expandedExtensions[ext.name] ? '▼' : '▶'}
                    </button>
                    <div>
                      <h3>{ext.name}</h3>
                      <div className="extension-stats">
                        <div className="stat">
                          <span className="stat-icon">🛠️</span>
                          <span>
                            {(mode === 'mcp' ? activeServer : activePreset) ? (
                              <>
                                <span className="stat-active">{getExtensionActiveCount(ext)}</span>
                                <span className="stat-separator"> / </span>
                                <span className="stat-total">{ext.tool_count}</span>
                                <span> tools active</span>
                              </>
                            ) : (
                              <>{ext.tool_count} tools</>
                            )}
                          </span>
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

                <div className="extension-card-actions">
                  {(mode === 'mcp' ? activeServer : activePreset) && (
                    <>
                      <Button 
                        variant="secondary" 
                        onClick={() => toggleAllToolsInExtension(ext.name, true)}
                        size="sm"
                      >
                        Enable All Tools
                      </Button>
                      <Button 
                        variant="secondary" 
                        onClick={() => toggleAllToolsInExtension(ext.name, false)}
                        size="sm"
                      >
                        Disable All Tools
                      </Button>
                    </>
                  )}
                </div>

                {expandedExtensions[ext.name] && (
                  <div className="expanded-content">
                    <div className="tools-list">
                      {ext.tools.map(tool => {
                        const enabled = isToolEnabledForActive(tool.name);
                        return (
                          <div key={tool.name} className="tool-card">
                            <div className="tool-header">
                              <div className="tool-header-content">
                                <div className="tool-header-left">
                                  <div className="tool-name-row">
                                    <h3>{tool.name}</h3>
                                    {tool.passthrough && (
                                      <span className="version-tag passthrough-tag">
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
                                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                                  <span style={{ fontSize: '0.9rem', color: '#a0a0a0' }}>Enabled</span>
                                  <label className="toggle-switch">
                                    <input
                                      type="checkbox"
                                      checked={enabled}
                                      onChange={() => mode === 'mcp' ? toggleServerTool(tool.name, enabled) : togglePresetTool(tool.name, enabled)}
                                      disabled={mode === 'mcp' ? !activeServer : !activePreset}
                                    />
                                    <span className="toggle-slider"></span>
                                  </label>
                                </div>
                              </div>
                            </div>
                          </div>
                        );
                      })}
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
