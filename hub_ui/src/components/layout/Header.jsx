import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useSystem } from '../../context/SystemContext';
import { useConfig } from '../../context/ConfigContext';
import StatusIndicator from '../common/StatusIndicator';
import RestartModal from '../common/RestartModal';
import Button from '../common/Button';

export default function Header() {
  const { health, version } = useSystem();
  const { hasChanges, pendingChanges } = useConfig();
  const [showRestartModal, setShowRestartModal] = useState(false);

  return (
    <div className="header">
      <div className="header-left">
        <Link to="/" className="header-logo">
          <h1>🌙 Luna Hub</h1>
        </Link>
        <p className="header-subtitle">AI Agent Platform</p>
      </div>
      
      <div className="header-right">
        {hasChanges && (
          <Link to="/queue" className="pending-changes-badge">
            ⚠️ {pendingChanges.length} pending change{pendingChanges.length !== 1 ? 's' : ''}
          </Link>
        )}
        
        <div className="system-health">
          <StatusIndicator status={health} />
          <span className="health-text">
            {health === 'online' ? 'Healthy' : health === 'offline' ? 'Offline' : 'Checking...'}
          </span>
        </div>
        
        {version && version !== 'unknown' && (
          <span className="version-badge">v{version}</span>
        )}

        <Button 
          size="sm" 
          variant="primary"
          onClick={() => setShowRestartModal(true)}
          title="Restart Luna system"
        >
          🔄 Restart
        </Button>
      </div>

      <RestartModal 
        isOpen={showRestartModal} 
        onClose={() => setShowRestartModal(false)} 
        onSuccess={() => window.location.reload()}
      />
    </div>
  );
}


