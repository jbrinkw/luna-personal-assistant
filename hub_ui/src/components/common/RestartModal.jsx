import React, { useState, useEffect } from 'react';
import { SystemAPI } from '../../lib/api';
import Modal from './Modal';
import LoadingSpinner from './LoadingSpinner';

const PHASES = [
  "Stopping services...",
  "Installing extensions...",
  "Installing dependencies...",
  "Starting services...",
  "Performing health checks..."
];

export default function RestartModal({ isOpen, onClose, onSuccess }) {
  const [phase, setPhase] = useState('initiating');
  const [phaseMessage, setPhaseMessage] = useState('System Restarting...');
  const [phaseIndex, setPhaseIndex] = useState(0);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!isOpen) {
      // Reset state when modal closes
      setPhase('initiating');
      setPhaseMessage('System Restarting...');
      setPhaseIndex(0);
      setError(null);
      return;
    }

    // Start the restart process
    startRestart();
  }, [isOpen]);

  const startRestart = async () => {
    try {
      await SystemAPI.restart();
      
      // Wait 5 seconds before starting to poll
      setTimeout(() => {
        setPhase('offline');
        cyclePhases();
        setTimeout(startPolling, 5000);
      }, 5000);
    } catch (error) {
      console.error('Failed to initiate restart:', error);
      setError('Failed to initiate restart. Please try again.');
      setPhase('error');
    }
  };

  const cyclePhases = () => {
    let currentPhase = 0;
    const interval = setInterval(() => {
      currentPhase = (currentPhase + 1) % PHASES.length;
      setPhaseIndex(currentPhase);
      setPhaseMessage(PHASES[currentPhase]);
    }, 25000); // Change phase every 25 seconds

    // Store interval ID so we can clear it later
    window.restartPhaseInterval = interval;
  };

  const startPolling = () => {
    setPhase('polling');
    setPhaseMessage('Starting Up...');
    
    let attempts = 0;
    const maxAttempts = 150; // 5 minutes at 2s intervals
    
    const interval = setInterval(async () => {
      try {
        const isHealthy = await SystemAPI.health();
        if (isHealthy) {
          clearInterval(interval);
          if (window.restartPhaseInterval) {
            clearInterval(window.restartPhaseInterval);
          }
          setPhase('success');
          setPhaseMessage('System ready!');
          setTimeout(() => {
            if (onSuccess) {
              onSuccess();
            } else {
              window.location.reload();
            }
          }, 1000);
        }
      } catch (e) {
        // Expected during restart
      }
      
      attempts++;
      if (attempts >= maxAttempts) {
        clearInterval(interval);
        if (window.restartPhaseInterval) {
          clearInterval(window.restartPhaseInterval);
        }
        setPhase('timeout');
        setPhaseMessage('Restart taking longer than expected');
        setError('The system is taking longer than expected to restart. You can wait longer or refresh the page manually.');
      }
    }, 2000);
  };

  const handleRetry = () => {
    setError(null);
    startRestart();
  };

  const handleForceReload = () => {
    window.location.reload();
  };

  return (
    <Modal isOpen={isOpen} onClose={null} title="System Restart" size="md">
      <div className="restart-modal-content">
        {phase === 'error' && (
          <div className="restart-error">
            <div className="error-icon">❌</div>
            <p>{error}</p>
            <div className="modal-actions">
              <button className="btn btn-secondary" onClick={onClose}>
                Cancel
              </button>
              <button className="btn btn-primary" onClick={handleRetry}>
                Retry
              </button>
            </div>
          </div>
        )}

        {phase === 'timeout' && (
          <div className="restart-timeout">
            <div className="warning-icon">⏱️</div>
            <p>{phaseMessage}</p>
            <p className="help-text">{error}</p>
            <div className="modal-actions">
              <button className="btn btn-secondary" onClick={onClose}>
                Keep Waiting
              </button>
              <button className="btn btn-primary" onClick={handleForceReload}>
                Reload Now
              </button>
            </div>
          </div>
        )}

        {phase === 'success' && (
          <div className="restart-success">
            <div className="success-icon">✅</div>
            <p>{phaseMessage}</p>
          </div>
        )}

        {(phase === 'initiating' || phase === 'offline' || phase === 'polling') && (
          <div className="restart-progress">
            <LoadingSpinner size="lg" />
            <p className="progress-message">{phaseMessage}</p>
            {phase === 'offline' && (
              <div className="progress-info">
                <p className="progress-detail">This may take several minutes...</p>
              </div>
            )}
            {phase === 'polling' && (
              <div className="progress-info">
                <p className="progress-detail">Waiting for system to respond...</p>
              </div>
            )}
          </div>
        )}
      </div>
    </Modal>
  );
}



