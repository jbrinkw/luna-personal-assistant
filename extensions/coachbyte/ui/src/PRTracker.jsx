import React, { useEffect, useState } from 'react';

// Move TrackedPRSection outside to prevent re-creation on every render
const TrackedPRSection = ({ 
  trackedExercises, 
  newTrackedExercise, 
  setNewTrackedExercise, 
  addTrackedExercise, 
  removeTrackedExercise 
}) => {
  return (
    <div style={{ 
      backgroundColor: '#f8f9fa', 
      padding: '20px', 
      borderRadius: '8px', 
      border: '1px solid #ddd',
      marginTop: '20px'
    }}>
      <h3 style={{ marginBottom: '8px', fontSize: '18px' }}>Tracked Exercises</h3>
      <p style={{ color: '#666', fontSize: '13px', marginBottom: '15px' }}>
        Add exercises to track all rep ranges for those exercises automatically.
      </p>
      
      {/* Add new tracked exercise - compact version */}
      <div style={{ marginBottom: '15px' }}>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <input
            placeholder="Exercise name (e.g., Bench Press, Squat)"
            value={newTrackedExercise}
            onChange={e => setNewTrackedExercise(e.target.value)}
            style={{ 
              flex: 1, 
              padding: '6px 10px', 
              borderRadius: '4px', 
              border: '1px solid #ddd',
              fontSize: '13px'
            }}
            onKeyPress={e => e.key === 'Enter' && addTrackedExercise()}
          />
          <button 
            onClick={addTrackedExercise}
            style={{
              padding: '6px 12px',
              backgroundColor: '#28a745',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '13px'
            }}
          >
            Add
          </button>
        </div>
      </div>

      {/* List of tracked exercises - compact version */}
      {trackedExercises.length === 0 ? (
        <div style={{ color: '#666', fontStyle: 'italic', fontSize: '13px' }}>No exercises being tracked</div>
      ) : (
        <div>
          <div style={{ fontSize: '14px', fontWeight: 'bold', marginBottom: '10px' }}>
            Currently Tracking ({trackedExercises.length} exercises)
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
            {trackedExercises.map(exercise => (
              <div key={exercise} style={{
                display: 'flex',
                alignItems: 'center',
                backgroundColor: 'white',
                padding: '6px 10px',
                borderRadius: '4px',
                border: '1px solid #ddd',
                fontSize: '13px'
              }}>
                <span style={{ marginRight: '8px' }}>{exercise}</span>
                <button 
                  onClick={() => removeTrackedExercise(exercise)}
                  style={{
                    padding: '2px 6px',
                    backgroundColor: '#dc3545',
                    color: 'white',
                    border: 'none',
                    borderRadius: '3px',
                    cursor: 'pointer',
                    fontSize: '11px'
                  }}
                >
                  Remove
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default function PRTracker({ onBack }) {
  const [prs, setPRs] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [trackedExercises, setTrackedExercises] = useState([]);
  const [newTrackedExercise, setNewTrackedExercise] = useState('');

  const computeEstimated1RM = (reps, load) => Math.round(load * (1 + reps / 30));

  const processPRs = (data) => {
    const processed = {};
    for (const [exercise, prList] of Object.entries(data)) {
      const sorted = [...prList].sort((a, b) => a.reps - b.reps);
      const hasOneRM = sorted.some(pr => pr.reps === 1);
      if (!hasOneRM && sorted.length > 0) {
        const next = sorted[0];
        const estimated = computeEstimated1RM(next.reps, next.maxLoad);
        processed[exercise] = [
          { reps: 1, maxLoad: estimated, estimated: true },
          ...sorted
        ];
      } else {
        processed[exercise] = sorted;
      }
    }
    return processed;
  };

  const loadPRs = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/prs');
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      setPRs(processPRs(data));
      setError(null);
    } catch (err) {
      console.error('Error loading PRs:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const loadTrackedExercises = async () => {
    try {
      const response = await fetch('/api/tracked-exercises');
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      setTrackedExercises(data);
    } catch (err) {
      console.error('Error loading tracked exercises:', err);
    }
  };

  const addTrackedExercise = async () => {
    if (!newTrackedExercise.trim()) return;
    await fetch('/api/tracked-exercises', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ exercise: newTrackedExercise.trim() })
    });
    setNewTrackedExercise('');
    loadTrackedExercises();
    loadPRs(); // Refresh PRs to show new tracked exercise
  };

  const removeTrackedExercise = async (exercise) => {
    await fetch('/api/tracked-exercises', {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ exercise })
    });
    loadTrackedExercises();
    loadPRs(); // Refresh PRs to remove untracked exercise
  };

  useEffect(() => {
    loadPRs();
    loadTrackedExercises();
  }, []);

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

  const titleStyle = {
    margin: 0,
    color: '#333',
    fontSize: '24px'
  };

  const exerciseCardStyle = {
    backgroundColor: 'white',
    borderRadius: '8px',
    padding: '20px',
    marginBottom: '20px',
    boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
    border: '1px solid #ddd'
  };

  const exerciseNameStyle = {
    fontSize: '20px',
    fontWeight: 'bold',
    marginBottom: '15px',
    color: '#333',
    textTransform: 'capitalize'
  };

  const prListStyle = {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '10px'
  };

  const prItemStyle = {
    backgroundColor: '#f8f9fa',
    padding: '8px 12px',
    borderRadius: '4px',
    border: '1px solid #ddd',
    fontSize: '14px',
    fontWeight: 'bold'
  };

  const loadingStyle = {
    textAlign: 'center',
    color: '#666',
    fontSize: '16px'
  };

  const errorStyle = {
    textAlign: 'center',
    color: '#dc3545',
    fontSize: '16px'
  };

  const emptyStateStyle = {
    textAlign: 'center',
    padding: '40px',
    border: '2px dashed #ddd',
    borderRadius: '8px',
    backgroundColor: '#f8f9fa',
    color: '#666'
  };

  const noDataStyle = {
    color: '#666',
    fontStyle: 'italic',
    fontSize: '14px'
  };

  // Bundle styles for passing to child component
  const styles = {
    exerciseCardStyle,
    exerciseNameStyle,
    prListStyle,
    prItemStyle,
    noDataStyle
  };

  if (loading) {
    return (
      <div style={containerStyle}>
        <div style={headerStyle}>
          <h1 style={titleStyle}>💪 Personal Records</h1>
          <button style={backButtonStyle} onClick={onBack}>Back</button>
        </div>
        <div style={loadingStyle}>
          <p>Loading your PRs...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={containerStyle}>
        <div style={headerStyle}>
          <h1 style={titleStyle}>💪 Personal Records</h1>
          <button style={backButtonStyle} onClick={onBack}>Back</button>
        </div>
        <div style={errorStyle}>
          <p>Error loading PRs: {error}</p>
        </div>
      </div>
    );
  }

  const exerciseNames = Object.keys(prs);
  const hasData = exerciseNames.length > 0;

  return (
    <div style={containerStyle}>
      <div style={headerStyle}>
        <h1 style={titleStyle}>💪 Personal Records</h1>
        <button style={backButtonStyle} onClick={onBack}>Back</button>
      </div>

      {!hasData ? (
        <div style={emptyStateStyle}>
          <h3>No PRs tracked yet</h3>
          <p>Complete some workouts with tracked exercises to see your personal records here!</p>
        </div>
      ) : (
        <div>
          {exerciseNames.map(exercise => (
            <div key={exercise} style={exerciseCardStyle}>
              <h2 style={exerciseNameStyle}>{exercise}</h2>
              {prs[exercise] && prs[exercise].length > 0 ? (
                <div style={prListStyle}>
                  {prs[exercise].map((pr, index) => (
                    <div key={index} style={prItemStyle}>
                      {pr.reps} rep{pr.reps !== 1 ? 's' : ''}: {pr.maxLoad} lbs{pr.estimated ? ' (estimated)' : ''}
                    </div>
                  ))}
                </div>
              ) : (
                <div style={noDataStyle}>No PRs recorded for this exercise yet</div>
              )}
            </div>
          ))}
        </div>
      )}
      <TrackedPRSection 
        trackedExercises={trackedExercises}
        newTrackedExercise={newTrackedExercise}
        setNewTrackedExercise={setNewTrackedExercise}
        addTrackedExercise={addTrackedExercise}
        removeTrackedExercise={removeTrackedExercise}
      />
    </div>
  );
}