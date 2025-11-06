import React, { useState, useEffect, useMemo } from 'react';
import { useConfig } from '../context/ConfigContext';
import { useServices } from '../context/ServicesContext';
import Button from '../components/common/Button';
import LoadingSpinner from '../components/common/LoadingSpinner';
import Card from '../components/common/Card';
import { getInstalledServices, installService, uploadService, getServiceDetails } from '../lib/externalServicesApi';
import { KeysAPI } from '../lib/api';

const REGISTRY_URL = 'https://raw.githubusercontent.com/jbrinkw/luna-ext-store/main/registry.json';

export default function ExtensionStore() {
  const { queuedState, originalState, updateExtension, deleteExtension } = useConfig();
  const { extensions } = useServices();
  const [registry, setRegistry] = useState(null);
  const [loading, setLoading] = useState(true);
  
  // Helper to get current config (queue or original)
  const currentConfig = queuedState?.master_config || originalState;
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [selectedType, setSelectedType] = useState('all'); // all, extension, service
  const [filterHasUI, setFilterHasUI] = useState(false);
  const [filterNoDeps, setFilterNoDeps] = useState(false);
  const [installedServices, setInstalledServices] = useState({});
  const [installModal, setInstallModal] = useState(null);
  const [installConfig, setInstallConfig] = useState({});
  const [installing, setInstalling] = useState(false);
  const [secretsModal, setSecretsModal] = useState(null);
  const [secretsFormData, setSecretsFormData] = useState({});
  const [savingSecrets, setSavingSecrets] = useState(false);
  const [secretsVisibility, setSecretsVisibility] = useState({});

  useEffect(() => {
    loadRegistry();
    loadInstalledServices();
  }, []);

  const loadInstalledServices = async () => {
    try {
      const data = await getInstalledServices();
      setInstalledServices(data);
    } catch (error) {
      console.error('Failed to load installed services:', error);
    }
  };

  const loadRegistry = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await fetch(REGISTRY_URL);
      if (!response.ok) {
        throw new Error('Failed to load extension registry');
      }
      
      const data = await response.json();
      setRegistry(data);
    } catch (error) {
      console.error('Failed to load registry:', error);
      setError(error.message || 'Failed to load addon registry');
      // Use fallback empty registry
      setRegistry({ version: 'unknown', extensions: [], external_services: [], categories: [] });
    } finally {
      setLoading(false);
    }
  };

  const isInstalled = (extId) => {
    // Check if extension actually exists on disk (via ServicesContext)
    return extensions?.some(e => e.name === extId);
  };

  const hasUpdate = (ext) => {
    // Extension must exist on disk to check for updates
    const onDisk = extensions?.find(e => e.name === ext.id);
    if (!onDisk) return false;
    
    // Compare store version with actual installed version from disk
    const installedVersion = onDisk.version;
    const storeVersion = ext.version;
    
    // If versions match, no update needed
    if (installedVersion === storeVersion) return false;
    
    // If either version is unknown, can't determine if update needed
    if (!installedVersion || installedVersion === 'unknown') return false;
    if (!storeVersion || storeVersion === 'unknown') return false;
    
    // Versions differ, update available
    return true;
  };

  const isPendingInstall = (extId) => {
    // Check if extension is in queue but not in original (new install)
    const inQueue = currentConfig?.extensions?.[extId];
    const inOriginal = originalState?.extensions?.[extId];
    const onDisk = isInstalled(extId);
    
    // Pending install only if it's NEW in queue (not in original) and not yet on disk
    return inQueue && !inOriginal && !onDisk;
  };

  const isPendingUpdate = (extId) => {
    // Check if extension source has changed from original
    const inQueue = currentConfig?.extensions?.[extId];
    const inOriginal = originalState?.extensions?.[extId];
    
    // Pending update if in both states AND source changed
    return inQueue && inOriginal && inQueue.source !== inOriginal.source;
  };

  const isPendingReinstall = (extId) => {
    // Check if extension is marked for reinstall
    const inQueue = currentConfig?.extensions?.[extId];
    const inOriginal = originalState?.extensions?.[extId];
    const onDisk = isInstalled(extId);
    
    // Pending reinstall if on disk, in both states, and source has #reinstall marker
    return onDisk && inQueue && inOriginal && 
           inQueue.source && inQueue.source.includes('#reinstall');
  };

  const doInstallExtension = async (storeExt) => {
    // Generate source string
    let source;
    if (storeExt.type === 'embedded') {
      source = `github:jbrinkw/luna-ext-store:${storeExt.path}`;
    } else {
      source = storeExt.source;
    }

    // Check if extension exists in queue (from master_config) but not on disk
    const existsInConfig = currentConfig?.extensions?.[storeExt.id];
    
    if (existsInConfig && existsInConfig.source === source) {
      // Extension is in config with same source but not on disk (reinstall scenario)
      // Append reinstall marker to force change detection, will be cleaned by apply_updates
      source = source + '#reinstall';
    }

    // Add to queue
    await updateExtension(storeExt.id, {
      enabled: true,
      source,
      config: existsInConfig?.config || {},
    });
  };

  const handleInstallToggle = async (storeExt) => {
    // If already pending, remove it (undo)
    if (isPendingInstall(storeExt.id)) {
      await deleteExtension(storeExt.id);
      return;
    }

    // Otherwise, add it to pending
    if (isInstalled(storeExt.id)) {
      return;
    }

    // Check if extension has required secrets
    if (storeExt.required_secrets && storeExt.required_secrets.length > 0) {
      // Load existing secrets from .env
      try {
        const existingSecrets = await KeysAPI.list();
        const initialFormData = {};
        const initialVisibility = {};
        
        storeExt.required_secrets.forEach(secret => {
          // Prefill with existing value if available
          initialFormData[secret] = existingSecrets[secret] || '';
          initialVisibility[secret] = false;
        });
        
        setSecretsFormData(initialFormData);
        setSecretsVisibility(initialVisibility);
        setSecretsModal(storeExt);
      } catch (error) {
        console.error('Failed to load existing secrets:', error);
        // Still open modal even if loading fails
        const initialFormData = {};
        const initialVisibility = {};
        storeExt.required_secrets.forEach(secret => {
          initialFormData[secret] = '';
          initialVisibility[secret] = false;
        });
        setSecretsFormData(initialFormData);
        setSecretsVisibility(initialVisibility);
        setSecretsModal(storeExt);
      }
    } else {
      // No secrets required, proceed with install
      await doInstallExtension(storeExt);
    }
  };

  const handleUpdateToggle = async (storeExt) => {
    // If already pending update, revert to original source (undo)
    if (isPendingUpdate(storeExt.id)) {
      const original = originalState?.extensions?.[storeExt.id];
      if (original) {
        await updateExtension(storeExt.id, {
          ...original,
        });
      }
      return;
    }

    // Otherwise, add update to pending
    let source;
    if (storeExt.type === 'embedded') {
      source = `github:jbrinkw/luna-ext-store:${storeExt.path}`;
    } else {
      source = storeExt.source;
    }

    // Get existing extension data from queue, or use defaults
    const existing = currentConfig?.extensions?.[storeExt.id] || {};
    const existingSource = existing.source || '';
    
    // If the base source is the same, append a version marker to force change detection
    // This is needed because GitHub sources don't include version numbers
    const baseSource = existingSource.replace(/#update-.*$/g, '');
    if (baseSource === source) {
      source = `${source}#update-${storeExt.version}`;
    }
    
    await updateExtension(storeExt.id, {
      enabled: existing.enabled !== undefined ? existing.enabled : true,
      config: existing.config || {},
      source,
    });
  };

  const handleReinstallToggle = async (storeExt) => {
    // If already pending reinstall, revert to original (undo)
    if (isPendingReinstall(storeExt.id)) {
      const original = originalState?.extensions?.[storeExt.id];
      if (original) {
        await updateExtension(storeExt.id, {
          ...original,
        });
      }
      return;
    }

    // Otherwise, add reinstall marker to trigger reinstall
    const existing = currentConfig.extensions[storeExt.id];
    const currentSource = existing?.source || '';
    
    // Add unique reinstall marker with timestamp to force change detection
    const timestamp = Date.now();
    const newSource = currentSource.replace(/#reinstall-\d+/g, '') + `#reinstall-${timestamp}`;
    
    await updateExtension(storeExt.id, {
      ...existing,
      source: newSource,
    });
  };

  const isServiceInstalled = (serviceName) => {
    return installedServices[serviceName]?.installed === true;
  };

  const filteredAddons = useMemo(() => {
    if (!registry) return [];

    // Combine extensions and services into unified addon list
    let addons = [];
    
    if (registry.extensions) {
      addons = addons.concat(
        registry.extensions.map(ext => ({ ...ext, addon_type: 'extension' }))
      );
    }
    
    if (registry.external_services) {
      addons = addons.concat(
        registry.external_services.map(svc => ({ ...svc, addon_type: 'service', id: svc.name }))
      );
    }

    // Type filter
    if (selectedType !== 'all') {
      addons = addons.filter(addon => addon.addon_type === selectedType);
    }

    // Search filter
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      addons = addons.filter(addon =>
        addon.name?.toLowerCase().includes(term) ||
        addon.display_name?.toLowerCase().includes(term) ||
        addon.description?.toLowerCase().includes(term) ||
        addon.tags?.some(tag => tag.toLowerCase().includes(term)) ||
        addon.provides_vars?.some(v => v.toLowerCase().includes(term))
      );
    }

    // Category filter
    if (selectedCategory && selectedCategory !== 'all') {
      addons = addons.filter(addon => addon.category === selectedCategory);
    }

    // Has UI filter
    if (filterHasUI) {
      addons = addons.filter(addon => addon.has_ui);
    }

    // No dependencies filter (only for extensions)
    if (filterNoDeps) {
      addons = addons.filter(addon => 
        addon.addon_type === 'service' || 
        !addon.required_secrets || 
        addon.required_secrets.length === 0
      );
    }

    return addons;
  }, [registry, searchTerm, selectedCategory, selectedType, filterHasUI, filterNoDeps]);

  const handleServiceInstall = async (service) => {
    const config = installConfig;
    setInstalling(true);
    
    try {
      // First, check if service definition exists locally
      // If not, upload it from the registry
      try {
        await getServiceDetails(service.name);
        // Service exists locally, proceed with installation
      } catch (error) {
        // Service doesn't exist locally (404), need to upload it first
        if (service.service_definition) {
          console.log(`Uploading service definition for ${service.name}...`);
          await uploadService(service.service_definition);
        } else {
          throw new Error(`Service definition not found for ${service.name}. Cannot install.`);
        }
      }
      
      // Now install the service
      await installService(service.name, config);
      await loadInstalledServices();
      setInstallModal(null);
      setInstallConfig({});
    } catch (error) {
      console.error('Failed to install service:', error);
      alert(`Installation failed: ${error.message}`);
    } finally {
      setInstalling(false);
    }
  };

  const openInstallModal = (service) => {
    // Initialize config with defaults
    const defaults = {};
    service.service_definition?.config_form?.fields?.forEach(field => {
      defaults[field.name] = field.default || '';
    });
    setInstallConfig(defaults);
    setInstallModal(service);
  };

  const handleSecretsContinue = async () => {
    if (!secretsModal) return;

    setSavingSecrets(true);
    try {
      // Save all non-empty secrets to .env sequentially to avoid race conditions
      for (const [key, value] of Object.entries(secretsFormData)) {
        if (value && value.trim()) {
          await KeysAPI.set(key, value.trim());
        }
      }
      
      // Add extension to queue
      doInstallExtension(secretsModal);
      
      // Close modal and reset
      setSecretsModal(null);
      setSecretsFormData({});
      setSecretsVisibility({});
    } catch (error) {
      console.error('Failed to save secrets:', error);
      alert(`Failed to save secrets: ${error.message}`);
    } finally {
      setSavingSecrets(false);
    }
  };

  const handleSecretsSkip = () => {
    if (!secretsModal) return;
    
    // Add extension to queue without saving secrets
    doInstallExtension(secretsModal);
    
    // Close modal and reset
    setSecretsModal(null);
    setSecretsFormData({});
    setSecretsVisibility({});
  };

  const handleSecretsCancel = () => {
    // Just close modal and reset
    setSecretsModal(null);
    setSecretsFormData({});
    setSecretsVisibility({});
  };

  const toggleSecretVisibility = (secret) => {
    setSecretsVisibility(prev => ({
      ...prev,
      [secret]: !prev[secret]
    }));
  };

  if (loading) {
    return (
      <div className="page-container">
        <LoadingSpinner message="Loading addon store..." />
      </div>
    );
  }

  const categories = registry?.categories || [];

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1>Addon Store</h1>
          <p className="page-subtitle">Browse and install extensions and services</p>
        </div>
      </div>

      {error && (
        <div className="error-message">
          {error}
        </div>
      )}

      {/* Type Filter Tabs */}
      <div className="type-filter-tabs">
        <button
          className={`type-tab ${selectedType === 'all' ? 'active' : ''}`}
          onClick={() => setSelectedType('all')}
        >
          All
        </button>
        <button
          className={`type-tab ${selectedType === 'extension' ? 'active' : ''}`}
          onClick={() => setSelectedType('extension')}
        >
          Extensions
        </button>
        <button
          className={`type-tab ${selectedType === 'service' ? 'active' : ''}`}
          onClick={() => setSelectedType('service')}
        >
          Services
        </button>
      </div>

      {/* Search and Filters */}
      <div className="store-filters">
        <input
          type="text"
          className="search-input"
          placeholder="Search addons..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          autoComplete="off"
        />

        <select
          className="category-select"
          value={selectedCategory}
          onChange={(e) => setSelectedCategory(e.target.value)}
        >
          <option value="all">All Categories</option>
          {categories.map(cat => (
            <option key={typeof cat === 'string' ? cat : cat.id} value={typeof cat === 'string' ? cat : cat.id}>
              {typeof cat === 'string' ? cat : cat.name}
            </option>
          ))}
        </select>

        <label className="filter-checkbox">
          <input
            type="checkbox"
            checked={filterHasUI}
            onChange={(e) => setFilterHasUI(e.target.checked)}
          />
          <span>Has UI</span>
        </label>

        <label className="filter-checkbox">
          <input
            type="checkbox"
            checked={filterNoDeps}
            onChange={(e) => setFilterNoDeps(e.target.checked)}
          />
          <span>No Dependencies</span>
        </label>
      </div>

      {/* Addon Grid */}
      {filteredAddons.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">🔍</div>
          <h2>No Addons Found</h2>
          <p>Try adjusting your search or filters</p>
        </div>
      ) : (
        <div className="store-grid">
          {filteredAddons.map(addon => addon.addon_type === 'extension' ? (
            // Extension Card
            <Card key={addon.id} className="store-card">
              <div className="store-card-header">
                <div>
                  <h3>{addon.name}</h3>
                  <span className="store-badge store-badge-extension">
                    Extension
                  </span>
                </div>
                <span className="version-tag">v{addon.version}</span>
              </div>

              <p className="store-card-author">by {addon.author || 'Unknown'}</p>
              <p className="store-card-description">{addon.description}</p>

              <div className="store-card-metadata">
                <span>🛠️ {addon.tool_count || 0} tools</span>
                {addon.service_count > 0 && <span>• ⚙️ {addon.service_count} services</span>}
                {addon.has_ui && <span>• 🖥️ UI included</span>}
                <span>• 📦 {addon.category}</span>
              </div>

              {addon.required_secrets && addon.required_secrets.length > 0 && (
                <div className="store-card-requirements">
                  <strong>Requires:</strong> {addon.required_secrets.join(', ')}
                </div>
              )}

              {addon.tags && addon.tags.length > 0 && (
                <div className="store-card-tags">
                  {addon.tags.map(tag => (
                    <span key={tag} className="tag">{tag}</span>
                  ))}
                </div>
              )}

              <div className="store-card-actions">
                {isInstalled(addon.id) ? (
                  <>
                    {hasUpdate(addon) ? (
                      isPendingUpdate(addon.id) ? (
                        <Button 
                          onClick={() => handleUpdateToggle(addon)}
                          variant="success"
                        >
                          ⏳ Pending Update
                        </Button>
                      ) : (
                        <Button onClick={() => handleUpdateToggle(addon)}>
                          🔄 Update Available
                        </Button>
                      )
                    ) : (
                      isPendingReinstall(addon.id) ? (
                        <Button 
                          onClick={() => handleReinstallToggle(addon)}
                          variant="success"
                        >
                          ⏳ Pending Reinstall
                        </Button>
                      ) : (
                        <Button onClick={() => handleReinstallToggle(addon)}>
                          🔄 Reinstall
                        </Button>
                      )
                    )}
                  </>
                  ) : (
                    isPendingInstall(addon.id) ? (
                      <Button 
                        onClick={() => handleInstallToggle(addon)}
                        variant="success"
                      >
                        ⏳ Pending Install
                      </Button>
                    ) : (
                      <Button onClick={() => handleInstallToggle(addon)}>
                      Install
                    </Button>
                  )
                )}
              </div>
            </Card>
          ) : (
            // Service Card
            <Card key={addon.name} className="store-card">
              <div className="store-card-header">
                <div>
                  <h3>{addon.display_name || addon.name}</h3>
                  <span className="store-badge store-badge-service">
                    Service
                  </span>
                </div>
                <span className="version-tag">{addon.version}</span>
              </div>

              <p className="store-card-description">{addon.description}</p>

              <div className="store-card-metadata">
                <span>📦 {addon.category}</span>
                {addon.has_ui && <span>• 🌐 Web UI</span>}
                <span>• 🔌 {addon.config_fields || 0} config fields</span>
              </div>

              {addon.provides_vars && addon.provides_vars.length > 0 && (
                <div className="store-card-requirements store-card-requirements--provides">
                  <strong>Provides:</strong> {addon.provides_vars.slice(0, 3).join(', ')}
                  {addon.provides_vars.length > 3 && ` +${addon.provides_vars.length - 3} more`}
                </div>
              )}

              {addon.tags && addon.tags.length > 0 && (
                <div className="store-card-tags">
                  {addon.tags.map(tag => (
                    <span key={tag} className="tag">{tag}</span>
                  ))}
                </div>
              )}

              <div className="store-card-actions">
                {isServiceInstalled(addon.name) ? (
                  <Button 
                    variant="muted"
                    disabled
                  >
                    ✓ Installed
                  </Button>
                ) : (
                  <Button onClick={() => openInstallModal(addon)}>
                    Install
                  </Button>
                )}
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Install Service Modal */}
      {installModal && (
        <div className="modal-overlay" onClick={() => !installing && setInstallModal(null)}>
          <div className="modal-content store-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Install {installModal.display_name || installModal.name}</h2>
              <button className="modal-close" onClick={() => !installing && setInstallModal(null)}>×</button>
            </div>
            
            <div className="modal-body">
              <p className="store-modal-description">{installModal.description}</p>
              
              {installModal.service_definition?.config_form?.fields?.map(field => (
                <div key={field.name} className="store-modal-field">
                  <label className="store-modal-label">
                    {field.label}
                    {field.required && <span className="store-modal-required">*</span>}
                  </label>
                  {field.help && (
                    <p className="store-modal-help">{field.help}</p>
                  )}
                  <input
                    type={field.type}
                    value={installConfig[field.name] || ''}
                    onChange={(e) => setInstallConfig({ ...installConfig, [field.name]: e.target.value })}
                    placeholder={field.default}
                    required={field.required}
                    disabled={installing}
                    className="store-modal-input"
                  />
                </div>
              ))}
            </div>
            
            <div className="modal-footer">
              <Button 
                onClick={() => setInstallModal(null)} 
                disabled={installing}
                variant="muted"
              >
                Cancel
              </Button>
              <Button 
                onClick={() => handleServiceInstall(installModal)}
                disabled={installing}
              >
                {installing ? 'Installing...' : 'Install'}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Extension Secrets Configuration Modal */}
      {secretsModal && (
        <div className="modal-overlay" onClick={() => !savingSecrets && handleSecretsCancel()}>
          <div className="modal-content store-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Configure {secretsModal.name}</h2>
              <button className="modal-close" onClick={() => !savingSecrets && handleSecretsCancel()}>×</button>
            </div>
            
            <div className="modal-body">
              <p className="store-modal-description">
                {secretsModal.description}
              </p>
              <p className="store-modal-description">
                This extension requires the following environment variables. You can configure them now or skip and add them later.
              </p>
              
              {secretsModal.required_secrets?.map(secret => (
                <div key={secret} className="store-modal-field">
                  <label className="store-modal-label">
                    {secret}
                  </label>
                  <div style={{ position: 'relative' }}>
                    <input
                      type={secretsVisibility[secret] ? "text" : "password"}
                      value={secretsFormData[secret] || ''}
                      onChange={(e) => setSecretsFormData({ ...secretsFormData, [secret]: e.target.value })}
                      placeholder={`Enter ${secret}`}
                      disabled={savingSecrets}
                      className="store-modal-input"
                      autoComplete="new-password"
                      style={{ paddingRight: '40px' }}
                    />
                    <button
                      type="button"
                      onClick={() => toggleSecretVisibility(secret)}
                      disabled={savingSecrets}
                      style={{
                        position: 'absolute',
                        right: '8px',
                        top: '50%',
                        transform: 'translateY(-50%)',
                        background: 'none',
                        border: 'none',
                        cursor: 'pointer',
                        padding: '4px 8px',
                        fontSize: '16px',
                        opacity: savingSecrets ? 0.5 : 0.7,
                        transition: 'opacity 0.2s'
                      }}
                      onMouseEnter={(e) => e.currentTarget.style.opacity = '1'}
                      onMouseLeave={(e) => e.currentTarget.style.opacity = savingSecrets ? '0.5' : '0.7'}
                    >
                      {secretsVisibility[secret] ? '👁️' : '👁️‍🗨️'}
                    </button>
                  </div>
                </div>
              ))}
            </div>
            
            <div className="modal-footer">
              <Button 
                onClick={handleSecretsCancel} 
                disabled={savingSecrets}
                variant="muted"
              >
                Cancel
              </Button>
              <Button 
                onClick={handleSecretsSkip}
                disabled={savingSecrets}
                variant="secondary"
              >
                Skip
              </Button>
              <Button 
                onClick={handleSecretsContinue}
                disabled={savingSecrets}
              >
                {savingSecrets ? 'Saving...' : 'Continue'}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
