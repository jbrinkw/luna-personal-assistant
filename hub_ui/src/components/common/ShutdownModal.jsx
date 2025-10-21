import React, { useState } from 'react';
import Modal from './Modal';
import Button from './Button';

export default function ShutdownModal({ isOpen, onClose }) {
  const [shutdownStatus, setShutdownStatus] = useState('confirm'); // confirm, shutting_down, complete

  const handleShutdown = async () => {
    setShutdownStatus('shutting_down');
    
    try {
      const apiHost = window.location.hostname;
      await fetch(`http://${apiHost}:9999/shutdown`, {
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
          <div className="warning-icon" style={{ fontSize: '48px', textAlign: 'center', marginBottom: '16px' }}>
            ⚠️
          </div>
          <p style={{ textAlign: 'center', marginBottom: '8px' }}>
            Are you sure you want to shut down Luna?
          </p>
          <p style={{ textAlign: 'center', fontSize: '14px', color: '#666', marginBottom: '24px' }}>
            All services will stop and you'll need to manually restart the system.
          </p>
          <div className="modal-actions">
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
          <div className="spinner" style={{ margin: '0 auto 16px' }}></div>
          <p style={{ textAlign: 'center', fontSize: '16px', fontWeight: '600' }}>
            Shutting down Luna...
          </p>
          <p style={{ textAlign: 'center', fontSize: '14px', color: '#666' }}>
            All services are stopping
          </p>
        </div>
      )}

      {shutdownStatus === 'complete' && (
        <div className="shutdown-complete">
          <div className="success-icon" style={{ fontSize: '48px', textAlign: 'center', marginBottom: '16px' }}>
            ✅
          </div>
          <p style={{ textAlign: 'center', fontSize: '16px', fontWeight: '600', marginBottom: '8px' }}>
            System Shutdown Complete
          </p>
          <p style={{ textAlign: 'center', fontSize: '14px', color: '#666', marginBottom: '24px' }}>
            You can close this browser tab. To restart Luna, run <code>./luna.sh</code> on the server.
          </p>
          <div style={{ textAlign: 'center' }}>
            <Button onClick={handleClose}>
              Close
            </Button>
          </div>
        </div>
      )}
    </Modal>
  );
}



