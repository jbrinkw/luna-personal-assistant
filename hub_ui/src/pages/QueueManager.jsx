import React, { useState } from 'react';
import { useConfig } from '../context/ConfigContext';
import Button from '../components/common/Button';
import { ConfirmModal } from '../components/common/Modal';
import RestartModal from '../components/common/RestartModal';
import LoadingSpinner from '../components/common/LoadingSpinner';

export default function UpdateManager() {
  const { 
    originalState,
    queuedState, 
    deleteQueue, 
    loading,
    addCoreUpdate,
    removeCoreUpdate,
    removeQueueItem,
    checkForCoreUpdates,
    clearCoreUpdateInfo,
    coreUpdateInfo
  } = useConfig();
  
  const [showDeleteQueueConfirm, setShowDeleteQueueConfirm] = useState(false);
  const [showRestartModal, setShowRestartModal] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [removingItem, setRemovingItem] = useState(null);
  const [coreCheckLoading, setCoreCheckLoading] = useState(false);
  const [coreCheckError, setCoreCheckError] = useState(null);
  const hasCoreUpdateData = coreUpdateInfo && !coreUpdateInfo.error;
  const coreStatusMessage = coreCheckError || coreUpdateInfo?.error || null;

  const handleDeleteQueue = async () => {
    try {
      setDeleting(true);
      await deleteQueue();
      setShowDeleteQueueConfirm(false);
    } catch (error) {
      console.error('Failed to delete queue:', error);
      alert('Failed to delete queue: ' + error.message);
    } finally {
      setDeleting(false);
    }
  };

  const handleRestartAndApply = () => {
    setShowRestartModal(true);
  };

  const handleRemoveQueueItem = async (operation) => {
    const itemKey = `${operation.type}:${operation.target || operation.target_version || 'core'}`;
    setRemovingItem(itemKey);
    try {
      await removeQueueItem(operation);
    } catch (error) {
      console.error('Failed to remove queue item:', error);
      alert('Failed to remove queue item: ' + error.message);
    } finally {
      setRemovingItem(null);
    }
  };

  const handleCheckCoreUpdates = async () => {
    setCoreCheckLoading(true);
    setCoreCheckError(null);
    try {
      await checkForCoreUpdates();
    } catch (error) {
      setCoreCheckError(error.message || 'Update check failed');
      console.error('Core update check failed:', error);
    } finally {
      setCoreCheckLoading(false);
    }
  };

  const handleClearCoreUpdateInfo = () => {
    clearCoreUpdateInfo();
    setCoreCheckError(null);
  };

  const handleReinstallCore = async () => {
    if (!coreUpdateInfo || !coreUpdateInfo.current) {
      alert('Please check for updates first to get current version info');
      return;
    }
    const currentVersion = coreUpdateInfo.current.version || coreUpdateInfo.current.commit;
    if (!currentVersion) {
      alert('Unable to determine current version');
      return;
    }
    // Add core update with current version (this will force a git reset --hard to current commit)
    await addCoreUpdate(currentVersion);
  };

  if (loading) {
    return (
      <div className="page-container">
        <LoadingSpinner message="Loading queue..." />
      </div>
    );
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1>Update Manager</h1>
          <p className="page-subtitle">Manage system updates and configuration changes</p>
        </div>
      </div>

      <div className="queue-section">
        <div className="queue-section-header">
          <h2>Core Updates</h2>
          <div className="queue-section-actions">
            <Button
              onClick={handleCheckCoreUpdates}
              disabled={coreCheckLoading}
            >
              {coreCheckLoading ? 'Checking...' : 'Check for Core Updates'}
            </Button>
            {hasCoreUpdateData && (
              <Button
                variant="secondary"
                onClick={handleReinstallCore}
                title="Force reinstall current Luna core version (git reset --hard)"
              >
                🔧 Reinstall Core
              </Button>
            )}
            {(coreUpdateInfo || coreCheckError) && (
              <Button
                variant="secondary"
                onClick={handleClearCoreUpdateInfo}
              >
                Clear
              </Button>
            )}
          </div>
        </div>

        {coreStatusMessage && (
          <div className="queue-info">
            <div className="queue-stat">
              <span className="stat-label">Status:</span>
              <span className="stat-value">{coreStatusMessage}</span>
            </div>
          </div>
        )}

        {hasCoreUpdateData ? (
          <div className="queue-info">
            <div className="queue-stat">
              <span className="stat-label">Current:</span>
              <span className="stat-value">
                {(coreUpdateInfo.current?.version || 'unknown')} ({coreUpdateInfo.current?.commit || '???????'})
              </span>
            </div>
            <div className="queue-stat">
              <span className="stat-label">Remote:</span>
              <span className="stat-value">
                {(coreUpdateInfo.remote?.version || 'unknown')} ({coreUpdateInfo.remote?.commit || '???????'})
              </span>
            </div>
            <div className="queue-stat">
              <span className="stat-label">Updates:</span>
              <span className="stat-value">
                {coreUpdateInfo.update_available ? 'Available' : 'Up to date'}
              </span>
            </div>
          </div>
        ) : (!coreStatusMessage && (
          <div className="queue-info">
            <div className="queue-stat">
              <span className="stat-label">Status:</span>
              <span className="stat-value">Click the check button to compare against origin/main.</span>
            </div>
          </div>
        ))}
      </div>

      {/* Queue Section */}
      {queuedState && (
        <div className="queue-section">
          <div className="queue-section-header">
            <h2>Queue</h2>
            <div className="queue-section-actions">
              <Button 
                variant="danger" 
                onClick={() => setShowDeleteQueueConfirm(true)}
                disabled={deleting}
              >
                {deleting ? 'Deleting...' : 'Clear Queue'}
              </Button>
              <Button 
                onClick={handleRestartAndApply}
              >
                🔄 Restart & Apply Updates
              </Button>
            </div>
          </div>

          <div className="queue-info">
            <div className="queue-stat">
              <span className="stat-label">Operations:</span>
              <span className="stat-value">{(() => {
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
              })()}</span>
            </div>
            {queuedState.created_at && (
              <div className="queue-stat">
                <span className="stat-label">Created:</span>
                <span className="stat-value">{new Date(queuedState.created_at).toLocaleString()}</span>
              </div>
            )}
          </div>

          {queuedState.operations && queuedState.operations.length > 0 && (
            <div className="operations-list">
              <h3>Queued Operations:</h3>
              {queuedState.operations.map((op, index) => {
                const itemKey = `${op.type}:${op.target || op.target_version || 'core'}`;
                return (
                  <div key={index} className="operation-item">
                    <span className="operation-type">{op.type.toUpperCase().replace('_', ' ')}</span>
                    <span className="operation-target">
                      {op.type === 'update_core' ? 'Luna Core' : op.target}
                    </span>
                    {op.source && <span className="operation-source">from {op.source}</span>}
                    {op.target_version && <span className="operation-source">→ {op.target_version}</span>}
                    <Button
                      size="sm"
                      variant="danger"
                      onClick={() => handleRemoveQueueItem(op)}
                      disabled={removingItem === itemKey}
                      title="Remove from queue"
                    >
                      {removingItem === itemKey ? 'Removing...' : '✕'}
                    </Button>
                  </div>
                );
              })}
            </div>
          )}

          {/* Show config changes that will be applied */}
          {queuedState.master_config && originalState && (() => {
            const configChanges = [];
            const queuedExts = queuedState.master_config.extensions || {};
            const originalExts = originalState.extensions || {};
            
            Object.keys(queuedExts).forEach(extName => {
              const queuedExt = queuedExts[extName];
              const originalExt = originalExts[extName];
              if (originalExt && queuedExt.enabled !== originalExt.enabled) {
                configChanges.push({
                  type: 'config',
                  target: extName,
                  detail: `${queuedExt.enabled ? 'Enable' : 'Disable'} extension`,
                });
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
                configChanges.push({
                  type: 'tool_config',
                  target: toolName,
                  detail: 'Update tool configuration',
                });
              }
            });

            if (configChanges.length > 0) {
              return (
                <div className="operations-list">
                  <h3>Configuration Changes:</h3>
                  {configChanges.map((change, index) => {
                    const itemKey = `config:${change.target}`;
                    // Create a pseudo-operation for removeQueueItem
                    const pseudoOp = { 
                      type: 'config', 
                      target: change.target 
                    };
                    return (
                      <div key={`config-${index}`} className="operation-item">
                        <span className="operation-type">CONFIG</span>
                        <span className="operation-target">{change.target}</span>
                        <span className="operation-source">{change.detail}</span>
                        <Button
                          size="sm"
                          variant="danger"
                          onClick={() => handleRemoveQueueItem(pseudoOp)}
                          disabled={removingItem === itemKey}
                          title="Remove from queue"
                        >
                          {removingItem === itemKey ? 'Removing...' : '✕'}
                        </Button>
                      </div>
                    );
                  })}
                </div>
              );
            }
            return null;
          })()}
        </div>
      )}

      {/* Empty State */}
      {!queuedState && (
        <div className="empty-state">
          <div className="empty-state-icon">📋</div>
          <h2>No Changes Queued</h2>
          <p>Make changes to extensions or tools, and they will automatically appear here.</p>
          <Button variant="secondary" onClick={() => window.location.href = '/extensions'}>
            Go to Extensions
          </Button>
        </div>
      )}

      {/* Confirmation Modals */}

      <ConfirmModal
        isOpen={showDeleteQueueConfirm}
        onClose={() => setShowDeleteQueueConfirm(false)}
        onConfirm={handleDeleteQueue}
        title="Clear Queue"
        message="Are you sure you want to clear the queue? This will remove all queued operations."
        confirmText="Clear"
      />

      <RestartModal
        isOpen={showRestartModal}
        onClose={() => setShowRestartModal(false)}
        onSuccess={() => window.location.reload()}
      />
    </div>
  );
}
