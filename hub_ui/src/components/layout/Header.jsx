import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useSystem } from '../../context/SystemContext';
import { useConfig } from '../../context/ConfigContext';
import StatusIndicator from '../common/StatusIndicator';
import RestartModal from '../common/RestartModal';
import Button from '../common/Button';

export default function Header() {
  const { health, version } = useSystem();
  const { hasChanges, pendingChanges } = useConfig();
  const [showRestartModal, setShowRestartModal] = useState(false);
  const navigate = useNavigate();
  const pendingCount = pendingChanges?.length || 0;
  const hasPendingChanges = hasChanges && pendingCount > 0;

  return (
    <div className="header">
      <div className="header-left">
        <Link to="/" className="header-logo">
          <h1>🌙 Luna Hub</h1>
        </Link>
        <p className="header-subtitle">AI Agent Platform</p>
      </div>
      
      <div className="header-right">
        <Button
          size="sm"
          variant="secondary"
          className={`update-manager-button${hasPendingChanges ? ' has-pending' : ''}`}
          onClick={() => navigate('/queue')}
          title="Open Update Manager"
        >
          <span className="update-manager-icon" aria-hidden="true">🛠️</span>
          <span className="update-manager-label">Update Manager</span>
          {hasPendingChanges && (
            <span className="update-manager-badge">
              {pendingCount}
            </span>
          )}
        </Button>
        
        <div className="system-health">
          <StatusIndicator status={health} />
          <span className="health-text">
            {health === 'online' ? 'Healthy' : health === 'offline' ? 'Offline' : 'Checking...'}
          </span>
        </div>
        
        {version && version !== 'unknown' && (
          <span className="version-badge">v{version}</span>
        )}

        <a
          href="https://docs.lunahub.dev"
          target="_blank"
          rel="noopener noreferrer"
          className="button button-sm button-secondary"
          title="User guide and technical documentation"
        >
          📚 Docs
        </a>

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

