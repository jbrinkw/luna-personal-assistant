import React, { useEffect, useState, useRef } from 'react';
import { calculatePlates, formatWeightAndPlates } from './utils/weightCalc';

export default function DayDetail({ id, onBack, onDelete }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [newPlan, setNewPlan] = useState({ exercise: '', reps: 0, load: 0, rest: 60, order_num: 1 });
  const [completionForm, setCompletionForm] = useState({ exercise: '', reps_done: 0, load_done: 0 });
  const [isCompleting, setIsCompleting] = useState(false);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [timerStatus, setTimerStatus] = useState(null);
  const [deleteConfirm, setDeleteConfirm] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const isEditingRef = useRef(false);
  const [summaryDraft, setSummaryDraft] = useState('');

  useEffect(() => {
    isEditingRef.current = isEditing;
  }, [isEditing]);

  const loadTimer = async () => {
    try {
      const response = await fetch('/api/timer');
      if (response.ok) {
        const timer = await response.json();
        setTimerStatus(timer);
      }
    } catch (err) {
      console.error('Error loading timer:', err);
    }
  };

  const load = async (showLoading = true) => {
    if (showLoading) {
      setLoading(true);
      setError(null);
    }
    
    try {
      const response = await fetch(`/api/days/${id}`);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const newData = await response.json();
      
      // Only update if data has actually changed
      setData(prevData => {
        // Avoid overwriting user input while editing
        if (isEditingRef.current) {
          return prevData;
        }
        const newDataString = JSON.stringify(newData);
        const currentDataString = JSON.stringify(prevData);
        
        if (newDataString !== currentDataString) {
          setLastUpdated(new Date());
          
          // Pre-fill completion form with next set in queue
          if (newData.plan && newData.plan.length > 0 && !isEditingRef.current) {
            const nextSet = newData.plan[0]; // First set in queue
            setCompletionForm({
              exercise: nextSet.exercise,
              reps_done: nextSet.reps,
              load_done: nextSet.calculatedLoad || nextSet.load
            });
          }
          // Sync summary draft when not editing
          setSummaryDraft((newData && newData.log && newData.log.summary) ? newData.log.summary : '');
          
          return newData;
        }
        return prevData;
      });
      
      if (showLoading) {
        setLoading(false);
      }
    } catch (err) {
      console.error('Error loading day data:', err);
      setError(err.message);
      if (showLoading) {
        setLoading(false);
      }
    }
  };
  
  useEffect(() => {
    // Initial load
    load(true);
    loadTimer();
    
    // Set up polling every 1 second for data and timer (faster timer updates)
    const interval = setInterval(() => {
      load(false);
      loadTimer();
    }, 1000);
    
    // Cleanup interval on unmount
    return () => clearInterval(interval);
  }, [id]);

  if (loading) return <div><button onClick={onBack}>Back</button><p>Loading day details...</p></div>;
  if (error) return <div><button onClick={onBack}>Back</button><p>Error loading day: {error}</p></div>;
  if (!data) return <div><button onClick={onBack}>Back</button><p>No data found for this day.</p></div>;

  const addPlan = async () => {
    await fetch(`/api/days/${id}/plan`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(newPlan) });
    setNewPlan({ exercise: '', reps: 0, load: 0, rest: 60, order_num: 1 });
    load(false); // Don't show loading spinner for user-initiated actions
  };

  const completeSet = async () => {
    if (data.plan.length === 0) return;
    
    setIsCompleting(true);
    try {
      // Add to completed sets (this will link to the planned set)
      await fetch(`/api/days/${id}/completed`, { 
        method: 'POST', 
        headers: { 'Content-Type': 'application/json' }, 
        body: JSON.stringify({
          ...completionForm,
          planned_set_id: data.plan[0].id  // Link to the planned set
        }) 
      });
      
      // No need to delete the planned set - the backend will filter it out
      // when it's linked to a completed set
      
      // Refresh data and timer
      load(false);
      loadTimer();
    } catch (err) {
      console.error('Error completing set:', err);
    } finally {
      setIsCompleting(false);
    }
  };

  const handleCompletionFormSubmit = (e) => {
    e.preventDefault();
    completeSet();
  };

  const updateSummary = async (summary) => {
    await fetch(`/api/days/${id}/summary`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ summary }) });
  };

  const updatePlan = async (p) => {
    await fetch(`/api/plan/${p.id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(p) });
  };
  const deletePlan = async (pid) => { await fetch(`/api/plan/${pid}`, { method: 'DELETE' }); load(false); };
  const deleteComp = async (cid) => { await fetch(`/api/completed/${cid}`, { method: 'DELETE' }); load(false); };

  const handlePlanChange = (idx, field, value) => {
    const upd = { ...data.plan[idx], [field]: value };
    const copy = [...data.plan];
    copy[idx] = upd;
    setData({ ...data, plan: copy });
  };

  const handlePlanFocus = () => {
    setIsEditing(true);
  };

  const handlePlanBlur = (idx) => {
    setIsEditing(false);
    const updated = data.plan[idx];
    updatePlan(updated);
  };

  const handleCompletionChange = (field, value) => {
    setCompletionForm(prev => ({ ...prev, [field]: value }));
  };

  const handleDelete = async () => {
    if (!deleteConfirm) {
      // First click - show confirmation
      setDeleteConfirm(true);
      // Reset confirmation after 3 seconds if user doesn't confirm
      setTimeout(() => setDeleteConfirm(false), 3000);
    } else {
      // Second click - actually delete
      try {
        await fetch(`/api/days/${id}`, { method: 'DELETE' });
        onBack(); // Navigate back to the list
        if (onDelete) {
          onDelete(id); // Update the parent component's state
        }
      } catch (err) {
        console.error('Error deleting day:', err);
        setDeleteConfirm(false); // Reset on error
      }
    }
  };

  // Styles
  const containerStyle = {
    fontFamily: 'Arial, sans-serif',
    maxWidth: '1200px',
    margin: '0 auto',
    padding: '20px'
  };

  const headerStyle = {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '20px',
    borderBottom: '2px solid #eee',
    paddingBottom: '10px'
  };

  const backButtonStyle = {
    padding: '8px 16px',
    backgroundColor: '#007bff',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer'
  };

  const deleteButtonStyle = {
    padding: '8px 16px',
    backgroundColor: deleteConfirm ? '#dc3545' : '#6c757d',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
    marginLeft: '10px'
  };

  const workoutSectionStyle = {
    display: 'flex',
    gap: '20px',
    marginBottom: '20px'
  };

  const queueSectionStyle = {
    flex: 1,
    border: '1px solid #ddd',
    borderRadius: '8px',
    overflow: 'hidden'
  };

  const completedSectionStyle = {
    flex: 1,
    border: '1px solid #ddd',
    borderRadius: '8px',
    overflow: 'hidden'
  };

  const completionSectionStyle = {
    border: '1px solid #28a745',
    borderRadius: '8px',
    padding: '20px',
    marginBottom: '20px',
    backgroundColor: '#f8fff8'
  };

  const nextSetStyle = {
    backgroundColor: '#e8f5e8',
    padding: '15px',
    borderRadius: '6px',
    marginBottom: '15px',
    border: '2px solid #28a745'
  };

  const completionFormStyle = {
    display: 'flex',
    gap: '10px',
    alignItems: 'end',
    flexWrap: 'wrap'
  };

  const formGroupStyle = {
    display: 'flex',
    flexDirection: 'column',
    gap: '5px'
  };

  const tableHeaderStyle = {
    backgroundColor: '#f8f9fa',
    padding: '12px',
    margin: 0,
    borderBottom: '1px solid #ddd',
    fontSize: '16px',
    fontWeight: 'bold'
  };

  const tableStyle = {
    width: '100%',
    borderCollapse: 'collapse',
    fontSize: '14px'
  };

  const thStyle = {
    backgroundColor: '#f8f9fa',
    padding: '8px',
    textAlign: 'left',
    borderBottom: '1px solid #ddd',
    fontSize: '12px',
    fontWeight: 'bold'
  };

  const tdStyle = {
    padding: '4px',
    borderBottom: '1px solid #eee'
  };

  const inputStyle = {
    width: '100%',
    padding: '4px',
    border: '1px solid #ccc',
    borderRadius: '3px',
    fontSize: '14px'
  };

  const numberInputStyle = {
    ...inputStyle,
    width: '60px',
    textAlign: 'center'
  };

  const orderInputStyle = {
    ...inputStyle,
    width: '40px',
    textAlign: 'center'
  };

  const restInputStyle = {
    ...inputStyle,
    width: '50px',
    textAlign: 'center'
  };

  const buttonStyle = {
    padding: '4px 8px',
    backgroundColor: '#dc3545',
    color: 'white',
    border: 'none',
    borderRadius: '3px',
    cursor: 'pointer',
    fontSize: '12px'
  };

  const addButtonStyle = {
    ...buttonStyle,
    backgroundColor: '#28a745'
  };

  const completeButtonStyle = {
    padding: '10px 20px',
    backgroundColor: '#28a745',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '14px',
    fontWeight: 'bold'
  };

  const summaryStyle = {
    border: '1px solid #ddd',
    borderRadius: '8px',
    padding: '15px'
  };

  const textareaStyle = {
    width: '100%',
    padding: '10px',
    border: '1px solid #ccc',
    borderRadius: '4px',
    fontSize: '14px',
    fontFamily: 'Arial, sans-serif',
    resize: 'vertical'
  };

  const nextSet = data.plan.length > 0 ? data.plan[0] : null;

  // Helper function to display weight with plates
  const displayWeight = (weight) => {
    const result = calculatePlates(weight);
    return formatWeightAndPlates(result.weight, result.plates);
  };

  return (
    <div style={containerStyle}>
      <div style={headerStyle}>
        <div>
          <h2 style={{ margin: 0 }}>Workout Day: {data.log.log_date}</h2>
          {lastUpdated && (
            <div style={{ fontSize: '12px', color: '#666' }}>
              Last updated: {lastUpdated.toLocaleTimeString()}
            </div>
          )}
        </div>
        <div>
          <button style={backButtonStyle} onClick={onBack}>← Back</button>
          <button style={deleteButtonStyle} onClick={handleDelete}>
            {deleteConfirm ? 'Confirm Delete?' : '🗑️ Delete Day'}
          </button>
        </div>
      </div>
      
      {/* Complete Set Section */}
      <div style={completionSectionStyle}>
        <h3 style={{ marginTop: 0, marginBottom: '20px', fontSize: '20px', color: '#155724' }}>Next in Queue:</h3>
        
        {nextSet ? (
          <div style={nextSetStyle}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div style={{ flex: 1 }}>
                <div style={{ marginBottom: '12px' }}>
                  <div style={{ fontSize: '22px', fontWeight: 'bold', color: '#155724', marginBottom: '6px' }}>
                    {nextSet.exercise}
                  </div>
                  <div style={{ fontSize: '18px', fontWeight: 'bold', color: '#333' }}>
                    {nextSet.relative ? (
                      <span>
                        {nextSet.reps} reps @ {nextSet.originalLoad}% → {displayWeight(nextSet.calculatedLoad || nextSet.load)}
                      </span>
                    ) : (
                      <span>
                        {nextSet.reps} reps @ {displayWeight(nextSet.calculatedLoad || nextSet.load)}
                      </span>
                    )}
                  </div>
                  <div style={{ fontSize: '15px', color: '#666', marginTop: '4px' }}>
                    Rest: {nextSet.rest || 60} seconds
                  </div>
                </div>
              </div>
              {timerStatus && (
                <div style={{ textAlign: 'right', marginLeft: '20px', fontSize: '18px', fontWeight: 'bold' }}>
                  {timerStatus.status === 'running' && (
                    <div style={{ color: '#007bff' }}>
                      <div>⏱️ Timer:</div>
                      <div style={{ fontSize: '20px', marginTop: '4px' }}>
                        {Math.floor(timerStatus.remaining_seconds / 60)}:{(timerStatus.remaining_seconds % 60).toString().padStart(2, '0')} remaining
                      </div>
                    </div>
                  )}
                  {timerStatus.status === 'expired' && (
                    <div style={{ color: '#dc3545' }}>
                      <div>⏰ Timer</div>
                      <div style={{ fontSize: '20px', marginTop: '4px' }}>
                        expired!
                      </div>
                    </div>
                  )}
                  {timerStatus.status === 'no_timer' && (
                    <div style={{ color: '#666' }}>
                      No timer set
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        ) : (
          <div style={{ ...nextSetStyle, backgroundColor: '#f8f9fa', borderColor: '#6c757d' }}>
            <div style={{ fontSize: '20px', fontWeight: 'bold', color: '#6c757d', textAlign: 'center', padding: '10px' }}>
              🎉 All sets completed!
            </div>
          </div>
        )}

        {nextSet && (
          <form onSubmit={handleCompletionFormSubmit} style={{ ...completionFormStyle, marginTop: '16px' }}>
            <div style={formGroupStyle}>
              <label style={{ fontSize: '14px', fontWeight: 'bold', color: '#333' }}>Exercise</label>
              <input
                style={{ ...inputStyle, width: '180px', padding: '8px', fontSize: '16px' }}
                value={completionForm.exercise}
                onFocus={() => setIsEditing(true)}
                onBlur={() => setIsEditing(false)}
                onChange={e => handleCompletionChange('exercise', e.target.value)}
                placeholder="Exercise name"
              />
            </div>
            <div style={formGroupStyle}>
              <label style={{ fontSize: '14px', fontWeight: 'bold', color: '#333' }}>Reps Done</label>
              <input
                style={{ ...numberInputStyle, width: '80px', padding: '8px', fontSize: '16px' }}
                type="number"
                value={completionForm.reps_done}
                onFocus={() => setIsEditing(true)}
                onBlur={() => setIsEditing(false)}
                onChange={e => handleCompletionChange('reps_done', parseInt(e.target.value) || 0)}
              />
            </div>
            <div style={formGroupStyle}>
              <label style={{ fontSize: '14px', fontWeight: 'bold', color: '#333' }}>Weight (lbs)</label>
              <input
                style={{ ...numberInputStyle, width: '80px', padding: '8px', fontSize: '16px' }}
                type="number"
                value={completionForm.load_done}
                onFocus={() => setIsEditing(true)}
                onBlur={() => setIsEditing(false)}
                onChange={e => handleCompletionChange('load_done', parseFloat(e.target.value) || 0)}
              />
            </div>
            <button
              type="submit"
              style={{ ...completeButtonStyle, padding: '12px 24px', fontSize: '16px' }}
              disabled={isCompleting}
            >
              {isCompleting ? 'Completing...' : '✓ Complete Set'}
            </button>
          </form>
        )}
      </div>

      <div style={workoutSectionStyle}>
        {/* Set Queue */}
        <div style={queueSectionStyle}>
          <h3 style={tableHeaderStyle}>📋 Set Queue ({data.plan.length} remaining)</h3>
          <table style={tableStyle}>
            <thead>
              <tr>
                <th style={thStyle}>Exercise</th>
                <th style={thStyle}>Reps</th>
                <th style={thStyle}>Load</th>
                <th style={thStyle}>Rest</th>
                <th style={thStyle}>Order</th>
                <th style={thStyle}>Action</th>
              </tr>
            </thead>
            <tbody>
              {data.plan.map((p, i) => (
                <tr key={p.id} style={i === 0 ? { backgroundColor: '#e8f5e8' } : {}}>
                  <td style={tdStyle}>
                    <input 
                      style={inputStyle}
                      value={p.exercise} 
                      onFocus={handlePlanFocus}
                      onBlur={() => handlePlanBlur(i)}
                      onChange={e => handlePlanChange(i,'exercise', e.target.value)} 
                    />
                  </td>
                  <td style={tdStyle}>
                    <input 
                      style={numberInputStyle}
                      type="number" 
                      value={p.reps} 
                      onFocus={handlePlanFocus}
                      onBlur={() => handlePlanBlur(i)}
                      onChange={e => handlePlanChange(i,'reps', parseInt(e.target.value) || 0)} 
                    />
                  </td>
                  <td style={tdStyle}>
                    <input 
                      style={numberInputStyle}
                      type="number" 
                      value={p.load} 
                      onFocus={handlePlanFocus}
                      onBlur={() => handlePlanBlur(i)}
                      onChange={e => handlePlanChange(i,'load', parseFloat(e.target.value) || 0)} 
                    />
                    {p.relative && (
                      <div style={{ fontSize: '10px', color: '#666', marginTop: '1px' }}>
                        {p.load}% → {displayWeight(p.calculatedLoad || p.load)}
                      </div>
                    )}
                    {!p.relative && (
                      <div style={{ fontSize: '11px', color: '#666', marginTop: '2px' }}>
                        {displayWeight(p.load)}
                      </div>
                    )}
                  </td>
                  <td style={tdStyle}>
                    <input 
                      style={restInputStyle}
                      type="number" 
                      value={p.rest || 60} 
                      onFocus={handlePlanFocus}
                      onBlur={() => handlePlanBlur(i)}
                      onChange={e => handlePlanChange(i,'rest', parseInt(e.target.value) || 60)} 
                    />
                  </td>
                  <td style={tdStyle}>
                    <input 
                      style={orderInputStyle}
                      type="number" 
                      value={p.order_num} 
                      onFocus={handlePlanFocus}
                      onBlur={() => handlePlanBlur(i)}
                      onChange={e => handlePlanChange(i,'order_num', parseInt(e.target.value) || 0)} 
                    />
                  </td>
                  <td style={tdStyle}>
                    <button 
                      style={buttonStyle}
                      onClick={() => {deletePlan(p.id);}}
                    >
                      Remove
                    </button>
                  </td>
                </tr>
              ))}
              <tr style={{ backgroundColor: '#f8f9fa' }}>
                <td style={tdStyle}>
                  <input 
                    style={inputStyle}
                    value={newPlan.exercise} 
                    onChange={e => setNewPlan({...newPlan, exercise:e.target.value})} 
                    placeholder="Exercise name"
                  />
                </td>
                <td style={tdStyle}>
                  <input 
                    style={numberInputStyle}
                    type="number" 
                    value={newPlan.reps} 
                    onChange={e => setNewPlan({...newPlan, reps:e.target.value})} 
                  />
                </td>
                <td style={tdStyle}>
                  <input 
                    style={numberInputStyle}
                    type="number" 
                    value={newPlan.load} 
                    onChange={e => setNewPlan({...newPlan, load:e.target.value})} 
                  />
                </td>
                <td style={tdStyle}>
                  <input 
                    style={restInputStyle}
                    type="number" 
                    value={newPlan.rest} 
                    onChange={e => setNewPlan({...newPlan, rest:e.target.value})} 
                  />
                </td>
                <td style={tdStyle}>
                  <input 
                    style={orderInputStyle}
                    type="number" 
                    value={newPlan.order_num} 
                    onChange={e => setNewPlan({...newPlan, order_num:e.target.value})} 
                  />
                </td>
                <td style={tdStyle}>
                  <button 
                    style={addButtonStyle}
                    onClick={addPlan}
                  >
                    Add
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        {/* Completed Sets Log */}
        <div style={completedSectionStyle}>
          <h3 style={tableHeaderStyle}>✅ Completed Sets ({data.completed.length} done)</h3>
          <table style={tableStyle}>
            <thead>
              <tr>
                <th style={thStyle}>Exercise</th>
                <th style={thStyle}>Reps</th>
                <th style={thStyle}>Load</th>
                <th style={thStyle}>Time</th>
                <th style={thStyle}>Action</th>
              </tr>
            </thead>
            <tbody>
              {data.completed.map((c) => (
                <tr key={c.id}>
                  <td style={tdStyle}>
                    <strong>{c.exercise}</strong>
                  </td>
                  <td style={tdStyle}>
                    <strong>{c.reps_done}</strong>
                  </td>
                  <td style={tdStyle}>
                    <strong>{displayWeight(c.load_done)}</strong>
                  </td>
                  <td style={tdStyle}>
                    <span style={{ fontSize: '12px', color: '#666' }}>
                      {(() => {
                        try {
                          if (!c.completed_at) return 'N/A';
                          const date = new Date(c.completed_at);
                          if (isNaN(date.getTime())) return 'Invalid Time';
                          
                          return new Intl.DateTimeFormat('en-US', {
                            timeZone: 'America/New_York',
                            hour: 'numeric',
                            minute: '2-digit',
                            hour12: true
                          }).format(date);
                        } catch (e) {
                          console.error('Date formatting error:', e);
                          return 'Error';
                        }
                      })()}
                    </span>
                  </td>
                  <td style={tdStyle}>
                    <button 
                      style={buttonStyle}
                      onClick={() => {deleteComp(c.id);}}
                    >
                      Remove
                    </button>
                  </td>
                </tr>
              ))}
              {data.completed.length === 0 && (
                <tr>
                  <td colSpan="5" style={{ ...tdStyle, textAlign: 'center', color: '#666', fontStyle: 'italic' }}>
                    No sets completed yet
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div style={summaryStyle}>
        <h3 style={{ marginTop: 0, marginBottom: '10px' }}>📝 Workout Summary</h3>
        <textarea 
          style={textareaStyle}
          rows="4"
          placeholder="Add your workout summary here..."
          value={summaryDraft}
          onFocus={() => setIsEditing(true)}
          onChange={e => setSummaryDraft(e.target.value)} 
          onBlur={() => {
            setIsEditing(false);
            // Optimistically update local data and persist
            setData(prev => prev ? { ...prev, log: { ...prev.log, summary: summaryDraft } } : prev);
            updateSummary(summaryDraft);
          }} 
        />
      </div>
    </div>
  );
}
