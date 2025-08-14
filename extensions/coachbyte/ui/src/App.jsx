import React, { useEffect, useState } from 'react';
import DayDetail from './DayDetail';
import ChatBar from './ChatBar';
import PRTracker from './PRTracker';
import SplitPlanner from './SplitPlanner';
import EditSplitPage from './EditSplitPage';
import { format, parseISO } from 'date-fns';

export default function App() {
  const [days, setDays] = useState([]);
  const [selected, setSelected] = useState(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [showPRTracker, setShowPRTracker] = useState(false);
  const [showSplitPlanner, setShowSplitPlanner] = useState(false);
  const [showEditSplitPage, setShowEditSplitPage] = useState(false);

  const loadDays = async () => {
    try {
      const response = await fetch('/api/days');
      const data = await response.json();
      
      // Update days and track last updated time
      setDays(prevDays => {
        const dataString = JSON.stringify(data);
        const currentDataString = JSON.stringify(prevDays);
        
        if (dataString !== currentDataString) {
          setLastUpdated(new Date());
          return data;
        }
        return prevDays;
      });
      
      setLoading(false);
    } catch (err) {
      console.error('Error loading days:', err);
      setLoading(false);
    }
  };

  useEffect(() => {
    // Initial load
    loadDays();
    
    // Set up polling every 5 seconds
    const interval = setInterval(loadDays, 5000);
    
    // Cleanup interval on unmount
    return () => clearInterval(interval);
  }, []);

  const refreshDays = () => {
    setLoading(true);
    loadDays();
  };

  const deleteDay = async (id) => {
    await fetch(`/api/days/${id}`, { method: 'DELETE' });
    setDays(days.filter(d => d.id !== id));
    if (selected === id) setSelected(null);
  };

  const handleBack = () => {
    setShowPRTracker(false);
    setShowSplitPlanner(false);
    setShowEditSplitPage(false);
    setSelected(null);
    refreshDays(); // Refresh the list when going back
  };

  const handleEditSplit = () => {
    setShowEditSplitPage(true);
    setSelected(null);
    setShowPRTracker(false);
    setShowSplitPlanner(false);
  }

  const handlePRTracker = () => {
    setShowPRTracker(true);
    setSelected(null);
    setShowSplitPlanner(false);
  };

  const handleSplitPlanner = () => {
    setShowSplitPlanner(true);
    setShowPRTracker(false);
    setSelected(null);
  };

  // Styles
  const containerStyle = {
    fontFamily: 'Arial, sans-serif',
    maxWidth: '1200px',
    margin: '0 auto',
    padding: '20px'
  };

  const headerStyle = {
    borderBottom: '2px solid #eee',
    paddingBottom: '15px',
    marginBottom: '20px'
  };

  const titleStyle = {
    margin: 0,
    color: '#333',
    fontSize: '24px'
  };

  const loadingStyle = {
    textAlign: 'center',
    color: '#666',
    fontSize: '16px'
  };

  const emptyStateStyle = {
    textAlign: 'center',
    padding: '40px',
    border: '2px dashed #ddd',
    borderRadius: '8px',
    backgroundColor: '#f8f9fa'
  };

  const tableStyle = {
    width: '100%',
    borderCollapse: 'collapse',
    backgroundColor: 'white',
    borderRadius: '8px',
    overflow: 'hidden',
    boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
  };

  const thStyle = {
    backgroundColor: '#f8f9fa',
    padding: '12px',
    textAlign: 'left',
    borderBottom: '2px solid #ddd',
    fontSize: '14px',
    fontWeight: 'bold',
    color: '#333'
  };

  const tdStyle = {
    padding: '12px',
    borderBottom: '1px solid #eee',
    fontSize: '14px'
  };

  const buttonStyle = {
    padding: '6px 12px',
    margin: '0 4px',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '12px',
    fontWeight: 'bold'
  };

  const viewButtonStyle = {
    ...buttonStyle,
    backgroundColor: '#007bff',
    color: 'white'
  };



  const codeStyle = {
    backgroundColor: '#f8f9fa',
    padding: '2px 6px',
    borderRadius: '3px',
    fontSize: '13px',
    fontFamily: 'monospace'
  };

  const prButtonStyle = {
    padding: '8px 16px',
    backgroundColor: '#28a745',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '14px',
    fontWeight: 'bold'
  };

  const splitButtonStyle = {
    padding: '8px 16px',
    backgroundColor: '#17a2b8',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '14px',
    fontWeight: 'bold',
    marginLeft: '10px'
  };

  const mainView = (
    <div>
      <div style={headerStyle}>
        <div>
          <h1 style={titleStyle}>🏋️ Workout Tracker</h1>
          {lastUpdated && (
            <div style={{ fontSize: '12px', color: '#666' }}>
              Last updated: {lastUpdated.toLocaleTimeString()}
            </div>
          )}
        </div>
        <div>
          <button style={prButtonStyle} onClick={handlePRTracker}>
            💪 View PRs
          </button>
          <button style={splitButtonStyle} onClick={handleEditSplit}>
            📅 Edit Split
          </button>
        </div>
      </div>
      
      {loading && (
        <div style={loadingStyle}>
          <p>Loading workout days...</p>
        </div>
      )}
      
      {!loading && days.length === 0 && (
        <div style={emptyStateStyle}>
          <h3>No workout days found</h3>
          <p>Get started by loading some sample data:</p>
          <p>Run <code style={codeStyle}>npm run load-sample</code> to load sample data.</p>
        </div>
      )}
      
      {!loading && days.length > 0 && (
        <table style={tableStyle}>
          <thead>
            <tr>
              <th style={thStyle}>📅 Date</th>
              <th style={thStyle}>📝 Summary</th>
              <th style={thStyle}>⚡ Actions</th>
            </tr>
          </thead>
          <tbody>
            {days.map(d => (
              <tr key={d.id}>
                <td style={tdStyle}>
                  <strong>{format(parseISO(d.log_date), 'EEE, MMM d, yyyy')}</strong>
                </td>
                <td style={tdStyle}>
                  {d.summary ? (
                    <div style={{ maxWidth: '300px', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {d.summary}
                    </div>
                  ) : (
                    <em style={{ color: '#666' }}>No summary</em>
                  )}
                </td>
                <td style={tdStyle}>
                  <button 
                    style={viewButtonStyle} 
                    onClick={() => setSelected(d.id)}
                  >
                    View Details
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );

  return (
    <>
      <div style={containerStyle}>
        {showEditSplitPage ? (
          <EditSplitPage onBack={handleBack} />
        ) : showSplitPlanner ? (
          <SplitPlanner onBack={handleBack} />
        ) : showPRTracker ? (
          <PRTracker onBack={handleBack} />
        ) : selected ? (
          <DayDetail id={selected} onBack={handleBack} onDelete={deleteDay} />
        ) : (
          mainView
        )}
      </div>
      <ChatBar />
    </>
  );
}
