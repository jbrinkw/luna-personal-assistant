import React, { useState, useEffect, useRef } from 'react';
import { KeysAPI, ConfigAPI } from '../lib/api';
import { useConfig } from '../context/ConfigContext';
import Button from '../components/common/Button';
import Modal from '../components/common/Modal';
import StatusIndicator from '../components/common/StatusIndicator';
import LoadingSpinner from '../components/common/LoadingSpinner';
import { maskValue, validateKeyFormat } from '../lib/utils';

export default function KeyManager() {
  const { currentState } = useConfig();
  const [secrets, setSecrets] = useState({});
  const [requiredSecrets, setRequiredSecrets] = useState({});
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [editingKey, setEditingKey] = useState(null);
  const [editingValue, setEditingValue] = useState('');
  const [savedValue, setSavedValue] = useState('');
  const [showValue, setShowValue] = useState(false);
  const [showNewValue, setShowNewValue] = useState(false);
  const [newKeyName, setNewKeyName] = useState('');
  const [newKeyValue, setNewKeyValue] = useState('');
  const fileInputRef = useRef();

  useEffect(() => {
    loadSecrets();
  }, [currentState]);

  const loadSecrets = async () => {
    try {
      setLoading(true);
      
      // Load all secrets
      const allSecrets = await KeysAPI.list();
      setSecrets(allSecrets);

      // Load required secrets from extensions
      const required = {};
      const secretToExts = {};
      
      if (currentState?.extensions) {
        for (const [name, ext] of Object.entries(currentState.extensions)) {
          try {
            const extConfig = await ConfigAPI.getExtension(name);
            if (extConfig?.required_secrets) {
              extConfig.required_secrets.forEach(secret => {
                required[secret] = allSecrets[secret] || null;
                if (!secretToExts[secret]) {
                  secretToExts[secret] = [];
                }
                secretToExts[secret].push(name);
              });
            }
          } catch (error) {
            console.error(`Failed to load config for ${name}:`, error);
          }
        }
      }

      setRequiredSecrets({ secrets: required, mapping: secretToExts });
    } catch (error) {
      console.error('Failed to load secrets:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleEnvUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    try {
      setUploading(true);
      const result = await KeysAPI.uploadEnv(file);
      alert(`Updated ${result.updated_count} secrets`);
      await loadSecrets();
    } catch (error) {
      console.error('Failed to upload .env file:', error);
      alert('Failed to upload .env file: ' + error.message);
    } finally {
      setUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleEditClick = (key, value) => {
    setEditingKey(key);
    setSavedValue(value || '');
    setEditingValue(''); // Keep hidden initially
    setShowValue(false);
    setShowEditModal(true);
  };

  const handleSaveSecret = async () => {
    try {
      // Use saved value if editing value is empty (user didn't change it)
      const valueToSave = editingValue || savedValue;
      await KeysAPI.set(editingKey, valueToSave);
      alert('Secret updated successfully!');
      setShowEditModal(false);
      setSavedValue('');
      await loadSecrets();
    } catch (error) {
      console.error('Failed to save secret:', error);
      alert('Failed to save secret: ' + error.message);
    }
  };

  const handleDeleteSecret = async (key) => {
    if (!confirm(`Are you sure you want to delete the secret "${key}"?`)) {
      return;
    }

    try {
      await KeysAPI.delete(key);
      alert('Secret deleted successfully!');
      await loadSecrets();
    } catch (error) {
      console.error('Failed to delete secret:', error);
      alert('Failed to delete secret: ' + error.message);
    }
  };

  const handleAddSecret = async () => {
    if (!newKeyName || !newKeyValue) {
      alert('Please enter both key name and value');
      return;
    }

    if (!validateKeyFormat(newKeyName)) {
      alert('Key must be uppercase letters, numbers, and underscores only');
      return;
    }

    try {
      await KeysAPI.set(newKeyName, newKeyValue);
      alert('Secret added successfully!');
      setNewKeyName('');
      setNewKeyValue('');
      setShowNewValue(false);
      await loadSecrets();
    } catch (error) {
      console.error('Failed to add secret:', error);
      alert('Failed to add secret: ' + error.message);
    }
  };

  if (loading) {
    return (
      <div className="page-container">
        <LoadingSpinner message="Loading secrets..." />
      </div>
    );
  }

  const customSecrets = Object.keys(secrets).filter(
    key => !requiredSecrets.secrets?.[key] && requiredSecrets.secrets?.[key] !== null
  );

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1>Key Manager</h1>
          <p className="page-subtitle">Manage API keys and secrets</p>
        </div>
        <div>
          <input
            ref={fileInputRef}
            type="file"
            accept=".env"
            style={{ display: 'none' }}
            onChange={handleEnvUpload}
          />
          <Button 
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
          >
            {uploading ? 'Uploading...' : '📤 Upload .env File'}
          </Button>
        </div>
      </div>

      {/* Required Secrets */}
      {requiredSecrets.secrets && Object.keys(requiredSecrets.secrets).length > 0 && (
        <div className="secrets-section">
          <h2>Required by Extensions</h2>
          <div className="secrets-list">
            {Object.entries(requiredSecrets.secrets).map(([key, value]) => (
              <div key={key} className="secret-row">
                <div className="secret-info">
                  <div className="secret-key-wrapper">
                    <StatusIndicator status={value ? 'online' : 'offline'} />
                    <code className="secret-key">{key}</code>
                  </div>
                  <div className="secret-extensions">
                    Used by: {requiredSecrets.mapping[key]?.join(', ')}
                  </div>
                </div>
                
                <div className="secret-value">
                  {value ? (
                    <span className="masked-value">{maskValue(value)}</span>
                  ) : (
                    <span className="missing-value">(not set)</span>
                  )}
                </div>

                <div className="secret-actions">
                  <Button 
                    size="sm" 
                    variant="secondary"
                    onClick={() => handleEditClick(key, value)}
                  >
                    {value ? 'Edit' : 'Add'}
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Custom Secrets */}
      {customSecrets.length > 0 && (
        <div className="secrets-section">
          <h2>Custom Secrets</h2>
          <div className="secrets-list">
            {customSecrets.map(key => (
              <div key={key} className="secret-row">
                <div className="secret-info">
                  <div className="secret-key-wrapper">
                    <StatusIndicator status="online" />
                    <code className="secret-key">{key}</code>
                  </div>
                </div>
                
                <div className="secret-value">
                  <span className="masked-value">{maskValue(secrets[key])}</span>
                </div>

                <div className="secret-actions">
                  <Button 
                    size="sm" 
                    variant="secondary"
                    onClick={() => handleEditClick(key, secrets[key])}
                  >
                    Edit
                  </Button>
                  <Button 
                    size="sm" 
                    variant="danger"
                    onClick={() => handleDeleteSecret(key)}
                  >
                    Delete
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Add New Secret */}
      <div className="secrets-section">
        <h2>Add New Secret</h2>
        <div className="add-secret-form">
          <input
            type="text"
            className="secret-input"
            placeholder="KEY_NAME (uppercase, underscores)"
            value={newKeyName}
            onChange={(e) => setNewKeyName(e.target.value.toUpperCase())}
          />
          <div className="input-with-toggle">
            <input
              type={showNewValue ? 'text' : 'password'}
              className="secret-input"
              placeholder="Secret value"
              value={newKeyValue}
              onChange={(e) => setNewKeyValue(e.target.value)}
            />
            <button
              type="button"
              className="toggle-visibility-btn"
              onClick={() => setShowNewValue(!showNewValue)}
            >
              {showNewValue ? '👁️' : '👁️‍🗨️'}
            </button>
          </div>
          <Button onClick={handleAddSecret}>
            Add Secret
          </Button>
        </div>
      </div>

      {/* Edit Modal */}
      <Modal
        isOpen={showEditModal}
        onClose={() => setShowEditModal(false)}
        title={`${secrets[editingKey] ? 'Edit' : 'Add'} Secret`}
      >
        <div className="edit-secret-form">
          <label>
            <strong>Key:</strong> <code>{editingKey}</code>
          </label>
          
          <div className="input-with-toggle">
            <input
              type={showValue ? 'text' : 'password'}
              className="secret-input"
              value={showValue && !editingValue && savedValue ? savedValue : editingValue}
              onChange={(e) => setEditingValue(e.target.value)}
              placeholder={savedValue ? '••••••••••••' : 'Enter new secret value'}
              autoFocus
            />
            <button
              type="button"
              className="toggle-visibility-btn"
              onClick={() => setShowValue(!showValue)}
            >
              {showValue ? '👁️' : '👁️‍🗨️'}
            </button>
          </div>

          <div className="modal-actions">
            <Button variant="secondary" onClick={() => setShowEditModal(false)}>
              Cancel
            </Button>
            <Button onClick={handleSaveSecret}>
              Save
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
