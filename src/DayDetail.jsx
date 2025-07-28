import React, { useEffect, useState } from 'react';

export default function DayDetail({ id, onBack }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [newPlan, setNewPlan] = useState({ exercise: '', reps: 0, load: 0, order_num: 1 });
  const [newComp, setNewComp] = useState({ exercise: '', reps_done: 0, load_done: 0 });

  const load = () => {
    setLoading(true);
    setError(null);
    fetch(`/api/days/${id}`)
      .then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then(data => {
        setData(data);
        setLoading(false);
      })
      .catch(err => {
        console.error('Error loading day data:', err);
        setError(err.message);
        setLoading(false);
      });
  };
  
  useEffect(load, [id]);

  if (loading) return <div><button onClick={onBack}>Back</button><p>Loading day details...</p></div>;
  if (error) return <div><button onClick={onBack}>Back</button><p>Error loading day: {error}</p></div>;
  if (!data) return <div><button onClick={onBack}>Back</button><p>No data found for this day.</p></div>;

  const addPlan = async () => {
    await fetch(`/api/days/${id}/plan`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(newPlan) });
    setNewPlan({ exercise: '', reps: 0, load: 0, order_num: 1 });
    load();
  };
  const addCompleted = async () => {
    await fetch(`/api/days/${id}/completed`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(newComp) });
    setNewComp({ exercise: '', reps_done: 0, load_done: 0 });
    load();
  };
  const updateSummary = async () => {
    await fetch(`/api/days/${id}/summary`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ summary: data.log.summary }) });
  };

  const updatePlan = async (p) => {
    await fetch(`/api/plan/${p.id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(p) });
  };
  const deletePlan = async (pid) => { await fetch(`/api/plan/${pid}`, { method: 'DELETE' }); load(); };
  const updateComp = async (c) => { await fetch(`/api/completed/${c.id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(c) }); };
  const deleteComp = async (cid) => { await fetch(`/api/completed/${cid}`, { method: 'DELETE' }); load(); };

  const handlePlanChange = (idx, field, value) => {
    const upd = { ...data.plan[idx], [field]: value };
    const copy = [...data.plan];
    copy[idx] = upd;
    setData({ ...data, plan: copy });
    updatePlan(upd);
  };
  const handleCompChange = (idx, field, value) => {
    const upd = { ...data.completed[idx], [field]: value };
    const copy = [...data.completed];
    copy[idx] = upd;
    setData({ ...data, completed: copy });
    updateComp(upd);
  };

  return (
    <div>
      <button onClick={onBack}>Back</button>
      <h3>{data.log.log_date}</h3>
      <div>
        <h4>Planned Sets</h4>
        <table border="1" cellPadding="4">
          <thead><tr><th>Exercise</th><th>Reps</th><th>Load</th><th>Order</th><th></th></tr></thead>
          <tbody>
            {data.plan.map((p, i) => (
              <tr key={p.id}>
                <td><input value={p.exercise} onChange={e => handlePlanChange(i,'exercise', e.target.value)} /></td>
                <td><input type="number" value={p.reps} onChange={e => handlePlanChange(i,'reps', e.target.value)} /></td>
                <td><input type="number" value={p.load} onChange={e => handlePlanChange(i,'load', e.target.value)} /></td>
                <td><input type="number" value={p.order_num} onChange={e => handlePlanChange(i,'order_num', e.target.value)} /></td>
                <td><button onClick={() => {deletePlan(p.id);}}>Delete</button></td>
              </tr>
            ))}
            <tr>
              <td><input value={newPlan.exercise} onChange={e => setNewPlan({...newPlan, exercise:e.target.value})} /></td>
              <td><input type="number" value={newPlan.reps} onChange={e => setNewPlan({...newPlan, reps:e.target.value})} /></td>
              <td><input type="number" value={newPlan.load} onChange={e => setNewPlan({...newPlan, load:e.target.value})} /></td>
              <td><input type="number" value={newPlan.order_num} onChange={e => setNewPlan({...newPlan, order_num:e.target.value})} /></td>
              <td><button onClick={addPlan}>Add</button></td>
            </tr>
          </tbody>
        </table>
      </div>
      <div>
        <h4>Completed Sets</h4>
        <table border="1" cellPadding="4">
          <thead><tr><th>Exercise</th><th>Reps</th><th>Load</th><th></th></tr></thead>
          <tbody>
            {data.completed.map((c,i) => (
              <tr key={c.id}>
                <td><input value={c.exercise} onChange={e => handleCompChange(i,'exercise', e.target.value)} /></td>
                <td><input type="number" value={c.reps_done} onChange={e => handleCompChange(i,'reps_done', e.target.value)} /></td>
                <td><input type="number" value={c.load_done} onChange={e => handleCompChange(i,'load_done', e.target.value)} /></td>
                <td><button onClick={() => {deleteComp(c.id);}}>Delete</button></td>
              </tr>
            ))}
            <tr>
              <td><input value={newComp.exercise} onChange={e => setNewComp({...newComp, exercise:e.target.value})} /></td>
              <td><input type="number" value={newComp.reps_done} onChange={e => setNewComp({...newComp, reps_done:e.target.value})} /></td>
              <td><input type="number" value={newComp.load_done} onChange={e => setNewComp({...newComp, load_done:e.target.value})} /></td>
              <td><button onClick={addCompleted}>Add</button></td>
            </tr>
          </tbody>
        </table>
      </div>
      <div>
        <h4>Summary</h4>
        <textarea 
          rows="3" 
          cols="50"
          placeholder="Add workout summary..."
          value={data.log.summary || ''} 
          onChange={e => setData({ ...data, log: { ...data.log, summary: e.target.value } })} 
          onBlur={updateSummary} 
        />
      </div>
    </div>
  );
}
