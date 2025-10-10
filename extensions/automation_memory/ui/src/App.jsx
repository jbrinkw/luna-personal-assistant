import React, { useState, useEffect } from 'react';

const API_BASE = 'http://127.0.0.1:3051';

export default function App() {
  const [tab, setTab] = useState('memories');
  const [memories, setMemories] = useState([]);
  const [flows, setFlows] = useState([]);
  const [schedules, setSchedules] = useState([]);
  const [agents, setAgents] = useState(['simple_agent', 'passthrough_agent']);
  const [health, setHealth] = useState(null);

  // Load data on mount and tab change
  useEffect(() => {
    loadAgents();
    loadData();
    checkHealth();
  }, []);

  useEffect(() => {
    loadData();
  }, [tab]);

  const checkHealth = async () => {
    try {
      const res = await fetch(`${API_BASE}/healthz`);
      const data = await res.json();
      setHealth(data.status === 'ok' ? 'Connected' : 'Error');
    } catch (e) {
      setHealth('Disconnected');
    }
  };

  const loadAgents = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/agents`);
      const data = await res.json();
      if (data.agents && data.agents.length > 0) {
        setAgents(data.agents);
      }
    } catch (e) {
      console.error('Failed to load agents:', e);
    }
  };

  const loadData = async () => {
    try {
      if (tab === 'memories') {
        const res = await fetch(`${API_BASE}/api/memories`);
        const data = await res.json();
        setMemories(data || []);
      } else if (tab === 'flows') {
        const res = await fetch(`${API_BASE}/api/task_flows`);
        const data = await res.json();
        setFlows(data || []);
      } else if (tab === 'schedules') {
        const res = await fetch(`${API_BASE}/api/scheduled_prompts`);
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
        {tab === 'memories' && <MemoriesTab memories={memories} onUpdate={loadData} />}
        {tab === 'flows' && <FlowsTab flows={flows} agents={agents} onUpdate={loadData} />}
        {tab === 'schedules' && <SchedulesTab schedules={schedules} agents={agents} onUpdate={loadData} />}
      </div>
    </div>
  );
}

function MemoriesTab({ memories, onUpdate }) {
  const [newContent, setNewContent] = useState('');

  const handleAdd = async () => {
    if (!newContent.trim()) return;
    try {
      await fetch(`${API_BASE}/api/memories`, {
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
      await fetch(`${API_BASE}/api/memories/${id}`, { method: 'DELETE' });
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

function FlowsTab({ flows, agents, onUpdate }) {
  const [showAdd, setShowAdd] = useState(false);
  const [newFlow, setNewFlow] = useState({
    call_name: '',
    prompts: [''],
    agent: 'simple_agent',
  });

  const handleAdd = async () => {
    if (!newFlow.call_name.trim()) {
      alert('Call name is required');
      return;
    }
    try {
      await fetch(`${API_BASE}/api/task_flows`, {
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

  const handleRun = async (id) => {
    try {
      await fetch(`${API_BASE}/api/task_flows/${id}/run`, { method: 'POST' });
      alert('Flow execution started');
    } catch (e) {
      alert('Failed to run flow');
    }
  };

  const handleDelete = async (id) => {
    if (!confirm('Delete this flow?')) return;
    try {
      await fetch(`${API_BASE}/api/task_flows/${id}`, { method: 'DELETE' });
      onUpdate();
    } catch (e) {
      alert('Failed to delete flow');
    }
  };

  return (
    <div>
      <button className="btn btn-primary add-button" onClick={() => setShowAdd(!showAdd)}>
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
        ))}
      </div>
    </div>
  );
}

function SchedulesTab({ schedules, agents, onUpdate }) {
  const [showAdd, setShowAdd] = useState(false);
  const [newSchedule, setNewSchedule] = useState({
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
      await fetch(`${API_BASE}/api/scheduled_prompts`, {
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

  const handleToggle = async (id, enabled) => {
    try {
      await fetch(`${API_BASE}/api/scheduled_prompts/${id}`, {
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
      await fetch(`${API_BASE}/api/scheduled_prompts/${id}`, { method: 'DELETE' });
      onUpdate();
    } catch (e) {
      alert('Failed to delete schedule');
    }
  };

  return (
    <div>
      <button className="btn btn-primary add-button" onClick={() => setShowAdd(!showAdd)}>
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
              <div className="item-header">
                <div>
                  <span className="item-title">{sched.time_of_day}</span>
                  <span className="agent-badge" style={{ marginLeft: 10 }}>
                    {sched.agent}
                  </span>
                  <span style={{ marginLeft: 10, fontSize: 13, color: '#666' }}>
                    {activeDays.join(', ')}
                  </span>
                </div>
                <div className="item-actions">
                  <button
                    className={`btn ${sched.enabled ? 'btn-secondary' : 'btn-primary'}`}
                    onClick={() => handleToggle(sched.id, !sched.enabled)}
                  >
                    {sched.enabled ? 'Disable' : 'Enable'}
                  </button>
                  <button className="btn btn-danger" onClick={() => handleDelete(sched.id)}>
                    Delete
                  </button>
                </div>
              </div>
              <div>{sched.prompt}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

