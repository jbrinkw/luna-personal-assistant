import React, { useEffect, useRef, useState } from 'react';

function SectionTab({ label, active, onClick }) {
  const base = {
    padding: '8px 12px',
    border: '1px solid #ddd',
    borderBottom: active ? '2px solid #007bff' : '1px solid #ddd',
    marginRight: '8px',
    cursor: 'pointer',
    background: active ? '#eef6ff' : '#fff',
    fontWeight: active ? 'bold' : 'normal'
  };
  return <button style={base} onClick={onClick}>{label}</button>;
}

function InlineInput({ value, onChange, placeholder }) {
  const [draft, setDraft] = useState(value ?? '');
  useEffect(() => { setDraft(value ?? ''); }, [value]);
  const commit = () => { if (draft !== value) onChange(draft); };
  const onKey = (e) => { if (e.key === 'Enter') { e.preventDefault(); commit(); } };
  return (
    <input
      style={{ width: '100%', padding: 8, border: '1px solid #ddd', borderRadius: 4 }}
      value={draft}
      onChange={e => setDraft(e.target.value)}
      onBlur={commit}
      onKeyDown={onKey}
      placeholder={placeholder}
    />
  );
}

function InlineTextarea({ value, onChange, placeholder, rows = 4 }) {
  const [draft, setDraft] = useState(value ?? '');
  useEffect(() => { setDraft(value ?? ''); }, [value]);
  const commit = () => { if (draft !== value) onChange(draft); };
  const onKey = (e) => { if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') { e.preventDefault(); commit(); } };
  return (
    <textarea
      style={{ width: '100%', padding: 8, border: '1px solid #ddd', borderRadius: 4 }}
      value={draft}
      onChange={e => setDraft(e.target.value)}
      onBlur={commit}
      onKeyDown={onKey}
      placeholder={placeholder}
      rows={rows}
    />
  );
}

function Block({ children }) {
  return (
    <div style={{ border: '1px solid #eee', borderRadius: 8, padding: 12, marginBottom: 12, background: '#fff' }}>
      {children}
    </div>
  );
}

export default function App() {
  const [tab, setTab] = useState('flows');
  const [flows, setFlows] = useState([]);
  const [schedules, setSchedules] = useState([]);
  const [memories, setMemories] = useState([]);
  const [queued, setQueued] = useState([]);
  const [loading, setLoading] = useState(true);
  const [notice, setNotice] = useState(null);
  const noticeTimer = useRef(null);

  const showNotice = (text, type = 'info') => {
    if (noticeTimer.current) {
      clearTimeout(noticeTimer.current);
    }
    setNotice({ text, type });
    noticeTimer.current = setTimeout(() => setNotice(null), 4000);
  };

  const readError = async (res) => {
    try {
      const text = await res.text();
      try {
        const j = JSON.parse(text);
        const msg = (j && (j.error || j.message || j.detail || j.status)) || '';
        return msg || text || (res.statusText || 'Unknown error');
      } catch (_) {
        return text || (res.statusText || 'Unknown error');
      }
    } catch (_) {
      try { return res.statusText || 'Unknown error'; } catch { return 'Unknown error'; }
    }
  };

  const loadAll = async () => {
    setLoading(true);
    try {
      const [f, s, m, q] = await Promise.all([
        fetch('/api/task_flows').then(async r => { try { const j = await r.json(); return Array.isArray(j) ? j : []; } catch { return []; } }),
        fetch('/api/scheduled_prompts').then(async r => { try { const j = await r.json(); return Array.isArray(j) ? j : []; } catch { return []; } }),
        fetch('/api/memories').then(async r => { try { const j = await r.json(); return Array.isArray(j) ? j : []; } catch { return []; } }),
        fetch('/api/queued_messages').then(async r => { try { const j = await r.json(); return Array.isArray(j) ? j : []; } catch { return []; } }),
      ]);
      setFlows(f);
      setSchedules(s);
      setMemories(m);
      setQueued(q);
    } catch (e) {
      console.error('load error', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadAll(); }, []);

  useEffect(() => {
    return () => {
      if (noticeTimer.current) {
        clearTimeout(noticeTimer.current);
      }
    };
  }, []);

  // CRUD helpers
  const createFlow = async () => {
    const temp = { id: Math.random(), call_name: 'new_flow', prompts: ['step 1'], _temp: true };
    setFlows(prev => [temp, ...prev]);
    try {
      const res = await fetch('/api/task_flows', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ call_name: temp.call_name, prompts: temp.prompts }) });
      if (res.ok) {
        const { id } = await res.json();
        setFlows(prev => prev.map(f => f === temp ? { ...temp, id, _temp: false } : f));
        showNotice(`Created "${temp.call_name}"`, 'success');
      } else {
        setFlows(prev => prev.filter(f => f !== temp));
        const err = await readError(res);
        showNotice(`Failed to create "${temp.call_name}": ${err}`,'error');
      }
    } catch (e) {
      setFlows(prev => prev.filter(f => f !== temp));
      showNotice(`Failed to create "${temp.call_name}": ` + (e && e.message ? e.message : String(e)), 'error');
    }
  };
  const updateFlow = async (id, payload) => {
    setFlows(prev => prev.map(f => f.id === id ? { ...f, ...payload } : f));
    try {
      const res = await fetch(`/api/task_flows/${id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
      if (res.ok) {
        const name = (payload && typeof payload.call_name === 'string')
          ? payload.call_name
          : (flows.find(f => f.id === id)?.call_name || 'flow');
        showNotice(`Updated "${name}"`, 'success');
      } else {
        const name = (payload && typeof payload.call_name === 'string')
          ? payload.call_name
          : (flows.find(f => f.id === id)?.call_name || 'flow');
        const err = await readError(res);
        showNotice(`Update failed for "${name}": ${err}`, 'error');
      }
    } catch (e) {
      const name = (payload && typeof payload.call_name === 'string')
        ? payload.call_name
        : (flows.find(f => f.id === id)?.call_name || 'flow');
      showNotice(`Update failed for "${name}": ` + (e && e.message ? e.message : String(e)), 'error');
    }
  };
  const deleteFlow = async (id) => {
    const prev = flows;
    const name = (prev.find(f => f.id === id)?.call_name) || 'flow';
    setFlows(flows.filter(f => f.id !== id));
    try {
      const res = await fetch(`/api/task_flows/${id}`, { method: 'DELETE' });
      if (!res.ok) {
        setFlows(prev);
        const err = await readError(res);
        showNotice(`Delete failed for "${name}": ${err}`, 'error');
      } else {
        showNotice(`Deleted "${name}"`, 'success');
      }
    } catch (e) {
      setFlows(prev);
      showNotice(`Delete failed for "${name}": ` + (e && e.message ? e.message : String(e)), 'error');
    }
  };
  const runFlow = async (id) => {
    const name = (flows.find(f => f.id === id)?.call_name) || 'flow';
    try {
      const res = await fetch(`/api/task_flows/${id}/run`, { method: 'POST' });
      if (res.ok) {
        showNotice(`Started "${name}"`, 'success');
      } else {
        const err = await readError(res);
        showNotice(`Run failed for "${name}": ${err}`, 'error');
      }
    } catch (e) {
      showNotice(`Run failed for "${name}": ` + (e && e.message ? e.message : String(e)), 'error');
    }
  };

  const createSchedule = async () => {
    const temp = { id: Math.random(), time_of_day: '09:00', days_of_week: [false,true,true,true,true,true,false], prompt: 'Good morning', enabled: true, _temp: true };
    setSchedules(prev => [temp, ...prev]);
    const res = await fetch('/api/scheduled_prompts', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(temp) });
    if (res.ok) {
      const { id } = await res.json();
      setSchedules(prev => prev.map(s => s === temp ? { ...temp, id, _temp: false } : s));
    } else {
      setSchedules(prev => prev.filter(s => s !== temp));
    }
  };
  const updateSchedule = async (id, payload) => {
    setSchedules(prev => prev.map(s => s.id === id ? { ...s, ...payload } : s));
    await fetch(`/api/scheduled_prompts/${id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
  };
  const deleteSchedule = async (id) => {
    const prev = schedules;
    setSchedules(schedules.filter(s => s.id !== id));
    const res = await fetch(`/api/scheduled_prompts/${id}`, { method: 'DELETE' });
    if (!res.ok) setSchedules(prev);
  };

  const createMemory = async () => {
    const temp = { id: Math.random(), content: '', _temp: true };
    setMemories(prev => [temp, ...prev]);
    const res = await fetch('/api/memories', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ content: '' }) });
    if (res.ok) {
      const { id } = await res.json();
      setMemories(prev => prev.map(m => m === temp ? { ...temp, id, _temp: false } : m));
    } else {
      setMemories(prev => prev.filter(m => m !== temp));
    }
  };
  const updateMemory = async (id, payload) => {
    setMemories(prev => prev.map(m => m.id === id ? { ...m, ...payload } : m));
    await fetch(`/api/memories/${id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
  };
  const deleteMemory = async (id) => {
    const prev = memories;
    setMemories(memories.filter(m => m.id !== id));
    const res = await fetch(`/api/memories/${id}`, { method: 'DELETE' });
    if (!res.ok) setMemories(prev);
  };

  const createQueuedMsg = async () => {
    const temp = { id: Math.random(), content: '', created_at: new Date().toISOString(), _temp: true };
    setQueued(prev => [temp, ...prev]);
    const res = await fetch('/api/queued_messages', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ content: '' }) });
    if (res.ok) {
      const { id } = await res.json();
      setQueued(prev => prev.map(q => q === temp ? { ...temp, id, _temp: false } : q));
    } else {
      setQueued(prev => prev.filter(q => q !== temp));
    }
  };
  const updateQueuedMsg = async (id, payload) => {
    setQueued(prev => prev.map(q => q.id === id ? { ...q, ...payload } : q));
    await fetch(`/api/queued_messages/${id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
  };
  const deleteQueuedMsg = async (id) => {
    const prev = queued;
    setQueued(queued.filter(q => q.id !== id));
    const res = await fetch(`/api/queued_messages/${id}`, { method: 'DELETE' });
    if (!res.ok) setQueued(prev);
  };

  if (loading) {
    return <div style={{ padding: 20 }}>Loading…</div>;
  }

  return (
    <div style={{ padding: 20, fontFamily: 'Arial, sans-serif' }}>
      <div style={{ marginBottom: 12 }}>
        <SectionTab label="Task Flows" active={tab==='flows'} onClick={()=>setTab('flows')} />
        <SectionTab label="Scheduled Prompts" active={tab==='scheduled'} onClick={()=>setTab('scheduled')} />
        <SectionTab label="Memories" active={tab==='memories'} onClick={()=>setTab('memories')} />
        <SectionTab label="Queued Messages" active={tab==='queued'} onClick={()=>setTab('queued')} />
      </div>

      {tab === 'flows' && (
        <div>
          {notice && (
            <div style={{
              padding: '8px 12px',
              border: '1px solid',
              borderColor: notice.type === 'error' ? '#f5c2c7' : (notice.type === 'success' ? '#a3d9a5' : '#b6d4fe'),
              background: notice.type === 'error' ? '#f8d7da' : (notice.type === 'success' ? '#d1e7dd' : '#e7f1ff'),
              color: notice.type === 'error' ? '#842029' : (notice.type === 'success' ? '#0f5132' : '#084298'),
              borderRadius: 6,
              marginBottom: 8,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between'
            }}>
              <span>{notice.text}</span>
              <button onClick={() => setNotice(null)} style={{ background: 'transparent', border: 'none', color: 'inherit', cursor: 'pointer', fontSize: 16, lineHeight: 1 }}>×</button>
            </div>
          )}
          <div style={{ marginBottom: 8 }}>
            <button onClick={createFlow}>New Task Flow</button>
          </div>
          {flows.map(f => (
            <Block key={f.id}>
              <div style={{ display: 'flex', gap: 8 }}>
                <InlineInput value={f.call_name} onChange={v => updateFlow(f.id, { call_name: v })} placeholder="call name" />
                <button onClick={()=>runFlow(f.id)}>Run now</button>
                <button onClick={()=>deleteFlow(f.id)} style={{ color: '#b00' }}>Delete</button>
              </div>
              <div style={{ marginTop: 8 }}>
                <InlineTextarea
                  value={(f.prompts || []).join('\n')}
                  onChange={v => updateFlow(f.id, { prompts: v.split('\n').map(s => s.trim()).filter(Boolean) })}
                  placeholder="One prompt per line"
                  rows={Math.max(3, (f.prompts||[]).length)}
                />
              </div>
            </Block>
          ))}
          {flows.length === 0 && <div>No task flows yet.</div>}
        </div>
      )}

      {tab === 'scheduled' && (
        <div>
          <div style={{ marginBottom: 8 }}>
            <button onClick={createSchedule}>New Scheduled Prompt</button>
          </div>
          {schedules.map(s => (
            <Block key={s.id}>
              <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                <InlineInput value={s.time_of_day} onChange={v => updateSchedule(s.id, { time_of_day: v })} placeholder="HH:MM" />
                <label style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
                  <input type="checkbox" checked={!!s.enabled} onChange={e => updateSchedule(s.id, { enabled: e.target.checked })} /> Enabled
                </label>
                <button onClick={()=>deleteSchedule(s.id)} style={{ color: '#b00' }}>Delete</button>
              </div>
              <div style={{ marginTop: 8 }}>
                <InlineTextarea value={s.prompt || ''} onChange={v => updateSchedule(s.id, { prompt: v })} placeholder="Prompt to send" rows={3} />
              </div>
              <div style={{ marginTop: 8, display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                {['Sun','Mon','Tue','Wed','Thu','Fri','Sat'].map((d, idx) => (
                  <label key={idx} style={{ border: '1px solid #ddd', padding: '4px 8px', borderRadius: 4 }}>
                    <input
                      type="checkbox"
                      checked={Array.isArray(s.days_of_week) ? !!s.days_of_week[idx] : false}
                      onChange={e => {
                        const next = Array.isArray(s.days_of_week) && s.days_of_week.length === 7 ? [...s.days_of_week] : [false,false,false,false,false,false,false];
                        next[idx] = e.target.checked;
                        updateSchedule(s.id, { days_of_week: next });
                      }}
                    /> {d}
                  </label>
                ))}
              </div>
            </Block>
          ))}
          {schedules.length === 0 && <div>No scheduled prompts yet.</div>}
        </div>
      )}

      {tab === 'memories' && (
        <div>
          <div style={{ marginBottom: 8 }}>
            <button onClick={createMemory}>New Memory</button>
          </div>
          {memories.map(m => (
            <Block key={m.id}>
              <div style={{ display: 'flex', gap: 8 }}>
                <InlineInput value={m.content || ''} onChange={v => updateMemory(m.id, { content: v })} placeholder="Memory text" />
                <button onClick={()=>deleteMemory(m.id)} style={{ color: '#b00' }}>Delete</button>
              </div>
            </Block>
          ))}
          {memories.length === 0 && <div>No memories yet.</div>}
        </div>
      )}

      {tab === 'queued' && (
        <div>
          <div style={{ marginBottom: 8 }}>
            <button onClick={createQueuedMsg}>New Queued Message</button>
          </div>
          {queued.map(qm => (
            <Block key={qm.id}>
              <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                <span style={{ fontSize: 12, color: '#666', minWidth: 180 }}>Created: {qm.created_at}</span>
                <InlineInput value={qm.content || ''} onChange={v => updateQueuedMsg(qm.id, { content: v })} placeholder="Message text" />
                <button onClick={()=>deleteQueuedMsg(qm.id)} style={{ color: '#b00' }}>Delete</button>
              </div>
            </Block>
          ))}
          {queued.length === 0 && <div>No queued messages yet.</div>}
        </div>
      )}
    </div>
  );
}
