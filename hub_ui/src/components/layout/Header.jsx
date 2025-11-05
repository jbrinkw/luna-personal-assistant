import React, { useState, useMemo } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useSystem } from '../../context/SystemContext';
import { useConfig } from '../../context/ConfigContext';
import StatusIndicator from '../common/StatusIndicator';
import RestartModal from '../common/RestartModal';
import Button from '../common/Button';

export default function Header() {
  const { health, version } = useSystem();
  const { queuedState, originalState } = useConfig();
  const [showRestartModal, setShowRestartModal] = useState(false);
  const navigate = useNavigate();
  
  // Calculate pending count from queue
  const pendingCount = useMemo(() => {
    if (!queuedState) return 0;
    
    let count = queuedState.operations?.length || 0;
    
    // Add config changes count
    if (queuedState.master_config && originalState) {
      const queuedExts = queuedState.master_config.extensions || {};
      const originalExts = originalState.extensions || {};
      
      Object.keys(queuedExts).forEach(extName => {
        if (originalExts[extName] && queuedExts[extName].enabled !== originalExts[extName].enabled) {
          count++;
        }
      });

      const queuedTools = queuedState.master_config.tool_configs || {};
      const originalTools = originalState.tool_configs || {};
      const toolNames = new Set([...Object.keys(queuedTools), ...Object.keys(originalTools)]);
      toolNames.forEach(toolName => {
        const queuedTool = queuedTools[toolName];
        const originalTool = originalTools[toolName];
        const serializedQueued = JSON.stringify(queuedTool || {});
        const serializedOriginal = JSON.stringify(originalTool || {});
        if (serializedQueued !== serializedOriginal) {
          count++;
        }
      });
    }
    
    return count;
  }, [queuedState, originalState]);
  
  const hasPendingChanges = pendingCount > 0;

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
          className="docs-button"
          onClick={() => window.open('https://docs.lunahub.dev', '_blank')}
          title="User guide and technical documentation at docs.lunahub.dev"
        >
          <span className="docs-icon" aria-hidden="true">📚</span>
          <span className="docs-label">User Guide & Docs</span>
        </Button>

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

