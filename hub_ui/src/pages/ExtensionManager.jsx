import React, { useState, useRef } from 'react';
import { useConfig } from '../context/ConfigContext';
import { useServices } from '../context/ServicesContext';
import { ExtensionsAPI } from '../lib/api';
import ExtensionCard from '../components/features/ExtensionCard';
import Button from '../components/common/Button';
import LoadingSpinner from '../components/common/LoadingSpinner';

export default function ExtensionManager() {
  const { queuedState, originalState, updateExtension, loading: configLoading } = useConfig();
  const { extensions, loading: servicesLoading } = useServices();
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState(null);
  const [showGitModal, setShowGitModal] = useState(false);
  const [gitUrl, setGitUrl] = useState('');
  const [extensionName, setExtensionName] = useState('');
  const [gitError, setGitError] = useState(null);
  const fileInputRef = useRef();

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileSelect = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    // Validate file type
    if (!file.name.endsWith('.zip') && !file.name.endsWith('.tar.gz')) {
      setUploadError('Please upload a .zip or .tar.gz file');
      return;
    }

    setUploading(true);
    setUploadError(null);

    try {
      const result = await ExtensionsAPI.upload(file);
      const tempFilename = result.temp_filename;

      // Extract extension name from original filename
      const extName = file.name.replace(/\.(zip|tar\.gz)$/i, '');

      // Check if this is an update (extension already exists) or install
      const currentConfig = queuedState?.master_config || originalState;
      const isUpdate = currentConfig?.extensions?.[extName];

      // Add to queue
      await updateExtension(extName, {
        enabled: true,
        source: `upload:${tempFilename}`,
        config: currentConfig?.extensions?.[extName]?.config || {},
      });
    } catch (error) {
      console.error('Upload failed:', error);
      setUploadError(error.message || 'Upload failed');
    } finally {
      setUploading(false);
      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleGitInstall = async () => {
    setGitError(null);
    
    // Validate inputs
    if (!gitUrl.trim()) {
      setGitError('Please enter a GitHub URL');
      return;
    }
    
    if (!extensionName.trim()) {
      setGitError('Please enter an extension name');
      return;
    }

    // Parse Git URL to create source string
    // Expected formats:
    // - user/repo -> github:user/repo
    // - user/repo:path/to/subfolder -> github:user/repo:path/to/subfolder
    // - https://github.com/user/repo -> github:user/repo
    // - github.com/user/repo -> github:user/repo
    
    let source = gitUrl.trim();
    
    // Remove https:// or http:// prefix
    source = source.replace(/^https?:\/\//, '');
    
    // Remove github.com/ prefix if present
    source = source.replace(/^github\.com\//, '');
    
    // Add github: prefix if not already there
    if (!source.startsWith('github:')) {
      source = `github:${source}`;
    }

    const extName = extensionName.trim();

    // Add to queue
    const currentConfig = queuedState?.master_config || originalState;
    await updateExtension(extName, {
      enabled: true,
      source,
      config: currentConfig?.extensions?.[extName]?.config || {},
    });

    // Close modal and reset
    setShowGitModal(false);
    setGitUrl('');
    setExtensionName('');
    setGitError(null);
  };

  if (configLoading || servicesLoading) {
    return (
      <div className="page-container">
        <LoadingSpinner message="Loading extensions..." />
      </div>
    );
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1>Extension Manager</h1>
          <p className="page-subtitle">Manage your Luna extensions</p>
        </div>
        <div className="page-header-actions">
          <input
            ref={fileInputRef}
            type="file"
            accept=".zip,.tar.gz"
            style={{ display: 'none' }}
            onChange={handleFileSelect}
          />
          <Button onClick={handleUploadClick} disabled={uploading}>
            {uploading ? 'Uploading...' : '📤 Install by Zip'}
          </Button>
          <Button onClick={() => setShowGitModal(true)} variant="secondary">
            🔗 Install by Git
          </Button>
        </div>
      </div>

      {uploadError && (
        <div className="error-message">
          {uploadError}
        </div>
      )}

      {extensions.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">📦</div>
          <h2>No Extensions Installed</h2>
          <p>Install an extension from zip, git, or browse the store to get started</p>
          <div className="empty-state-actions">
            <Button onClick={handleUploadClick}>📤 Install by Zip</Button>
            <Button onClick={() => setShowGitModal(true)}>🔗 Install by Git</Button>
            <Button variant="secondary" onClick={() => window.location.href = '/store'}>
              Browse Store
            </Button>
          </div>
        </div>
      ) : (
        <div className="extensions-grid">
          {extensions.map(ext => (
            <ExtensionCard
              key={ext.name}
              extension={ext}
              status={ext}
            />
          ))}
        </div>
      )}

      {/* Git Install Modal */}
      {showGitModal && (
        <div className="modal-overlay" onClick={() => setShowGitModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Install Extension from Git</h2>
              <button 
                className="modal-close" 
                onClick={() => setShowGitModal(false)}
              >
                ×
              </button>
            </div>
            
            <div className="modal-body">
              {gitError && (
                <div className="error-message mb-md">
                  {gitError}
                </div>
              )}
              
              <div className="form-group">
                <label htmlFor="gitUrl">GitHub URL</label>
                <input
                  id="gitUrl"
                  type="text"
                  className="form-input"
                  placeholder="user/repo or user/repo:path/to/subfolder"
                  value={gitUrl}
                  onChange={(e) => setGitUrl(e.target.value)}
                  onKeyPress={(e) => {
                    if (e.key === 'Enter') handleGitInstall();
                  }}
                />
                <small className="form-help">
                  Examples: <code>jbrinkw/my-extension</code> or <code>jbrinkw/monorepo:extensions/my-ext</code>
                </small>
              </div>
              
              <div className="form-group">
                <label htmlFor="extensionName">Extension Name</label>
                <input
                  id="extensionName"
                  type="text"
                  className="form-input"
                  placeholder="my_extension"
                  value={extensionName}
                  onChange={(e) => setExtensionName(e.target.value)}
                  onKeyPress={(e) => {
                    if (e.key === 'Enter') handleGitInstall();
                  }}
                />
                <small className="form-help">
                  The name to install this extension as (use lowercase and underscores)
                </small>
              </div>
            </div>
            
            <div className="modal-footer">
              <Button variant="secondary" onClick={() => setShowGitModal(false)}>
                Cancel
              </Button>
              <Button onClick={handleGitInstall}>
                Install
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
