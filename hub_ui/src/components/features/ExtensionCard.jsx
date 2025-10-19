import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useConfig } from '../../context/ConfigContext';
import Button from '../common/Button';
import StatusIndicator from '../common/StatusIndicator';
import { ConfirmModal } from '../common/Modal';

export default function ExtensionCard({ extension, status }) {
  const navigate = useNavigate();
  const { currentState, updateExtension, deleteExtension } = useConfig();
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  const extConfig = currentState?.extensions?.[extension.name] || {};
  const isEnabled = extConfig.enabled !== false;

  const handleToggle = () => {
    updateExtension(extension.name, {
      ...extConfig,
      enabled: !isEnabled,
    });
  };

  const handleDelete = () => {
    deleteExtension(extension.name);
    setShowDeleteConfirm(false);
  };

  return (
    <>
      <div className="extension-card">
        <div className="extension-card-header">
          <div className="extension-card-title">
            <h3>{extension.name}</h3>
            {extension.version && (
              <span className="version-tag">v{extension.version}</span>
            )}
          </div>
          <label className="toggle-switch">
            <input 
              type="checkbox" 
              checked={isEnabled} 
              onChange={handleToggle}
            />
            <span className="toggle-slider"></span>
          </label>
        </div>

        <div className="extension-card-body">
          <div className="extension-status">
            <StatusIndicator status={status?.ui?.status || 'offline'} />
            <span>{status?.ui?.status || 'stopped'}</span>
          </div>

          <div className="extension-stats">
            <div className="stat">
              <span className="stat-icon">🛠️</span>
              <span>{extension.tool_count || 0} tools</span>
            </div>
            <div className="stat">
              <span className="stat-icon">⚙️</span>
              <span>{extension.services?.length || 0} services</span>
            </div>
          </div>
        </div>

        <div className="extension-card-actions">
          <Button 
            variant="secondary" 
            onClick={() => navigate(`/extensions/${extension.name}`)}
          >
            Details
          </Button>
          <Button 
            variant="danger" 
            onClick={() => setShowDeleteConfirm(true)}
          >
            Delete
          </Button>
        </div>
      </div>

      <ConfirmModal
        isOpen={showDeleteConfirm}
        onClose={() => setShowDeleteConfirm(false)}
        onConfirm={handleDelete}
        title="Delete Extension"
        message={`Are you sure you want to delete "${extension.name}"? This will be queued and applied on restart.`}
        confirmText="Delete"
      />
    </>
  );
}



