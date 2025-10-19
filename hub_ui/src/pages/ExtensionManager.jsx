import React, { useState, useRef } from 'react';
import { useConfig } from '../context/ConfigContext';
import { useServices } from '../context/ServicesContext';
import { ExtensionsAPI } from '../lib/api';
import ExtensionCard from '../components/features/ExtensionCard';
import Button from '../components/common/Button';
import LoadingSpinner from '../components/common/LoadingSpinner';

export default function ExtensionManager() {
  const { currentState, updateExtension, loading: configLoading } = useConfig();
  const { extensions, loading: servicesLoading } = useServices();
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState(null);
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
      const isUpdate = currentState?.extensions?.[extName];

      // Add to currentState
      updateExtension(extName, {
        enabled: true,
        source: `upload:${tempFilename}`,
        config: currentState?.extensions?.[extName]?.config || {},
      });

      // Show success message
      alert(`${isUpdate ? 'Updated' : 'Installed'} ${extName} - Save to queue to apply changes`);
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
        <div>
          <input
            ref={fileInputRef}
            type="file"
            accept=".zip,.tar.gz"
            style={{ display: 'none' }}
            onChange={handleFileSelect}
          />
          <Button onClick={handleUploadClick} disabled={uploading}>
            {uploading ? 'Uploading...' : '📤 Upload Extension'}
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
          <p>Upload an extension or browse the store to get started</p>
          <div className="empty-state-actions">
            <Button onClick={handleUploadClick}>Upload Extension</Button>
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
    </div>
  );
}
