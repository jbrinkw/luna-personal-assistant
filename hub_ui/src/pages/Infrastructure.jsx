import { useState, useEffect, useRef } from 'react';
import {
  getInstalledServices,
  getServiceDetails,
  startService,
  stopService,
  restartService,
  enableService,
  disableService,
  uninstallService,
  getServiceLogs,
  uploadService,
  installService,
} from '../lib/externalServicesApi';
import './Infrastructure.css';

export default function Infrastructure() {
  const [services, setServices] = useState({});
  const [serviceConfigs, setServiceConfigs] = useState({});
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState({});
  const [error, setError] = useState(null);
  const [logsModal, setLogsModal] = useState(null);
  const [deleteModal, setDeleteModal] = useState(null);
  const [expandedConfig, setExpandedConfig] = useState({});
  const [uploadModal, setUploadModal] = useState(null);
  const [uploadError, setUploadError] = useState(null);
  const [installModal, setInstallModal] = useState(null);
  const fileInputRef = useRef(null);

  // Fetch installed services
  const fetchServices = async () => {
    try {
      const data = await getInstalledServices();
      setServices(data);
      setError(null);
    } catch (err) {
      setError(err.message);
      console.error('Failed to fetch installed services:', err);
    } finally {
      setLoading(false);
    }
  };

  // Fetch service config when expanding
  const fetchServiceConfig = async (serviceName) => {
    if (serviceConfigs[serviceName]) return; // Already loaded
    
    try {
      const details = await getServiceDetails(serviceName);
      setServiceConfigs(prev => ({
        ...prev,
        [serviceName]: details.config || {}
      }));
    } catch (err) {
      console.error(`Failed to fetch config for ${serviceName}:`, err);
      setServiceConfigs(prev => ({
        ...prev,
        [serviceName]: { error: 'Failed to load configuration' }
      }));
    }
  };

  useEffect(() => {
    fetchServices();
    
    // Poll for status updates every 10 seconds
    const interval = setInterval(fetchServices, 10000);
    return () => clearInterval(interval);
  }, []);

  // Handle service start
  const handleStart = async (serviceName) => {
    setActionLoading(prev => ({ ...prev, [serviceName]: 'starting' }));
    try {
      await startService(serviceName);
      await fetchServices();
      showToast(`${serviceName} started successfully`, 'success');
    } catch (err) {
      showToast(`Failed to start ${serviceName}: ${err.message}`, 'error');
    } finally {
      setActionLoading(prev => ({ ...prev, [serviceName]: null }));
    }
  };

  // Handle service stop
  const handleStop = async (serviceName) => {
    setActionLoading(prev => ({ ...prev, [serviceName]: 'stopping' }));
    try {
      await stopService(serviceName);
      await fetchServices();
      showToast(`${serviceName} stopped successfully`, 'success');
    } catch (err) {
      showToast(`Failed to stop ${serviceName}: ${err.message}`, 'error');
    } finally {
      setActionLoading(prev => ({ ...prev, [serviceName]: null }));
    }
  };

  // Handle service restart
  const handleRestart = async (serviceName) => {
    setActionLoading(prev => ({ ...prev, [serviceName]: 'restarting' }));
    try {
      await restartService(serviceName);
      await fetchServices();
      showToast(`${serviceName} restarted successfully`, 'success');
    } catch (err) {
      showToast(`Failed to restart ${serviceName}: ${err.message}`, 'error');
    } finally {
      setActionLoading(prev => ({ ...prev, [serviceName]: null }));
    }
  };

  // Handle enable/disable toggle
  const handleToggleEnabled = async (serviceName, currentlyEnabled) => {
    setActionLoading(prev => ({ ...prev, [serviceName]: 'toggling' }));
    try {
      if (currentlyEnabled) {
        await disableService(serviceName);
        showToast(`${serviceName} auto-start disabled`, 'success');
      } else {
        await enableService(serviceName);
        showToast(`${serviceName} auto-start enabled`, 'success');
      }
      await fetchServices();
    } catch (err) {
      showToast(`Failed to toggle ${serviceName}: ${err.message}`, 'error');
    } finally {
      setActionLoading(prev => ({ ...prev, [serviceName]: null }));
    }
  };

  // Handle delete
  const confirmDelete = async () => {
    if (!deleteModal) return;
    
    const { serviceName, removeData } = deleteModal;
    setActionLoading(prev => ({ ...prev, [serviceName]: 'deleting' }));
    setDeleteModal(null);
    
    try {
      await uninstallService(serviceName, removeData);
      await fetchServices();
      showToast(`${serviceName} deleted successfully`, 'success');
    } catch (err) {
      showToast(`Failed to delete ${serviceName}: ${err.message}`, 'error');
    } finally {
      setActionLoading(prev => ({ ...prev, [serviceName]: null }));
    }
  };

  // Handle view logs
  const handleViewLogs = async (serviceName) => {
    try {
      const { logs, path } = await getServiceLogs(serviceName, 100);
      setLogsModal({ serviceName, logs, path });
    } catch (err) {
      showToast(`Failed to fetch logs: ${err.message}`, 'error');
    }
  };

  // Toggle config expansion
  const toggleConfig = (serviceName) => {
    setExpandedConfig(prev => {
      const newState = { ...prev, [serviceName]: !prev[serviceName] };
      if (newState[serviceName]) {
        fetchServiceConfig(serviceName);
      }
      return newState;
    });
  };

  // Simple toast notification
  const showToast = (message, type = 'info') => {
    // Implement toast notification (or use existing toast system)
    console.log(`[${type}] ${message}`);
    alert(message); // Replace with proper toast
  };

  // Get status indicator
  const getStatusIndicator = (status) => {
    switch (status) {
      case 'running':
        return <span className="status-indicator running">● Running</span>;
      case 'stopped':
        return <span className="status-indicator stopped">○ Stopped</span>;
      case 'unhealthy':
        return <span className="status-indicator failed">⚠ Unhealthy</span>;
      default:
        return <span className="status-indicator unknown">? Unknown</span>;
    }
  };

  // Mask sensitive fields
  const maskValue = (key, value) => {
    if (key.toLowerCase().includes('password') || 
        key.toLowerCase().includes('secret') || 
        key.toLowerCase().includes('token') ||
        key.toLowerCase().includes('key')) {
      return '••••••••••••';
    }
    return typeof value === 'object' ? JSON.stringify(value) : String(value);
  };

  // Copy config to clipboard
  const copyToClipboard = async (config) => {
    const text = Object.entries(config)
      .filter(([key]) => !key.includes('_at') && !key.includes('_path'))
      .map(([key, value]) => `${key.toUpperCase()}=${value}`)
      .join('\n');
    
    try {
      await navigator.clipboard.writeText(text);
      showToast('Configuration copied to clipboard', 'success');
    } catch (err) {
      showToast('Failed to copy to clipboard', 'error');
    }
  };

  // Handle upload button click
  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  // Handle file selection
  const handleFileSelect = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    // Reset file input
    event.target.value = '';

    try {
      // Read file as text
      const text = await file.text();
      
      // Parse JSON
      const serviceDefinition = JSON.parse(text);
      
      // Basic validation
      if (!serviceDefinition.name) {
        setUploadError('Invalid service definition: missing "name" field');
        setUploadModal({ serviceDefinition: null, fileName: file.name });
        return;
      }
      
      if (!serviceDefinition.display_name) {
        setUploadError('Invalid service definition: missing "display_name" field');
        setUploadModal({ serviceDefinition: null, fileName: file.name });
        return;
      }

      // Show preview modal
      setUploadError(null);
      setUploadModal({ serviceDefinition, fileName: file.name });
    } catch (err) {
      setUploadError(`Failed to parse JSON: ${err.message}`);
      setUploadModal({ serviceDefinition: null, fileName: file.name });
    }
  };

  // Handle upload confirmation - upload AND install
  const handleUploadConfirm = async () => {
    if (!uploadModal?.serviceDefinition) return;

    setActionLoading(prev => ({ ...prev, upload: true }));
    
    try {
      // Step 1: Upload the service definition
      const uploadResult = await uploadService(uploadModal.serviceDefinition);
      const serviceName = uploadResult.name;
      
      // Close upload modal
      setUploadModal(null);
      setUploadError(null);
      
      // Step 2: Check if service has config form fields
      const serviceDetails = await getServiceDetails(serviceName);
      const configForm = serviceDetails.form;
      
      if (configForm && configForm.fields && configForm.fields.length > 0) {
        // Has config form - show install modal
        setInstallModal({ serviceName, serviceDetails });
      } else {
        // No config form - install with empty config
        await installService(serviceName, {});
        await fetchServices();
        showToast(`Service "${serviceName}" installed successfully`, 'success');
      }
    } catch (err) {
      setUploadError(err.message);
    } finally {
      setActionLoading(prev => ({ ...prev, upload: false }));
    }
  };

  // Handle install after upload
  const handleInstallAfterUpload = async (serviceName, config) => {
    setActionLoading(prev => ({ ...prev, [serviceName]: 'installing' }));
    
    try {
      await installService(serviceName, config);
      setInstallModal(null);
      await fetchServices();
      showToast(`Service "${serviceName}" installed successfully`, 'success');
    } catch (err) {
      showToast(`Failed to install ${serviceName}: ${err.message}`, 'error');
    } finally {
      setActionLoading(prev => ({ ...prev, [serviceName]: null }));
    }
  };

  if (loading) {
    return (
      <div className="infrastructure-page">
        <div className="infrastructure-container">
          <h1 className="page-title">🏗️ Infrastructure</h1>
          <div className="loading-state">
            <div className="spinner"></div>
            <p>Loading services...</p>
          </div>
        </div>
      </div>
    );
  }

  const serviceNames = Object.keys(services);
  const hasServices = serviceNames.length > 0;

  return (
    <div className="infrastructure-page">
      <div className="infrastructure-container">
        <h1 className="page-title">🏗️ Infrastructure</h1>
        <p className="page-subtitle">Manage external services like databases, message queues, and other infrastructure components</p>

        {error && (
          <div className="error-banner">
            <span className="error-icon">⚠️</span>
            <span>{error}</span>
          </div>
        )}

        <div className="services-section">
          <div className="section-header">
            <div className="section-header-left">
              <h2 className="section-title">External Services</h2>
              {hasServices && (
                <span className="service-count">{serviceNames.length} service{serviceNames.length !== 1 ? 's' : ''} installed</span>
              )}
            </div>
            <button
              onClick={handleUploadClick}
              className="btn btn-primary upload-service-btn"
              disabled={loading}
            >
              + Upload & Install Service
            </button>
          </div>
          
          {/* Hidden file input */}
          <input
            ref={fileInputRef}
            type="file"
            accept=".json"
            onChange={handleFileSelect}
            style={{ display: 'none' }}
          />
          
          {!hasServices ? (
            <div className="empty-state">
              <div className="empty-state-icon">📦</div>
              <h3 className="empty-state-title">No External Services Installed</h3>
              <p className="empty-state-description">
                External services are infrastructure components that run alongside Luna, such as databases, message queues, and caching systems.
              </p>
              <a href="/store" className="empty-state-button">
                Browse Addon Store
              </a>
            </div>
          ) : (
            <div className="services-grid">
              {serviceNames.map((serviceName) => {
                const service = services[serviceName];
                const isLoading = actionLoading[serviceName];
                const isExpanded = expandedConfig[serviceName];
                const config = serviceConfigs[serviceName];
                const uiMeta = service.ui;
                const uiHref = uiMeta?.path_with_slash || uiMeta?.path;
                const uiOpensNewTab = uiMeta?.open_mode === 'new_tab';

                return (
                  <div key={serviceName} className="service-card">
                    {/* Card Header */}
                    <div className="service-card-header">
                      <div className="service-info">
                        <h3 className="service-name">{serviceName.replace(/_/g, ' ')}</h3>
                        <div className="service-status">
                          {getStatusIndicator(service.status)}
                        </div>
                      </div>
                      {service.enabled && (
                        <div className="service-badge">
                          <span className="badge-auto-start">⚡ Auto-start</span>
                        </div>
                      )}
                    </div>

                    {/* Timestamps */}
                    {service.installed_at && (
                      <div className="service-meta">
                        <span className="meta-label">Installed:</span>
                        <span className="meta-value">
                          {new Date(service.installed_at).toLocaleDateString()}
                        </span>
                      </div>
                    )}
                    {uiMeta?.path && (
                      <div className="service-meta">
                        <span className="meta-label">UI Path:</span>
                        <span className="meta-value"><code>{uiMeta.path}</code></span>
                      </div>
                    )}

                    {/* Enable/Disable Toggle */}
                    <div className="service-toggle">
                      <label className="toggle-label">
                        <input
                          type="checkbox"
                          checked={service.enabled || false}
                          onChange={() => handleToggleEnabled(serviceName, service.enabled)}
                          disabled={!!isLoading}
                          className="toggle-checkbox"
                        />
                        <span className="toggle-text">Enable auto-start on boot</span>
                      </label>
                    </div>

                    {/* Control Buttons */}
                    <div className="service-actions">
                      {service.status !== 'running' && (
                        <button
                          onClick={() => handleStart(serviceName)}
                          disabled={!!isLoading}
                          className="btn btn-success"
                        >
                          {isLoading === 'starting' ? '⟳ Starting...' : '▶ Start'}
                        </button>
                      )}
                      
                      {service.status === 'running' && (
                        <>
                          <button
                            onClick={() => handleStop(serviceName)}
                            disabled={!!isLoading}
                            className="btn btn-danger"
                          >
                            {isLoading === 'stopping' ? '⟳ Stopping...' : '⏹ Stop'}
                          </button>
                          <button
                            onClick={() => handleRestart(serviceName)}
                            disabled={!!isLoading}
                            className="btn btn-primary"
                          >
                            {isLoading === 'restarting' ? '⟳ Restarting...' : '↻ Restart'}
                          </button>
                        </>
                      )}
                      
                      <button
                        onClick={() => handleViewLogs(serviceName)}
                        disabled={!!isLoading}
                        className="btn btn-secondary"
                      >
                        📄 Logs
                      </button>

                      {uiHref && (
                        <a
                          href={uiHref}
                          className="btn btn-primary"
                          target={uiOpensNewTab ? '_blank' : '_self'}
                          rel={uiOpensNewTab ? 'noreferrer noopener' : undefined}
                        >
                          🌐 Open UI{uiOpensNewTab ? ' ↗' : ''}
                        </a>
                      )}
                      
                      <button
                        onClick={() => setDeleteModal({ serviceName, removeData: true })}
                        disabled={!!isLoading}
                        className="btn btn-danger-outline"
                      >
                        {isLoading === 'deleting' ? '⟳ Deleting...' : '🗑️ Delete'}
                      </button>
                    </div>

                    {/* Configuration Section */}
                    <div className="config-section">
                      <button
                        onClick={() => toggleConfig(serviceName)}
                        className="config-toggle-btn"
                      >
                        <span className="config-toggle-icon">{isExpanded ? '▼' : '▶'}</span>
                        Configuration
                      </button>
                      
                      {isExpanded && (
                        <div className="config-content">
                          {!config ? (
                            <div className="config-loading">Loading configuration...</div>
                          ) : config.error ? (
                            <div className="config-error">{config.error}</div>
                          ) : (
                            <>
                              <div className="config-table">
                                {Object.entries(config)
                                  .filter(([key]) => !key.includes('_at') && !key.includes('_path'))
                                  .map(([key, value]) => (
                                    <div key={key} className="config-row">
                                      <div className="config-key">{key}:</div>
                                      <div className="config-value">{maskValue(key, value)}</div>
                                    </div>
                                  ))
                                }
                              </div>
                              <div className="config-help">
                                💡 Luna already writes these values into <code>.env</code>; copy them only if another system needs them.
                              </div>
                              <button
                                onClick={() => copyToClipboard(config)}
                                className="btn btn-secondary btn-sm"
                              >
                                📋 Copy as ENV vars
                              </button>
                            </>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Logs Modal */}
        {logsModal && (
          <div className="modal-overlay" onClick={() => setLogsModal(null)}>
            <div className="modal-content logs-modal" onClick={(e) => e.stopPropagation()}>
              <div className="modal-header">
                <h2 className="modal-title">
                  📄 Logs: {logsModal.serviceName}
                </h2>
                <button
                  onClick={() => setLogsModal(null)}
                  className="modal-close-btn"
                >
                  ×
                </button>
              </div>
              
              <div className="log-file-path">
                📁 {logsModal.path}
              </div>
              
              <div className="logs-container">
                <pre className="logs-content">{logsModal.logs || 'No logs available'}</pre>
              </div>
              
              <div className="modal-footer">
                <button
                  onClick={async () => {
                    try {
                      await navigator.clipboard.writeText(logsModal.logs);
                      showToast('Logs copied to clipboard', 'success');
                    } catch (err) {
                      showToast('Failed to copy logs', 'error');
                    }
                  }}
                  className="btn btn-secondary"
                >
                  📋 Copy Logs
                </button>
                <button
                  onClick={() => setLogsModal(null)}
                  className="btn btn-primary"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Delete Confirmation Modal */}
        {deleteModal && (
          <div className="modal-overlay" onClick={() => setDeleteModal(null)}>
            <div className="modal-content delete-modal" onClick={(e) => e.stopPropagation()}>
              <div className="modal-header">
                <h2 className="modal-title">
                  🗑️ Delete Service
                </h2>
                <button
                  onClick={() => setDeleteModal(null)}
                  className="modal-close-btn"
                >
                  ×
                </button>
              </div>
              
              <div className="modal-body">
                <p className="delete-warning">
                  Are you sure you want to delete <strong>{deleteModal.serviceName}</strong>?
                </p>
                <p className="delete-description">
                  This will uninstall the service and stop any running processes.
                </p>
                
                <label className="delete-checkbox-label">
                  <input
                    type="checkbox"
                    checked={deleteModal.removeData}
                    onChange={(e) => setDeleteModal({ ...deleteModal, removeData: e.target.checked })}
                    className="delete-checkbox"
                  />
                  <span>Also remove data and configuration files</span>
                </label>
              </div>
              
              <div className="modal-footer">
                <button
                  onClick={() => setDeleteModal(null)}
                  className="btn btn-secondary"
                >
                  Cancel
                </button>
                <button
                  onClick={confirmDelete}
                  className="btn btn-danger"
                >
                  Delete Service
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Upload Service Modal */}
        {uploadModal && (
          <div className="modal-overlay" onClick={() => setUploadModal(null)}>
            <div className="modal-content upload-modal" onClick={(e) => e.stopPropagation()}>
              <div className="modal-header">
                <h2 className="modal-title">
                  📤 Upload & Install Service
                </h2>
                <button
                  onClick={() => setUploadModal(null)}
                  className="modal-close-btn"
                >
                  ×
                </button>
              </div>
              
              <div className="modal-body">
                <p className="upload-file-name">
                  File: <strong>{uploadModal.fileName}</strong>
                </p>
                
                {uploadError ? (
                  <div className="upload-error">
                    <span className="error-icon">⚠️</span>
                    <span>{uploadError}</span>
                  </div>
                ) : uploadModal.serviceDefinition ? (
                  <div className="upload-preview">
                    <h3 className="preview-title">Service Preview</h3>
                    <div className="preview-info">
                      <div className="preview-field">
                        <span className="preview-label">Name:</span>
                        <span className="preview-value">{uploadModal.serviceDefinition.name}</span>
                      </div>
                      <div className="preview-field">
                        <span className="preview-label">Display Name:</span>
                        <span className="preview-value">{uploadModal.serviceDefinition.display_name}</span>
                      </div>
                      <div className="preview-field">
                        <span className="preview-label">Description:</span>
                        <span className="preview-value">{uploadModal.serviceDefinition.description}</span>
                      </div>
                      <div className="preview-field">
                        <span className="preview-label">Category:</span>
                        <span className="preview-value">{uploadModal.serviceDefinition.category}</span>
                      </div>
                      {uploadModal.serviceDefinition.author && (
                        <div className="preview-field">
                          <span className="preview-label">Author:</span>
                          <span className="preview-value">{uploadModal.serviceDefinition.author}</span>
                        </div>
                      )}
                      {uploadModal.serviceDefinition.version && (
                        <div className="preview-field">
                          <span className="preview-label">Version:</span>
                          <span className="preview-value">{uploadModal.serviceDefinition.version}</span>
                        </div>
                      )}
                    </div>
                    
                    <div className="json-preview">
                      <h4 className="json-preview-title">JSON Content</h4>
                      <pre className="json-content">
                        {JSON.stringify(uploadModal.serviceDefinition, null, 2)}
                      </pre>
                    </div>
                  </div>
                ) : null}
              </div>
              
              <div className="modal-footer">
                <button
                  onClick={() => setUploadModal(null)}
                  className="btn btn-secondary"
                >
                  Cancel
                </button>
                <button
                  onClick={handleUploadConfirm}
                  className="btn btn-primary"
                  disabled={!uploadModal.serviceDefinition || actionLoading.upload}
                >
                  {actionLoading.upload ? '⟳ Processing...' : 'Upload & Install'}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Install Config Modal */}
        {installModal && installModal.serviceDetails && (
          <div className="modal-overlay" onClick={() => setInstallModal(null)}>
            <div className="modal-content" onClick={(e) => e.stopPropagation()}>
              <div className="modal-header">
                <h2 className="modal-title">
                  Install {installModal.serviceDetails.definition?.display_name || installModal.serviceName}
                </h2>
                <button
                  onClick={() => setInstallModal(null)}
                  className="modal-close-btn"
                  disabled={actionLoading[installModal.serviceName] === 'installing'}
                >
                  ×
                </button>
              </div>
              
              <div className="modal-body">
                <p className="text-gray-600 mb-4">
                  {installModal.serviceDetails.definition?.description}
                </p>

                {installModal.serviceDetails.form && installModal.serviceDetails.form.fields && installModal.serviceDetails.form.fields.length > 0 ? (
                  <div className="config-form">
                    {installModal.serviceDetails.form.fields.map(field => (
                      <div key={field.name} className="form-group">
                        <label className="form-label">
                          {field.label}
                          {field.required && <span className="required">*</span>}
                        </label>
                        {field.type === 'text' && (
                          <input
                            type="text"
                            defaultValue={field.default || ''}
                            placeholder={field.default}
                            className="form-input"
                            data-field-name={field.name}
                          />
                        )}
                        {field.type === 'password' && (
                          <input
                            type="password"
                            defaultValue={field.default || ''}
                            className="form-input"
                            data-field-name={field.name}
                          />
                        )}
                        {field.type === 'number' && (
                          <input
                            type="number"
                            defaultValue={field.default || ''}
                            placeholder={field.default}
                            className="form-input"
                            data-field-name={field.name}
                          />
                        )}
                        {field.help && (
                          <p className="form-help">{field.help}</p>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="empty-state">
                    No configuration required for this service.
                  </div>
                )}
              </div>
              
              <div className="modal-footer">
                <button
                  onClick={() => setInstallModal(null)}
                  className="btn btn-secondary"
                  disabled={actionLoading[installModal.serviceName] === 'installing'}
                >
                  Cancel
                </button>
                <button
                  onClick={() => {
                    // Collect config from form inputs
                    const config = {};
                    const inputs = document.querySelectorAll('[data-field-name]');
                    inputs.forEach(input => {
                      const fieldName = input.getAttribute('data-field-name');
                      config[fieldName] = input.type === 'number' ? parseInt(input.value) || 0 : input.value;
                    });
                    handleInstallAfterUpload(installModal.serviceName, config);
                  }}
                  className="btn btn-primary"
                  disabled={actionLoading[installModal.serviceName] === 'installing'}
                >
                  {actionLoading[installModal.serviceName] === 'installing' ? '⟳ Installing...' : 'Start Installation'}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
