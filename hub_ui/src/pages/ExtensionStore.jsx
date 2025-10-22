import React, { useState, useEffect, useMemo } from 'react';
import { useConfig } from '../context/ConfigContext';
import { useServices } from '../context/ServicesContext';
import Button from '../components/common/Button';
import LoadingSpinner from '../components/common/LoadingSpinner';
import Card from '../components/common/Card';
import { getInstalledServices, installService } from '../lib/externalServicesApi';

const REGISTRY_URL = 'https://raw.githubusercontent.com/jbrinkw/luna-ext-store/main/registry.json';

export default function ExtensionStore() {
  const { currentState, originalState, updateExtension, deleteExtension } = useConfig();
  const { extensions } = useServices();
  const [registry, setRegistry] = useState(null);
  const [loading, setLoading] = useState(true);
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
    // Check if extension is in currentState but not in originalState (new install)
    const inCurrent = currentState?.extensions?.[extId];
    const inOriginal = originalState?.extensions?.[extId];
    const onDisk = isInstalled(extId);
    
    // Pending install only if it's NEW in current (not in original) and not yet on disk
    return inCurrent && !inOriginal && !onDisk;
  };

  const isPendingUpdate = (extId) => {
    // Check if extension source has changed from original
    const inCurrent = currentState?.extensions?.[extId];
    const inOriginal = originalState?.extensions?.[extId];
    
    // Pending update if in both states AND source changed
    return inCurrent && inOriginal && inCurrent.source !== inOriginal.source;
  };

  const isPendingReinstall = (extId) => {
    // Check if extension is marked for reinstall
    const inCurrent = currentState?.extensions?.[extId];
    const inOriginal = originalState?.extensions?.[extId];
    const onDisk = isInstalled(extId);
    
    // Pending reinstall if on disk, in both states, and source has #reinstall marker
    return onDisk && inCurrent && inOriginal && 
           inCurrent.source && inCurrent.source.includes('#reinstall');
  };

  const handleInstallToggle = (storeExt) => {
    // If already pending, remove it (undo)
    if (isPendingInstall(storeExt.id)) {
      deleteExtension(storeExt.id);
      return;
    }

    // Otherwise, add it to pending
    if (isInstalled(storeExt.id)) {
      return;
    }

    // Generate source string
    let source;
    if (storeExt.type === 'embedded') {
      source = `github:jbrinkw/luna-ext-store:${storeExt.path}`;
    } else {
      source = storeExt.source;
    }

    // Check if extension exists in currentState (from master_config) but not on disk
    const existsInConfig = currentState?.extensions?.[storeExt.id];
    
    if (existsInConfig && existsInConfig.source === source) {
      // Extension is in config with same source but not on disk (reinstall scenario)
      // Append reinstall marker to force change detection, will be cleaned by apply_updates
      source = source + '#reinstall';
    }

    // Add to currentState
    updateExtension(storeExt.id, {
      enabled: true,
      source,
      config: existsInConfig?.config || {},
    });
  };

  const handleUpdateToggle = (storeExt) => {
    // If already pending update, revert to original source (undo)
    if (isPendingUpdate(storeExt.id)) {
      const original = originalState?.extensions?.[storeExt.id];
      if (original) {
        updateExtension(storeExt.id, {
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

    const existing = currentState.extensions[storeExt.id];
    updateExtension(storeExt.id, {
      ...existing,
      source,
    });
  };

  const handleReinstallToggle = (storeExt) => {
    // If already pending reinstall, revert to original (undo)
    if (isPendingReinstall(storeExt.id)) {
      const original = originalState?.extensions?.[storeExt.id];
      if (original) {
        updateExtension(storeExt.id, {
          ...original,
        });
      }
      return;
    }

    // Otherwise, add reinstall marker to trigger reinstall
    const existing = currentState.extensions[storeExt.id];
    const currentSource = existing?.source || '';
    
    // Add unique reinstall marker with timestamp to force change detection
    const timestamp = Date.now();
    const newSource = currentSource.replace(/#reinstall-\d+/g, '') + `#reinstall-${timestamp}`;
    
    updateExtension(storeExt.id, {
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
      <div className="type-filter-tabs" style={{ marginBottom: '1rem' }}>
        <button
          className={`type-tab ${selectedType === 'all' ? 'active' : ''}`}
          onClick={() => setSelectedType('all')}
          style={{
            padding: '0.5rem 1rem',
            backgroundColor: selectedType === 'all' ? '#3b82f6' : '#f3f4f6',
            color: selectedType === 'all' ? 'white' : '#374151',
            border: 'none',
            borderRadius: '0.375rem 0 0 0.375rem',
            cursor: 'pointer',
            fontWeight: 500
          }}
        >
          All
        </button>
        <button
          className={`type-tab ${selectedType === 'extension' ? 'active' : ''}`}
          onClick={() => setSelectedType('extension')}
          style={{
            padding: '0.5rem 1rem',
            backgroundColor: selectedType === 'extension' ? '#3b82f6' : '#f3f4f6',
            color: selectedType === 'extension' ? 'white' : '#374151',
            border: 'none',
            cursor: 'pointer',
            fontWeight: 500
          }}
        >
          Extensions
        </button>
        <button
          className={`type-tab ${selectedType === 'service' ? 'active' : ''}`}
          onClick={() => setSelectedType('service')}
          style={{
            padding: '0.5rem 1rem',
            backgroundColor: selectedType === 'service' ? '#10b981' : '#f3f4f6',
            color: selectedType === 'service' ? 'white' : '#374151',
            border: 'none',
            borderRadius: '0 0.375rem 0.375rem 0',
            cursor: 'pointer',
            fontWeight: 500
          }}
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
                  <span className="badge" style={{ backgroundColor: '#3b82f6', color: 'white', padding: '0.25rem 0.5rem', borderRadius: '0.25rem', fontSize: '0.75rem', fontWeight: 600 }}>
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
                          style={{ backgroundColor: '#10b981', borderColor: '#10b981' }}
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
                          style={{ backgroundColor: '#10b981', borderColor: '#10b981' }}
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
                      style={{ backgroundColor: '#10b981', borderColor: '#10b981' }}
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
                  <span className="badge" style={{ backgroundColor: '#10b981', color: 'white', padding: '0.25rem 0.5rem', borderRadius: '0.25rem', fontSize: '0.75rem', fontWeight: 600 }}>
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
                <div className="store-card-requirements" style={{ borderColor: '#10b981' }}>
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
                    style={{ backgroundColor: '#6b7280', borderColor: '#6b7280', cursor: 'default' }}
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
          <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '500px' }}>
            <div className="modal-header">
              <h2>Install {installModal.display_name || installModal.name}</h2>
              <button className="modal-close" onClick={() => !installing && setInstallModal(null)}>×</button>
            </div>
            
            <div className="modal-body">
              <p style={{ marginBottom: '1rem', color: '#6b7280' }}>{installModal.description}</p>
              
              {installModal.service_definition?.config_form?.fields?.map(field => (
                <div key={field.name} style={{ marginBottom: '1rem' }}>
                  <label style={{ display: 'block', fontWeight: 500, marginBottom: '0.25rem' }}>
                    {field.label}
                    {field.required && <span style={{ color: '#ef4444' }}>*</span>}
                  </label>
                  {field.help && (
                    <p style={{ fontSize: '0.875rem', color: '#6b7280', marginBottom: '0.25rem' }}>{field.help}</p>
                  )}
                  <input
                    type={field.type}
                    value={installConfig[field.name] || ''}
                    onChange={(e) => setInstallConfig({ ...installConfig, [field.name]: e.target.value })}
                    placeholder={field.default}
                    required={field.required}
                    disabled={installing}
                    style={{
                      width: '100%',
                      padding: '0.5rem',
                      border: '1px solid #d1d5db',
                      borderRadius: '0.375rem',
                      fontSize: '1rem'
                    }}
                  />
                </div>
              ))}
            </div>
            
            <div className="modal-footer">
              <Button 
                onClick={() => setInstallModal(null)} 
                disabled={installing}
                style={{ backgroundColor: '#6b7280', borderColor: '#6b7280' }}
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
    </div>
  );
}
