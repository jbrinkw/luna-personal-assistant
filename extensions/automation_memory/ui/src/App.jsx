import React, { useState, useEffect } from 'react';

// Determine API base URL dynamically
const getApiBase = async () => {
  try {
    // Get the current hostname (handles both localhost and network access)
    const hostname = window.location.hostname;
    
    // Fetch port mapping from supervisor via Caddy proxy
    const supervisorUrl = `/api/supervisor/ports`;
    console.log('[Init] Fetching port assignments from:', supervisorUrl);
    
    const response = await fetch(supervisorUrl);
    const ports = await response.json();
    console.log('[Init] Port assignments:', ports);
    
    // Get the automation_memory backend port
    const backendPort = ports.services?.['automation_memory.backend'];
    
    if (!backendPort) {
      console.error('[Init] ❌ automation_memory.backend port not found in assignments');
      console.error('[Init] Available services:', Object.keys(ports.services || {}));
      // Fallback to Caddy proxy path
      return `/api/automation_memory`;
    }
    
    // Use Caddy proxy path for backend
    const apiBase = `/api/automation_memory`;
    console.log('[Init] ✅ Resolved backend API:', apiBase);
    return apiBase;
  } catch (e) {
    console.error('[Init] Failed to resolve backend port from supervisor:', e);
    console.error('[Init] Falling back to Caddy proxy path');
    return '/api/automation_memory';
  }
};

export default function App() {
  const [tab, setTab] = useState('memories');
  const [memories, setMemories] = useState([]);
  const [flows, setFlows] = useState([]);
  const [schedules, setSchedules] = useState([]);
  const [agents, setAgents] = useState(['simple_agent', 'passthrough_agent']);
  const [health, setHealth] = useState(null);
  const [apiBase, setApiBase] = useState(null);

  // Initialize API base URL
  useEffect(() => {
    getApiBase()
      .then(url => {
        setApiBase(url);
      })
      .catch(err => {
        console.error('[App] Failed to initialize API base:', err);
        // Fallback to default API path
        setApiBase('/api/automation_memory');
      });
  }, []);

  // Load data on mount and when API base is ready
  useEffect(() => {
    if (!apiBase) return;
    loadAgents();
    loadData();
    checkHealth();
  }, [apiBase]);

  useEffect(() => {
    if (!apiBase) return;
    loadData();
  }, [tab, apiBase]);

  const checkHealth = async () => {
    if (!apiBase) return;
    try {
      console.log(`[Health Check] Attempting to connect to ${apiBase}/healthz`);
      const res = await fetch(`${apiBase}/healthz`);
      console.log(`[Health Check] Response status: ${res.status}`);
      const data = await res.json();
      console.log(`[Health Check] Response data:`, data);
      
      if (data.status === 'ok') {
        console.log('[Health Check] ✅ Backend is healthy - Status: Connected');
        setHealth('Connected');
      } else {
        console.error('[Health Check] ⚠️ Backend returned non-ok status:', data);
        setHealth('Error');
      }
    } catch (e) {
      console.error(`[Health Check] ❌ Failed to connect to backend at ${apiBase}`);
      console.error(`[Health Check] Error type: ${e.name}`);
      console.error(`[Health Check] Error message: ${e.message}`);
      console.error(`[Health Check] Full error:`, e);
      console.error('[Health Check] Possible causes:');
      console.error('  1. Backend not running on assigned port');
      console.error('  2. CORS issue (check backend allows origin)');
      console.error('  3. Network connectivity issue');
      console.error('  4. Backend crashed or unresponsive');
      setHealth('Disconnected');
    }
  };

  const loadAgents = async () => {
    if (!apiBase) return;
    try {
      const res = await fetch(`${apiBase}/api/agents`);
      const data = await res.json();
      if (data.agents && data.agents.length > 0) {
        setAgents(data.agents);
      }
    } catch (e) {
      console.error('Failed to load agents:', e);
    }
  };

  const loadData = async () => {
    if (!apiBase) return;
    try {
      if (tab === 'memories') {
        const res = await fetch(`${apiBase}/api/memories`);
        const data = await res.json();
        setMemories(data || []);
      } else if (tab === 'flows') {
        const res = await fetch(`${apiBase}/api/task_flows`);
        const data = await res.json();
        setFlows(data || []);
      } else if (tab === 'schedules') {
        const res = await fetch(`${apiBase}/api/scheduled_prompts`);
        const data = await res.json();
        setSchedules(data || []);
      }
    } catch (e) {
      console.error('Failed to load data:', e);
    }
  };

  return (
    <div className="app">
      <div className="header">
        <h1>Automation Memory</h1>
        <div className={`healthz ${health !== 'Connected' ? 'error' : ''}`}>
          Status: {health || 'Checking...'}
        </div>
      </div>

      <div className="tabs">
        <button
          className={`tab-button ${tab === 'memories' ? 'active' : ''}`}
          onClick={() => setTab('memories')}
        >
          Memories
        </button>
        <button
          className={`tab-button ${tab === 'flows' ? 'active' : ''}`}
          onClick={() => setTab('flows')}
        >
          Task Flows
        </button>
        <button
          className={`tab-button ${tab === 'schedules' ? 'active' : ''}`}
          onClick={() => setTab('schedules')}
        >
          Scheduled Tasks
        </button>
      </div>

      <div className="tab-content">
        {!apiBase ? (
          <div>Loading...</div>
        ) : (
          <>
            {tab === 'memories' && <MemoriesTab memories={memories} onUpdate={loadData} apiBase={apiBase} />}
            {tab === 'flows' && <FlowsTab flows={flows} agents={agents} onUpdate={loadData} apiBase={apiBase} />}
            {tab === 'schedules' && <SchedulesTab schedules={schedules} agents={agents} onUpdate={loadData} apiBase={apiBase} />}
          </>
        )}
      </div>
    </div>
  );
}

function MemoriesTab({ memories, onUpdate, apiBase }) {
  const [newContent, setNewContent] = useState('');

  const handleAdd = async () => {
    if (!newContent.trim()) return;
    try {
      await fetch(`${apiBase}/api/memories`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: newContent }),
      });
      setNewContent('');
      onUpdate();
    } catch (e) {
      alert('Failed to add memory');
    }
  };

  const handleDelete = async (id) => {
    if (!confirm('Delete this memory?')) return;
    try {
      await fetch(`${apiBase}/api/memories/${id}`, { method: 'DELETE' });
      onUpdate();
    } catch (e) {
      alert('Failed to delete memory');
    }
  };

  return (
    <div>
      <div className="form-group">
        <label className="form-label">Add New Memory</label>
        <textarea
          className="form-textarea"
          value={newContent}
          onChange={(e) => setNewContent(e.target.value)}
          placeholder="Enter memory content..."
        />
      </div>
      <button className="btn btn-primary add-button" onClick={handleAdd}>
        Add Memory
      </button>

      <div className="item-list">
        {memories.map((mem) => (
          <div key={mem.id} className="item">
            <div className="item-header">
              <span className="item-title">Memory #{mem.id}</span>
              <button className="btn btn-danger" onClick={() => handleDelete(mem.id)}>
                Delete
              </button>
            </div>
            <div>{mem.content}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

function FlowsTab({ flows, agents, onUpdate, apiBase }) {
  const [showAdd, setShowAdd] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [activeExecutions, setActiveExecutions] = useState([]);
  const [recentExecutions, setRecentExecutions] = useState([]);
  const [showHistory, setShowHistory] = useState(false);
  const [newFlow, setNewFlow] = useState({
    call_name: '',
    prompts: [''],
    agent: 'simple_agent',
  });
  const [editFlow, setEditFlow] = useState({
    call_name: '',
    prompts: [''],
    agent: 'simple_agent',
  });

  // Poll for execution updates
  useEffect(() => {
    loadExecutions();
    const interval = setInterval(loadExecutions, 2000); // Poll every 2 seconds
    return () => clearInterval(interval);
  }, []);

  const loadExecutions = async () => {
    try {
      // Use refresh endpoint to get both active and recent from cache
      const res = await fetch(`${apiBase}/api/executions/refresh`);
      const data = await res.json();
      setActiveExecutions(data.active || []);
      setRecentExecutions(data.recent || []);
    } catch (e) {
      console.error('Failed to load executions:', e);
    }
  };

  const handleAdd = async () => {
    if (!newFlow.call_name.trim()) {
      alert('Call name is required');
      return;
    }
    try {
      await fetch(`${apiBase}/api/task_flows`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          call_name: newFlow.call_name,
          prompts: newFlow.prompts.filter(p => p.trim()),
          agent: newFlow.agent,
        }),
      });
      setNewFlow({ call_name: '', prompts: [''], agent: 'simple_agent' });
      setShowAdd(false);
      onUpdate();
    } catch (e) {
      alert('Failed to add flow');
    }
  };

  const handleEdit = (flow) => {
    setEditingId(flow.id);
    setEditFlow({
      call_name: flow.call_name,
      prompts: flow.prompts || [''],
      agent: flow.agent || 'simple_agent',
    });
    setShowAdd(false);
  };

  const handleUpdate = async () => {
    if (!editFlow.call_name.trim()) {
      alert('Call name is required');
      return;
    }
    try {
      await fetch(`${apiBase}/api/task_flows/${editingId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          call_name: editFlow.call_name,
          prompts: editFlow.prompts.filter(p => p.trim()),
          agent: editFlow.agent,
        }),
      });
      setEditingId(null);
      setEditFlow({ call_name: '', prompts: [''], agent: 'simple_agent' });
      onUpdate();
    } catch (e) {
      alert('Failed to update flow');
    }
  };

  const handleCancelEdit = () => {
    setEditingId(null);
    setEditFlow({ call_name: '', prompts: [''], agent: 'simple_agent' });
  };

  const handleRun = async (id) => {
    try {
      const res = await fetch(`${apiBase}/api/task_flows/${id}/run`, { method: 'POST' });
      const data = await res.json();
      if (data.ok) {
        loadExecutions(); // Refresh executions immediately
        alert('Flow execution started');
      } else {
        alert('Failed to start flow');
      }
    } catch (e) {
      alert('Failed to run flow');
    }
  };

  const handleDelete = async (id) => {
    if (!confirm('Delete this flow?')) return;
    try {
      await fetch(`${apiBase}/api/task_flows/${id}`, { method: 'DELETE' });
      onUpdate();
    } catch (e) {
      alert('Failed to delete flow');
    }
  };

  return (
    <div>
      {/* Recent & Active Executions Section - Always Visible */}
      <div style={{ marginBottom: 20 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
          <h3 style={{ fontSize: 16, margin: 0, color: activeExecutions.length > 0 ? '#4CAF50' : '#666' }}>
            {activeExecutions.length > 0 ? `⚡ Running Flows (${activeExecutions.length})` : '📊 Recent Flow Executions'}
          </h3>
          <button 
            className="btn btn-secondary" 
            style={{ fontSize: 12, padding: '4px 12px' }}
            onClick={() => setShowHistory(!showHistory)}
          >
            {showHistory ? 'Hide All' : `Show All (${recentExecutions.length})`}
          </button>
        </div>
        
        {/* Active/Running Flows */}
        {activeExecutions.length > 0 && activeExecutions.map((exec) => {
            const prompts = Array.isArray(exec.prompts) ? exec.prompts : JSON.parse(exec.prompts || '[]');
            const currentPrompt = prompts[exec.current_prompt_index] || '';
            const promptResults = Array.isArray(exec.prompt_results) ? exec.prompt_results : JSON.parse(exec.prompt_results || '[]');
            const progress = exec.total_prompts > 0 ? (exec.current_prompt_index / exec.total_prompts) * 100 : 0;
            
            return (
              <div key={exec.id} className="item" style={{ borderLeft: '4px solid #4CAF50' }}>
                <div className="item-header">
                  <div>
                    <span className="item-title">{exec.call_name}</span>
                    <span className="agent-badge" style={{ marginLeft: 10 }}>
                      {exec.agent}
                    </span>
                    <span style={{ marginLeft: 10, fontSize: 13, color: '#4CAF50' }}>
                      Prompt {exec.current_prompt_index}/{exec.total_prompts}
                    </span>
                  </div>
                </div>
                
                {/* Progress Bar */}
                <div style={{ margin: '10px 0', background: '#f0f0f0', borderRadius: 4, height: 8, overflow: 'hidden' }}>
                  <div style={{ 
                    width: `${progress}%`, 
                    background: '#4CAF50', 
                    height: '100%',
                    transition: 'width 0.3s ease'
                  }}></div>
                </div>
                
                {/* Current Prompt */}
                {currentPrompt && (
                  <div style={{ marginTop: 10 }}>
                    <strong>Current Prompt:</strong>
                    <div style={{ 
                      padding: 8, 
                      background: '#f9f9f9', 
                      borderRadius: 4, 
                      marginTop: 4,
                      fontSize: 13
                    }}>
                      {currentPrompt}
                    </div>
                  </div>
                )}
                
                {/* Latest Response */}
                {promptResults.length > 0 && promptResults[promptResults.length - 1].response && (
                  <div style={{ marginTop: 10 }}>
                    <strong>Latest Response:</strong>
                    <div style={{ 
                      padding: 8, 
                      background: '#f0f8ff', 
                      borderRadius: 4, 
                      marginTop: 4,
                      fontSize: 13,
                      maxHeight: 100,
                      overflow: 'auto'
                    }}>
                      {promptResults[promptResults.length - 1].response}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        
        {/* Show most recent completed flows (top 3) when not running anything */}
        {activeExecutions.length === 0 && recentExecutions.length > 0 && !showHistory && 
          recentExecutions.slice(0, 3).map((exec) => {
            const promptResults = Array.isArray(exec.prompt_results) ? exec.prompt_results : JSON.parse(exec.prompt_results || '[]');
            const statusColor = exec.status === 'completed' ? '#4CAF50' : exec.status === 'failed' ? '#f44336' : '#2196F3';
            const statusIcon = exec.status === 'completed' ? '✓' : exec.status === 'failed' ? '✗' : '⟳';
            
            return (
              <div key={exec.id} className="item" style={{ borderLeft: `4px solid ${statusColor}` }}>
                <div className="item-header">
                  <div>
                    <span className="item-title">{exec.call_name}</span>
                    <span className="agent-badge" style={{ marginLeft: 10 }}>
                      {exec.agent}
                    </span>
                    <span style={{ marginLeft: 10, fontSize: 13, color: statusColor }}>
                      {statusIcon} {exec.status}
                    </span>
                    <span style={{ marginLeft: 10, fontSize: 12, color: '#666' }}>
                      {exec.current_prompt_index}/{exec.total_prompts} prompts
                    </span>
                  </div>
                </div>
                
                {exec.error && (
                  <div style={{ marginTop: 10, padding: 8, background: '#ffebee', borderRadius: 4, fontSize: 13 }}>
                    <strong style={{ color: '#f44336' }}>Error:</strong> {exec.error}
                  </div>
                )}
              </div>
            );
          })
        }
      </div>

      {/* Full Execution History */}
      {showHistory && recentExecutions.length > 0 && (
        <div style={{ marginBottom: 20 }}>
          <h3 style={{ fontSize: 16, marginBottom: 10 }}>All Recent Executions</h3>
          {recentExecutions.map((exec) => {
            const promptResults = Array.isArray(exec.prompt_results) ? exec.prompt_results : JSON.parse(exec.prompt_results || '[]');
            const statusColor = exec.status === 'completed' ? '#4CAF50' : exec.status === 'failed' ? '#f44336' : '#2196F3';
            const statusIcon = exec.status === 'completed' ? '✓' : exec.status === 'failed' ? '✗' : '⟳';
            
            return (
              <div key={exec.id} className="item" style={{ borderLeft: `4px solid ${statusColor}` }}>
                <div className="item-header">
                  <div>
                    <span className="item-title">{exec.call_name}</span>
                    <span className="agent-badge" style={{ marginLeft: 10 }}>
                      {exec.agent}
                    </span>
                    <span style={{ marginLeft: 10, fontSize: 13, color: statusColor }}>
                      {statusIcon} {exec.status}
                    </span>
                    <span style={{ marginLeft: 10, fontSize: 12, color: '#666' }}>
                      {exec.current_prompt_index}/{exec.total_prompts} prompts
                    </span>
                  </div>
                </div>
                
                {exec.error && (
                  <div style={{ marginTop: 10, padding: 8, background: '#ffebee', borderRadius: 4 }}>
                    <strong style={{ color: '#f44336' }}>Error:</strong> {exec.error}
                  </div>
                )}
                
                {promptResults.length > 0 && (
                  <details style={{ marginTop: 10 }}>
                    <summary style={{ cursor: 'pointer', fontSize: 14, fontWeight: 500 }}>
                      View Results ({promptResults.length})
                    </summary>
                    <div style={{ marginTop: 8 }}>
                      {promptResults.map((result, idx) => (
                        <div key={idx} style={{ 
                          padding: 8, 
                          background: result.success ? '#f0f8ff' : '#ffebee', 
                          borderRadius: 4,
                          marginBottom: 8
                        }}>
                          <div style={{ fontSize: 12, fontWeight: 500, marginBottom: 4 }}>
                            Prompt {idx + 1}: {result.prompt}
                          </div>
                          {result.success ? (
                            <div style={{ fontSize: 13 }}>{result.response}</div>
                          ) : (
                            <div style={{ fontSize: 13, color: '#f44336' }}>Error: {result.error}</div>
                          )}
                        </div>
                      ))}
                    </div>
                  </details>
                )}
              </div>
            );
          })}
        </div>
      )}

      <button className="btn btn-primary add-button" onClick={() => { setShowAdd(!showAdd); setEditingId(null); }}>
        {showAdd ? 'Cancel' : 'Add New Flow'}
      </button>

      {showAdd && (
        <div className="item" style={{ marginBottom: 15 }}>
          <div className="form-group">
            <label className="form-label">Call Name</label>
            <input
              className="form-input"
              value={newFlow.call_name}
              onChange={(e) => setNewFlow({ ...newFlow, call_name: e.target.value })}
              placeholder="e.g., morning_routine"
            />
          </div>
          <div className="form-group">
            <label className="form-label">Agent</label>
            <select
              className="form-select"
              value={newFlow.agent}
              onChange={(e) => setNewFlow({ ...newFlow, agent: e.target.value })}
            >
              {agents.map(agent => (
                <option key={agent} value={agent}>{agent}</option>
              ))}
            </select>
          </div>
          <div className="form-group">
            <label className="form-label">Prompts</label>
            {newFlow.prompts.map((prompt, idx) => (
              <input
                key={idx}
                className="form-input"
                style={{ marginBottom: 8 }}
                value={prompt}
                onChange={(e) => {
                  const updated = [...newFlow.prompts];
                  updated[idx] = e.target.value;
                  setNewFlow({ ...newFlow, prompts: updated });
                }}
                placeholder={`Prompt ${idx + 1}`}
              />
            ))}
            <button
              className="btn btn-secondary"
              onClick={() => setNewFlow({ ...newFlow, prompts: [...newFlow.prompts, ''] })}
            >
              Add Prompt
            </button>
          </div>
          <button className="btn btn-primary" onClick={handleAdd}>
            Save Flow
          </button>
        </div>
      )}

      <div className="item-list">
        {flows.map((flow) => (
          <div key={flow.id} className="item">
            {editingId === flow.id ? (
              <div>
                <div className="form-group">
                  <label className="form-label">Call Name</label>
                  <input
                    className="form-input"
                    value={editFlow.call_name}
                    onChange={(e) => setEditFlow({ ...editFlow, call_name: e.target.value })}
                    placeholder="e.g., morning_routine"
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Agent</label>
                  <select
                    className="form-select"
                    value={editFlow.agent}
                    onChange={(e) => setEditFlow({ ...editFlow, agent: e.target.value })}
                  >
                    {agents.map(agent => (
                      <option key={agent} value={agent}>{agent}</option>
                    ))}
                  </select>
                </div>
                <div className="form-group">
                  <label className="form-label">Prompts</label>
                  {editFlow.prompts.map((prompt, idx) => (
                    <input
                      key={idx}
                      className="form-input"
                      style={{ marginBottom: 8 }}
                      value={prompt}
                      onChange={(e) => {
                        const updated = [...editFlow.prompts];
                        updated[idx] = e.target.value;
                        setEditFlow({ ...editFlow, prompts: updated });
                      }}
                      placeholder={`Prompt ${idx + 1}`}
                    />
                  ))}
                  <button
                    className="btn btn-secondary"
                    onClick={() => setEditFlow({ ...editFlow, prompts: [...editFlow.prompts, ''] })}
                  >
                    Add Prompt
                  </button>
                </div>
                <div style={{ display: 'flex', gap: 8 }}>
                  <button className="btn btn-primary" onClick={handleUpdate}>
                    Save Changes
                  </button>
                  <button className="btn btn-secondary" onClick={handleCancelEdit}>
                    Cancel
                  </button>
                </div>
              </div>
            ) : (
              <div>
                <div className="item-header">
                  <div>
                    <span className="item-title">{flow.call_name}</span>
                    <span className="agent-badge" style={{ marginLeft: 10 }}>
                      {flow.agent}
                    </span>
                  </div>
                  <div className="item-actions">
                    <button className="btn btn-primary" onClick={() => handleRun(flow.id)}>
                      Run
                    </button>
                    <button className="btn btn-secondary" onClick={() => handleEdit(flow)}>
                      Edit
                    </button>
                    <button className="btn btn-danger" onClick={() => handleDelete(flow.id)}>
                      Delete
                    </button>
                  </div>
                </div>
                <ul className="prompts-list">
                  {(flow.prompts || []).map((prompt, idx) => (
                    <li key={idx}>{idx + 1}. {prompt}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function SchedulesTab({ schedules, agents, onUpdate, apiBase }) {
  const [showAdd, setShowAdd] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [newSchedule, setNewSchedule] = useState({
    time_of_day: '09:00',
    days_of_week: [false, false, false, false, false, false, false],
    prompt: '',
    agent: 'simple_agent',
    enabled: true,
  });
  const [editSchedule, setEditSchedule] = useState({
    time_of_day: '09:00',
    days_of_week: [false, false, false, false, false, false, false],
    prompt: '',
    agent: 'simple_agent',
    enabled: true,
  });

  const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

  const handleAdd = async () => {
    if (!newSchedule.prompt.trim()) {
      alert('Prompt is required');
      return;
    }
    try {
      await fetch(`${apiBase}/api/scheduled_prompts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newSchedule),
      });
      setNewSchedule({
        time_of_day: '09:00',
        days_of_week: [false, false, false, false, false, false, false],
        prompt: '',
        agent: 'simple_agent',
        enabled: true,
      });
      setShowAdd(false);
      onUpdate();
    } catch (e) {
      alert('Failed to add schedule');
    }
  };

  const handleEdit = (schedule) => {
    setEditingId(schedule.id);
    setEditSchedule({
      time_of_day: schedule.time_of_day,
      days_of_week: schedule.days_of_week || [false, false, false, false, false, false, false],
      prompt: schedule.prompt,
      agent: schedule.agent || 'simple_agent',
      enabled: schedule.enabled !== undefined ? schedule.enabled : true,
    });
    setShowAdd(false);
  };

  const handleUpdate = async () => {
    if (!editSchedule.prompt.trim()) {
      alert('Prompt is required');
      return;
    }
    try {
      await fetch(`${apiBase}/api/scheduled_prompts/${editingId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(editSchedule),
      });
      setEditingId(null);
      setEditSchedule({
        time_of_day: '09:00',
        days_of_week: [false, false, false, false, false, false, false],
        prompt: '',
        agent: 'simple_agent',
        enabled: true,
      });
      onUpdate();
    } catch (e) {
      alert('Failed to update schedule');
    }
  };

  const handleCancelEdit = () => {
    setEditingId(null);
    setEditSchedule({
      time_of_day: '09:00',
      days_of_week: [false, false, false, false, false, false, false],
      prompt: '',
      agent: 'simple_agent',
      enabled: true,
    });
  };

  const handleToggle = async (id, enabled) => {
    try {
      await fetch(`${apiBase}/api/scheduled_prompts/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled }),
      });
      onUpdate();
    } catch (e) {
      alert('Failed to toggle schedule');
    }
  };

  const handleDelete = async (id) => {
    if (!confirm('Delete this schedule?')) return;
    try {
      await fetch(`${apiBase}/api/scheduled_prompts/${id}`, { method: 'DELETE' });
      onUpdate();
    } catch (e) {
      alert('Failed to delete schedule');
    }
  };

  return (
    <div>
      <button className="btn btn-primary add-button" onClick={() => { setShowAdd(!showAdd); setEditingId(null); }}>
        {showAdd ? 'Cancel' : 'Add New Schedule'}
      </button>

      {showAdd && (
        <div className="item" style={{ marginBottom: 15 }}>
          <div className="form-group">
            <label className="form-label">Time (HH:MM)</label>
            <input
              className="form-input"
              type="time"
              value={newSchedule.time_of_day}
              onChange={(e) => setNewSchedule({ ...newSchedule, time_of_day: e.target.value })}
            />
          </div>
          <div className="form-group">
            <label className="form-label">Days of Week</label>
            <div style={{ display: 'flex', gap: 10 }}>
              {dayNames.map((day, idx) => (
                <label key={idx} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                  <input
                    type="checkbox"
                    checked={newSchedule.days_of_week[idx]}
                    onChange={(e) => {
                      const updated = [...newSchedule.days_of_week];
                      updated[idx] = e.target.checked;
                      setNewSchedule({ ...newSchedule, days_of_week: updated });
                    }}
                  />
                  {day}
                </label>
              ))}
            </div>
          </div>
          <div className="form-group">
            <label className="form-label">Agent</label>
            <select
              className="form-select"
              value={newSchedule.agent}
              onChange={(e) => setNewSchedule({ ...newSchedule, agent: e.target.value })}
            >
              {agents.map(agent => (
                <option key={agent} value={agent}>{agent}</option>
              ))}
            </select>
          </div>
          <div className="form-group">
            <label className="form-label">Prompt</label>
            <textarea
              className="form-textarea"
              value={newSchedule.prompt}
              onChange={(e) => setNewSchedule({ ...newSchedule, prompt: e.target.value })}
              placeholder="Enter prompt to execute..."
            />
          </div>
          <button className="btn btn-primary" onClick={handleAdd}>
            Save Schedule
          </button>
        </div>
      )}

      <div className="item-list">
        {schedules.map((sched) => {
          const activeDays = (sched.days_of_week || []).map((active, idx) => active ? dayNames[idx] : null).filter(Boolean);
          return (
            <div key={sched.id} className="item">
              {editingId === sched.id ? (
                <div>
                  <div className="form-group">
                    <label className="form-label">Time (HH:MM)</label>
                    <input
                      className="form-input"
                      type="time"
                      value={editSchedule.time_of_day}
                      onChange={(e) => setEditSchedule({ ...editSchedule, time_of_day: e.target.value })}
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Days of Week</label>
                    <div style={{ display: 'flex', gap: 10 }}>
                      {dayNames.map((day, idx) => (
                        <label key={idx} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                          <input
                            type="checkbox"
                            checked={editSchedule.days_of_week[idx]}
                            onChange={(e) => {
                              const updated = [...editSchedule.days_of_week];
                              updated[idx] = e.target.checked;
                              setEditSchedule({ ...editSchedule, days_of_week: updated });
                            }}
                          />
                          {day}
                        </label>
                      ))}
                    </div>
                  </div>
                  <div className="form-group">
                    <label className="form-label">Agent</label>
                    <select
                      className="form-select"
                      value={editSchedule.agent}
                      onChange={(e) => setEditSchedule({ ...editSchedule, agent: e.target.value })}
                    >
                      {agents.map(agent => (
                        <option key={agent} value={agent}>{agent}</option>
                      ))}
                    </select>
                  </div>
                  <div className="form-group">
                    <label className="form-label">Enabled</label>
                    <label style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <input
                        type="checkbox"
                        checked={editSchedule.enabled}
                        onChange={(e) => setEditSchedule({ ...editSchedule, enabled: e.target.checked })}
                      />
                      Schedule is enabled
                    </label>
                  </div>
                  <div className="form-group">
                    <label className="form-label">Prompt</label>
                    <textarea
                      className="form-textarea"
                      value={editSchedule.prompt}
                      onChange={(e) => setEditSchedule({ ...editSchedule, prompt: e.target.value })}
                      placeholder="Enter prompt to execute..."
                    />
                  </div>
                  <div style={{ display: 'flex', gap: 8 }}>
                    <button className="btn btn-primary" onClick={handleUpdate}>
                      Save Changes
                    </button>
                    <button className="btn btn-secondary" onClick={handleCancelEdit}>
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <div>
                  <div className="item-header">
                    <div>
                      <span className="item-title">{sched.time_of_day}</span>
                      <span className="agent-badge" style={{ marginLeft: 10 }}>
                        {sched.agent}
                      </span>
                      <span style={{ marginLeft: 10, fontSize: 13, color: '#666' }}>
                        {activeDays.join(', ')}
                      </span>
                      {!sched.enabled && (
                        <span style={{ marginLeft: 10, fontSize: 13, color: '#999', fontStyle: 'italic' }}>
                          (disabled)
                        </span>
                      )}
                    </div>
                    <div className="item-actions">
                      <button
                        className={`btn ${sched.enabled ? 'btn-secondary' : 'btn-primary'}`}
                        onClick={() => handleToggle(sched.id, !sched.enabled)}
                      >
                        {sched.enabled ? 'Disable' : 'Enable'}
                      </button>
                      <button className="btn btn-secondary" onClick={() => handleEdit(sched)}>
                        Edit
                      </button>
                      <button className="btn btn-danger" onClick={() => handleDelete(sched.id)}>
                        Delete
                      </button>
                    </div>
                  </div>
                  <div>{sched.prompt}</div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

