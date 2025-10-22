import React, { useState } from 'react';
import Modal from './Modal';
import Button from './Button';

export default function ShutdownModal({ isOpen, onClose }) {
  const [shutdownStatus, setShutdownStatus] = useState('confirm'); // confirm, shutting_down, complete

  const handleShutdown = async () => {
    setShutdownStatus('shutting_down');
    
    try {
      // Use relative path through Caddy reverse proxy
      await fetch('/api/supervisor/shutdown', {
        method: 'POST',
      });
      
      // Give it a moment to start shutting down
      setTimeout(() => {
        setShutdownStatus('complete');
      }, 2000);
    } catch (error) {
      console.error('Shutdown request sent');
      // Even if fetch fails due to server going down, that's expected
      setShutdownStatus('complete');
    }
  };

  const handleClose = () => {
    setShutdownStatus('confirm');
    onClose();
  };

  return (
    <Modal isOpen={isOpen} onClose={shutdownStatus === 'confirm' ? handleClose : null} title="Shutdown System" size="sm">
      {shutdownStatus === 'confirm' && (
        <div className="shutdown-confirm">
          <div className="shutdown-icon shutdown-warning-icon">
            ⚠️
          </div>
          <p className="shutdown-text">
            Are you sure you want to shut down Luna?
          </p>
          <p className="shutdown-text-muted">
            All services will stop and you'll need to manually restart the system.
          </p>
          <div className="modal-actions shutdown-actions">
            <Button variant="secondary" onClick={handleClose}>
              Cancel
            </Button>
            <Button variant="danger" onClick={handleShutdown}>
              Shutdown
            </Button>
          </div>
        </div>
      )}

      {shutdownStatus === 'shutting_down' && (
        <div className="shutdown-progress">
          <div className="spinner spinner-centered"></div>
          <p className="shutdown-text fw-semibold">
            Shutting down Luna...
          </p>
          <p className="shutdown-text-muted mb-0">
            All services are stopping
          </p>
        </div>
      )}

      {shutdownStatus === 'complete' && (
        <div className="shutdown-complete">
          <div className="shutdown-icon shutdown-success-icon">
            ✅
          </div>
          <p className="shutdown-text fw-semibold">
            System Shutdown Complete
          </p>
          <p className="shutdown-text-muted">
            You can close this browser tab. To restart Luna, run <code>./luna.sh</code> on the server.
          </p>
          <div className="shutdown-close">
            <Button onClick={handleClose}>
              Close
            </Button>
          </div>
        </div>
      )}
    </Modal>
  );
}
