import React, { useEffect, useState } from 'react';

export default function EditSplitPage({ onBack }) {
  const dayNames = ['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'];
  const emptySet = { exercise: '', reps: 0, load: 0, rest: 60, order_num: 1, relative: false };
  const [split, setSplit] = useState(() => Object.fromEntries(dayNames.map((_,i)=>[i,[]])));
  const [newSets, setNewSets] = useState(() => Object.fromEntries(dayNames.map((_,i)=>[i,{...emptySet}])));
  const [loading, setLoading] = useState(true);

  const loadSplit = async () => {
    try {
      const resp = await fetch('/api/split');
      const data = await resp.json();
      const grouped = Object.fromEntries(dayNames.map((_,i)=>[i,[]]));
      data.forEach(row => {
        grouped[row.day_of_week].push(row);
      });
      setSplit(grouped);
      setLoading(false);
    } catch (err) {
      console.error('Error loading split:', err);
      setLoading(false);
    }
  };

  useEffect(() => { loadSplit(); }, []);

  const handleChange = async (day, idx, field, value) => {
    const upd = { ...split[day][idx], [field]: value };
    const copy = { ...split };
    copy[day][idx] = upd;
    setSplit(copy);
    await fetch(`/api/split/plan/${upd.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(upd)
    });
  };

  const addSet = async (day) => {
    const payload = newSets[day];
    await fetch(`/api/split/${day}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    setNewSets({ ...newSets, [day]: { ...emptySet } });
    loadSplit();
  };

  const deleteSet = async (day, id) => {
    await fetch(`/api/split/plan/${id}`, { method: 'DELETE' });
    loadSplit();
  };

  const containerStyle = { padding: '20px', maxWidth: '1000px', margin: '0 auto', fontFamily: 'Arial, sans-serif' };
  const backButtonStyle = { padding: '8px 16px', backgroundColor: '#007bff', color:'white', border:'none', borderRadius:'4px', cursor:'pointer', marginBottom:'20px' };
  const tableStyle = { width:'100%', borderCollapse:'collapse', fontSize:'14px' };
  const thStyle = { backgroundColor:'#f8f9fa', padding:'8px', textAlign:'left', borderBottom:'1px solid #ddd', fontSize:'12px', fontWeight:'bold' };
  const tdStyle = { padding:'4px', borderBottom:'1px solid #eee' };
  const inputStyle = { width:'100%', padding:'4px', border:'1px solid #ccc', borderRadius:'3px', fontSize:'14px' };
  const numberInputStyle = { ...inputStyle, width:'60px', textAlign:'center' };
  const orderInputStyle = { ...inputStyle, width:'40px', textAlign:'center' };
  const restInputStyle = { ...inputStyle, width:'50px', textAlign:'center' };
  const buttonStyle = { padding:'4px 8px', backgroundColor:'#dc3545', color:'white', border:'none', borderRadius:'3px', cursor:'pointer', fontSize:'12px' };
  const addButtonStyle = { ...buttonStyle, backgroundColor:'#28a745' };

  return (
    <div style={containerStyle}>
      <button style={backButtonStyle} onClick={onBack}>← Back</button>
      <h2>Weekly Split</h2>
      {loading && <p>Loading split...</p>}
      {!loading && dayNames.map((name, idx) => (
        <div key={idx} style={{marginBottom:'40px'}}>
          <h3 style={{marginBottom:'10px'}}>{name}</h3>
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
              {split[idx].map((p, i) => (
                <tr key={p.id}>
                  <td style={tdStyle}>
                    <input style={inputStyle} value={p.exercise}
                      onChange={e=>handleChange(idx,i,'exercise',e.target.value)} />
                  </td>
                  <td style={tdStyle}>
                    <input style={numberInputStyle} type="number" value={p.reps}
                      onChange={e=>handleChange(idx,i,'reps',e.target.value)} />
                  </td>
                  <td style={tdStyle}>
                    <input style={numberInputStyle} type="number" value={p.load}
                      onChange={e=>handleChange(idx,i,'load',e.target.value)} />
                    <input type="checkbox" style={{marginLeft:'4px'}}
                      checked={p.relative || false}
                      onChange={e=>handleChange(idx,i,'relative',e.target.checked)} />
                  </td>
                  <td style={tdStyle}>
                    <input style={restInputStyle} type="number" value={p.rest || 60}
                      onChange={e=>handleChange(idx,i,'rest',e.target.value)} />
                  </td>
                  <td style={tdStyle}>
                    <input style={orderInputStyle} type="number" value={p.order_num}
                      onChange={e=>handleChange(idx,i,'order_num',e.target.value)} />
                  </td>
                  <td style={tdStyle}>
                    <button style={buttonStyle} onClick={()=>deleteSet(idx,p.id)}>Remove</button>
                  </td>
                </tr>
              ))}
              <tr style={{backgroundColor:'#f8f9fa'}}>
                <td style={tdStyle}>
                  <input style={inputStyle} value={newSets[idx].exercise}
                    onChange={e=>setNewSets({...newSets,[idx]:{...newSets[idx],exercise:e.target.value}})}
                    placeholder="Exercise" />
                </td>
                <td style={tdStyle}>
                  <input style={numberInputStyle} type="number" value={newSets[idx].reps}
                    onChange={e=>setNewSets({...newSets,[idx]:{...newSets[idx],reps:e.target.value}})} />
                </td>
                <td style={tdStyle}>
                  <input style={numberInputStyle} type="number" value={newSets[idx].load}
                    onChange={e=>setNewSets({...newSets,[idx]:{...newSets[idx],load:e.target.value}})} />
                  <input type="checkbox" style={{marginLeft:'4px'}}
                    checked={newSets[idx].relative || false}
                    onChange={e=>setNewSets({...newSets,[idx]:{...newSets[idx],relative:e.target.checked}})} />
                </td>
                <td style={tdStyle}>
                  <input style={restInputStyle} type="number" value={newSets[idx].rest}
                    onChange={e=>setNewSets({...newSets,[idx]:{...newSets[idx],rest:e.target.value}})} />
                </td>
                <td style={tdStyle}>
                  <input style={orderInputStyle} type="number" value={newSets[idx].order_num}
                    onChange={e=>setNewSets({...newSets,[idx]:{...newSets[idx],order_num:e.target.value}})} />
                </td>
                <td style={tdStyle}>
                  <button style={addButtonStyle} onClick={()=>addSet(idx)}>Add</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      ))}
    </div>
  );
} 