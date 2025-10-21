import React, { useState } from 'react';
import { useConfig } from '../context/ConfigContext';
import Button from '../components/common/Button';
import { ConfirmModal } from '../components/common/Modal';
import RestartModal from '../components/common/RestartModal';
import LoadingSpinner from '../components/common/LoadingSpinner';

export default function UpdateManager() {
  const { 
    originalState,
    pendingChanges, 
    queuedState, 
    saveToQueue, 
    revertChanges, 
    deleteQueue, 
    hasChanges, 
    loading,
    updateExtension,
    deleteExtension,
    updateTool,
    addCoreUpdate,
    removeCoreUpdate,
    stageChangeToQueue,
    unstageQueueItem,
    checkForCoreUpdates,
    clearCoreUpdateInfo,
    coreUpdateInfo
  } = useConfig();
  
  const [showRevertConfirm, setShowRevertConfirm] = useState(false);
  const [showDeleteQueueConfirm, setShowDeleteQueueConfirm] = useState(false);
  const [showRestartModal, setShowRestartModal] = useState(false);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [activeChangeKey, setActiveChangeKey] = useState(null);
  const [coreCheckLoading, setCoreCheckLoading] = useState(false);
  const [coreCheckError, setCoreCheckError] = useState(null);
  const hasCoreUpdateData = coreUpdateInfo && !coreUpdateInfo.error;
  const coreStatusMessage = coreCheckError || coreUpdateInfo?.error || null;

  const handleSaveToQueue = async () => {
    try {
      setSaving(true);
      await saveToQueue();
    } catch (error) {
      console.error('Failed to save queue:', error);
      alert('Failed to save queue: ' + error.message);
    } finally {
      setSaving(false);
    }
  };

  const handleRevert = () => {
    revertChanges();
    setShowRevertConfirm(false);
  };

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

  const handleRemoveChange = (change) => {
    if (change.type === 'update_core') {
      removeCoreUpdate();
    } else if (change.type === 'install' || change.type === 'update') {
      const original = originalState?.extensions?.[change.target];
      if (original) {
        updateExtension(change.target, original);
      } else {
        deleteExtension(change.target);
      }
    } else if (change.type === 'delete') {
      const original = originalState?.extensions?.[change.target];
      if (original) {
        updateExtension(change.target, original);
      }
    } else if (change.type === 'config') {
      const original = originalState?.extensions?.[change.target];
      if (original) {
        updateExtension(change.target, { enabled: original.enabled });
      }
    } else if (change.type === 'tool_config') {
      const original = originalState?.tool_configs?.[change.target];
      if (original) {
        updateTool(change.target, original);
      } else {
        updateTool(change.target, null);
      }
    }
  };

  const getChangeKey = (change) => `${change.type}:${change.target || change.detail || ''}`;

  const handleStageChange = async (change) => {
    const key = `stage:${getChangeKey(change)}`;
    setActiveChangeKey(key);
    try {
      await stageChangeToQueue(change);
    } catch (error) {
      console.error('Failed to move change to saved queue:', error);
      alert('Failed to move change to saved queue: ' + (error.message || error));
    } finally {
      setActiveChangeKey(null);
    }
  };

  const handleUnstageChange = async (change) => {
    const key = `unstage:${getChangeKey(change)}`;
    setActiveChangeKey(key);
    try {
      await unstageQueueItem(change);
    } catch (error) {
      console.error('Failed to move queued change back to unsaved:', error);
      alert('Failed to move queued change back to unsaved: ' + (error.message || error));
    } finally {
      setActiveChangeKey(null);
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

  const handleReinstallCore = () => {
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
    addCoreUpdate(currentVersion);
  };

  const groupChangesByType = () => {
    const groups = {
      install: [],
      update: [],
      delete: [],
      config: [],
      tool_config: [],
      update_core: [],
    };

    pendingChanges.forEach(change => {
      if (groups[change.type]) {
        groups[change.type].push(change);
      }
    });

    return groups;
  };

  if (loading) {
    return (
      <div className="page-container">
        <LoadingSpinner message="Loading queue..." />
      </div>
    );
  }

  const groupedChanges = hasChanges ? groupChangesByType() : null;

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

      {/* Unsaved Changes Section */}
      {hasChanges && (
        <div className="queue-section">
          <div className="queue-section-header">
            <h2>Unsaved Changes</h2>
            <div className="queue-section-actions">
              <Button 
                variant="secondary" 
                onClick={() => setShowRevertConfirm(true)}
              >
                Revert All
              </Button>
              <Button 
                onClick={handleSaveToQueue}
                disabled={saving}
              >
                {saving ? 'Saving...' : 'Save to Queue'}
              </Button>
            </div>
          </div>

          <div className="changes-list">
            {groupedChanges.update_core.length > 0 && (
              <div className="change-group">
                <h3 className="change-group-title">🌙 Luna Core Update ({groupedChanges.update_core.length})</h3>
                {groupedChanges.update_core.map(change => {
                  const stageKey = `stage:${getChangeKey(change)}`;
                  return (
                    <div key={`core-update-${change.detail || 'pending'}`} className="change-item update-core">
                      <div className="change-item-content">
                        <span className="change-icon">🌙</span>
                        <span className="change-target">{change.target}</span>
                        {change.detail && <span className="change-detail"> → {change.detail}</span>}
                      </div>
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => handleStageChange(change)}
                        disabled={activeChangeKey === stageKey}
                        title="Move to saved queue"
                      >
                        {activeChangeKey === stageKey ? 'Moving...' : 'Queue'}
                      </Button>
                      <Button 
                        size="sm" 
                        variant="danger" 
                        onClick={() => handleRemoveChange(change)}
                        title="Remove from unsaved changes"
                      >
                        ✕
                      </Button>
                    </div>
                  );
                })}
              </div>
            )}

            {groupedChanges.install.length > 0 && (
              <div className="change-group">
                <h3 className="change-group-title">📦 Extensions to Install ({groupedChanges.install.length})</h3>
                {groupedChanges.install.map(change => {
                  const stageKey = `stage:${getChangeKey(change)}`;
                  return (
                    <div key={change.target} className="change-item install">
                      <div className="change-item-content">
                        <span className="change-icon">➕</span>
                        <span className="change-target">{change.target}</span>
                      </div>
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => handleStageChange(change)}
                        disabled={activeChangeKey === stageKey}
                        title="Move to saved queue"
                      >
                        {activeChangeKey === stageKey ? 'Moving...' : 'Queue'}
                      </Button>
                      <Button 
                        size="sm" 
                        variant="danger" 
                        onClick={() => handleRemoveChange(change)}
                        title="Remove from unsaved changes"
                      >
                        ✕
                      </Button>
                    </div>
                  );
                })}
              </div>
            )}

            {groupedChanges.update.length > 0 && (
              <div className="change-group">
                <h3 className="change-group-title">🔄 Extensions to Update ({groupedChanges.update.length})</h3>
                {groupedChanges.update.map(change => {
                  const stageKey = `stage:${getChangeKey(change)}`;
                  return (
                    <div key={change.target} className="change-item update">
                      <div className="change-item-content">
                        <span className="change-icon">🔄</span>
                        <span className="change-target">{change.target}</span>
                      </div>
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => handleStageChange(change)}
                        disabled={activeChangeKey === stageKey}
                        title="Move to saved queue"
                      >
                        {activeChangeKey === stageKey ? 'Moving...' : 'Queue'}
                      </Button>
                      <Button 
                        size="sm" 
                        variant="danger" 
                        onClick={() => handleRemoveChange(change)}
                        title="Remove from unsaved changes"
                      >
                        ✕
                      </Button>
                    </div>
                  );
                })}
              </div>
            )}

            {groupedChanges.delete.length > 0 && (
              <div className="change-group">
                <h3 className="change-group-title">🗑️ Extensions to Delete ({groupedChanges.delete.length})</h3>
                {groupedChanges.delete.map(change => {
                  const stageKey = `stage:${getChangeKey(change)}`;
                  return (
                    <div key={change.target} className="change-item delete">
                      <div className="change-item-content">
                        <span className="change-icon">❌</span>
                        <span className="change-target">{change.target}</span>
                      </div>
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => handleStageChange(change)}
                        disabled={activeChangeKey === stageKey}
                        title="Move to saved queue"
                      >
                        {activeChangeKey === stageKey ? 'Moving...' : 'Queue'}
                      </Button>
                      <Button 
                        size="sm" 
                        variant="danger" 
                        onClick={() => handleRemoveChange(change)}
                        title="Remove from unsaved changes"
                      >
                        ✕
                      </Button>
                    </div>
                  );
                })}
              </div>
            )}

            {groupedChanges.config.length > 0 && (
              <div className="change-group">
                <h3 className="change-group-title">⚙️ Configuration Changes ({groupedChanges.config.length})</h3>
                {groupedChanges.config.map(change => {
                  const stageKey = `stage:${getChangeKey(change)}`;
                  return (
                    <div key={change.target} className="change-item config">
                      <div className="change-item-content">
                        <span className="change-icon">⚙️</span>
                        <span className="change-target">{change.target}</span>
                        {change.detail && <span className="change-detail"> ({change.detail})</span>}
                      </div>
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => handleStageChange(change)}
                        disabled={activeChangeKey === stageKey}
                        title="Move to saved queue"
                      >
                        {activeChangeKey === stageKey ? 'Moving...' : 'Queue'}
                      </Button>
                      <Button 
                        size="sm" 
                        variant="danger" 
                        onClick={() => handleRemoveChange(change)}
                        title="Remove from unsaved changes"
                      >
                        ✕
                      </Button>
                    </div>
                  );
                })}
              </div>
            )}

            {groupedChanges.tool_config.length > 0 && (
              <div className="change-group">
                <h3 className="change-group-title">🛠️ Tool Configuration Changes ({groupedChanges.tool_config.length})</h3>
                {groupedChanges.tool_config.map(change => {
                  const stageKey = `stage:${getChangeKey(change)}`;
                  return (
                    <div key={change.target} className="change-item tool-config">
                      <div className="change-item-content">
                        <span className="change-icon">🛠️</span>
                        <span className="change-target">{change.target}</span>
                      </div>
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => handleStageChange(change)}
                        disabled={activeChangeKey === stageKey}
                        title="Move to saved queue"
                      >
                        {activeChangeKey === stageKey ? 'Moving...' : 'Queue'}
                      </Button>
                      <Button 
                        size="sm" 
                        variant="danger" 
                        onClick={() => handleRemoveChange(change)}
                        title="Remove from unsaved changes"
                      >
                        ✕
                      </Button>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Saved Queue Section */}
      {queuedState && (
        <div className="queue-section">
          <div className="queue-section-header">
            <h2>Saved Queue</h2>
            <div className="queue-section-actions">
              <Button 
                variant="danger" 
                onClick={() => setShowDeleteQueueConfirm(true)}
                disabled={deleting}
              >
                {deleting ? 'Deleting...' : 'Delete Queue'}
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
                const change = op.type === 'update_core'
                  ? { type: 'update_core', target: 'Luna Core', detail: op.target_version }
                  : { type: op.type, target: op.target, detail: op.source || op.target_version };
                const unstageKey = `unstage:${getChangeKey(change)}`;
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
                      variant="secondary"
                      onClick={() => handleUnstageChange(change)}
                      disabled={activeChangeKey === unstageKey}
                      title="Move back to unsaved changes"
                    >
                      {activeChangeKey === unstageKey ? 'Moving...' : 'Unqueue'}
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
                    const unstageKey = `unstage:${getChangeKey(change)}`;
                    return (
                      <div key={`config-${index}`} className="operation-item">
                        <span className="operation-type">CONFIG</span>
                        <span className="operation-target">{change.target}</span>
                        <span className="operation-source">{change.detail}</span>
                        <Button
                          size="sm"
                          variant="secondary"
                          onClick={() => handleUnstageChange(change)}
                          disabled={activeChangeKey === unstageKey}
                          title="Move back to unsaved changes"
                        >
                          {activeChangeKey === unstageKey ? 'Moving...' : 'Unqueue'}
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
      {!hasChanges && !queuedState && (
        <div className="empty-state">
          <div className="empty-state-icon">📋</div>
          <h2>No Changes Pending</h2>
          <p>Make changes to extensions or tools, then save them to the queue.</p>
          <Button variant="secondary" onClick={() => window.location.href = '/extensions'}>
            Go to Extensions
          </Button>
        </div>
      )}

      {/* Confirmation Modals */}
      <ConfirmModal
        isOpen={showRevertConfirm}
        onClose={() => setShowRevertConfirm(false)}
        onConfirm={handleRevert}
        title="Revert Changes"
        message="Are you sure you want to revert all unsaved changes? This cannot be undone."
        confirmText="Revert"
      />

      <ConfirmModal
        isOpen={showDeleteQueueConfirm}
        onClose={() => setShowDeleteQueueConfirm(false)}
        onConfirm={handleDeleteQueue}
        title="Delete Queue"
        message="Are you sure you want to delete the saved queue? This will remove all queued operations."
        confirmText="Delete"
      />

      <RestartModal
        isOpen={showRestartModal}
        onClose={() => setShowRestartModal(false)}
        onSuccess={() => window.location.reload()}
      />
    </div>
  );
}
