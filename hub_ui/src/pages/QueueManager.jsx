import React, { useState } from 'react';
import { useConfig } from '../context/ConfigContext';
import Button from '../components/common/Button';
import { ConfirmModal } from '../components/common/Modal';
import RestartModal from '../components/common/RestartModal';
import LoadingSpinner from '../components/common/LoadingSpinner';

export default function QueueManager() {
  const { 
    originalState,
    pendingChanges, 
    queuedState, 
    saveToQueue, 
    revertChanges, 
    deleteQueue, 
    hasChanges, 
    loading 
  } = useConfig();
  
  const [showRevertConfirm, setShowRevertConfirm] = useState(false);
  const [showDeleteQueueConfirm, setShowDeleteQueueConfirm] = useState(false);
  const [showRestartModal, setShowRestartModal] = useState(false);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);

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

  const groupChangesByType = () => {
    const groups = {
      install: [],
      update: [],
      delete: [],
      config: [],
      tool_config: [],
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
          <h1>Queue Manager</h1>
          <p className="page-subtitle">Review and apply configuration changes</p>
        </div>
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
            {groupedChanges.install.length > 0 && (
              <div className="change-group">
                <h3 className="change-group-title">📦 Extensions to Install ({groupedChanges.install.length})</h3>
                {groupedChanges.install.map(change => (
                  <div key={change.target} className="change-item install">
                    <span className="change-icon">➕</span>
                    <span className="change-target">{change.target}</span>
                  </div>
                ))}
              </div>
            )}

            {groupedChanges.update.length > 0 && (
              <div className="change-group">
                <h3 className="change-group-title">🔄 Extensions to Update ({groupedChanges.update.length})</h3>
                {groupedChanges.update.map(change => (
                  <div key={change.target} className="change-item update">
                    <span className="change-icon">🔄</span>
                    <span className="change-target">{change.target}</span>
                  </div>
                ))}
              </div>
            )}

            {groupedChanges.delete.length > 0 && (
              <div className="change-group">
                <h3 className="change-group-title">🗑️ Extensions to Delete ({groupedChanges.delete.length})</h3>
                {groupedChanges.delete.map(change => (
                  <div key={change.target} className="change-item delete">
                    <span className="change-icon">❌</span>
                    <span className="change-target">{change.target}</span>
                  </div>
                ))}
              </div>
            )}

            {groupedChanges.config.length > 0 && (
              <div className="change-group">
                <h3 className="change-group-title">⚙️ Configuration Changes ({groupedChanges.config.length})</h3>
                {groupedChanges.config.map(change => (
                  <div key={change.target} className="change-item config">
                    <span className="change-icon">⚙️</span>
                    <span className="change-target">{change.target}</span>
                    {change.detail && <span className="change-detail"> ({change.detail})</span>}
                  </div>
                ))}
              </div>
            )}

            {groupedChanges.tool_config.length > 0 && (
              <div className="change-group">
                <h3 className="change-group-title">🛠️ Tool Configuration Changes ({groupedChanges.tool_config.length})</h3>
                {groupedChanges.tool_config.map(change => (
                  <div key={change.target} className="change-item tool-config">
                    <span className="change-icon">🛠️</span>
                    <span className="change-target">{change.target}</span>
                  </div>
                ))}
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
              {queuedState.operations.map((op, index) => (
                <div key={index} className="operation-item">
                  <span className="operation-type">{op.type.toUpperCase()}</span>
                  <span className="operation-target">{op.target}</span>
                  {op.source && <span className="operation-source">from {op.source}</span>}
                </div>
              ))}
            </div>
          )}

          {/* Show config changes that will be applied */}
          {queuedState.master_config && originalState && (() => {
            const configChanges = [];
            const queuedExts = queuedState.master_config.extensions || {};
            const originalExts = originalState.extensions || {};
            
            // Find enabled/disabled changes
            Object.keys(queuedExts).forEach(extName => {
              const queuedExt = queuedExts[extName];
              const originalExt = originalExts[extName];
              
              // Check if enabled status changed
              if (originalExt && queuedExt.enabled !== originalExt.enabled) {
                configChanges.push({
                  type: 'config',
                  target: extName,
                  detail: `${queuedExt.enabled ? 'Enable' : 'Disable'} extension`
                });
              }
            });
            
            if (configChanges.length > 0) {
              return (
                <div className="operations-list">
                  <h3>Configuration Changes:</h3>
                  {configChanges.map((change, index) => (
                    <div key={`config-${index}`} className="operation-item">
                      <span className="operation-type">CONFIG</span>
                      <span className="operation-target">{change.target}</span>
                      <span className="operation-source">{change.detail}</span>
                    </div>
                  ))}
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
