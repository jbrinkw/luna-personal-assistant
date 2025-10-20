import React, { useState, useEffect, useMemo } from 'react';
import { useConfig } from '../context/ConfigContext';
import { useServices } from '../context/ServicesContext';
import Button from '../components/common/Button';
import LoadingSpinner from '../components/common/LoadingSpinner';
import Card from '../components/common/Card';

const REGISTRY_URL = 'https://raw.githubusercontent.com/jbrinkw/luna-ext-store/main/registry.json';

export default function ExtensionStore() {
  const { currentState, originalState, updateExtension, deleteExtension } = useConfig();
  const { extensions } = useServices();
  const [registry, setRegistry] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [filterHasUI, setFilterHasUI] = useState(false);
  const [filterNoDeps, setFilterNoDeps] = useState(false);

  useEffect(() => {
    loadRegistry();
  }, []);

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
      setError(error.message || 'Failed to load extension registry');
      // Use fallback empty registry
      setRegistry({ version: 'unknown', extensions: [], categories: [] });
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

  const filteredExtensions = useMemo(() => {
    if (!registry?.extensions) return [];

    let filtered = [...registry.extensions];

    // Search filter
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      filtered = filtered.filter(ext =>
        ext.name.toLowerCase().includes(term) ||
        ext.description?.toLowerCase().includes(term) ||
        ext.tags?.some(tag => tag.toLowerCase().includes(term))
      );
    }

    // Category filter
    if (selectedCategory && selectedCategory !== 'all') {
      filtered = filtered.filter(ext => ext.category === selectedCategory);
    }

    // Has UI filter
    if (filterHasUI) {
      filtered = filtered.filter(ext => ext.has_ui);
    }

    // No dependencies filter
    if (filterNoDeps) {
      filtered = filtered.filter(ext => !ext.required_secrets || ext.required_secrets.length === 0);
    }

    return filtered;
  }, [registry, searchTerm, selectedCategory, filterHasUI, filterNoDeps]);

  if (loading) {
    return (
      <div className="page-container">
        <LoadingSpinner message="Loading extension store..." />
      </div>
    );
  }

  const categories = registry?.categories || [];

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1>Extension Store</h1>
          <p className="page-subtitle">Browse and install community extensions</p>
        </div>
      </div>

      {error && (
        <div className="error-message">
          {error}
        </div>
      )}

      {/* Search and Filters */}
      <div className="store-filters">
        <input
          type="text"
          className="search-input"
          placeholder="Search extensions..."
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

      {/* Extension Grid */}
      {filteredExtensions.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">🔍</div>
          <h2>No Extensions Found</h2>
          <p>Try adjusting your search or filters</p>
        </div>
      ) : (
        <div className="store-grid">
          {filteredExtensions.map(ext => (
            <Card key={ext.id} className="store-card">
              <div className="store-card-header">
                <h3>{ext.name}</h3>
                <span className="version-tag">v{ext.version}</span>
              </div>

              <p className="store-card-author">by {ext.author || 'Unknown'}</p>
              <p className="store-card-description">{ext.description}</p>

              <div className="store-card-metadata">
                <span>🛠️ {ext.tool_count || 0} tools</span>
                {ext.has_ui && <span>• 🖥️ UI included</span>}
                <span>• 📦 {ext.category}</span>
              </div>

              {ext.required_secrets && ext.required_secrets.length > 0 && (
                <div className="store-card-requirements">
                  <strong>Requires:</strong> {ext.required_secrets.join(', ')}
                </div>
              )}

              {ext.tags && ext.tags.length > 0 && (
                <div className="store-card-tags">
                  {ext.tags.map(tag => (
                    <span key={tag} className="tag">{tag}</span>
                  ))}
                </div>
              )}

              <div className="store-card-actions">
                {isInstalled(ext.id) ? (
                  <>
                    {hasUpdate(ext) ? (
                      isPendingUpdate(ext.id) ? (
                        <Button 
                          onClick={() => handleUpdateToggle(ext)}
                          style={{ backgroundColor: '#10b981', borderColor: '#10b981' }}
                        >
                          ⏳ Pending Update
                        </Button>
                      ) : (
                        <Button onClick={() => handleUpdateToggle(ext)}>
                          🔄 Update Available
                        </Button>
                      )
                    ) : (
                      isPendingReinstall(ext.id) ? (
                        <Button 
                          onClick={() => handleReinstallToggle(ext)}
                          style={{ backgroundColor: '#10b981', borderColor: '#10b981' }}
                        >
                          ⏳ Pending Reinstall
                        </Button>
                      ) : (
                        <Button onClick={() => handleReinstallToggle(ext)}>
                          🔄 Reinstall
                        </Button>
                      )
                    )}
                  </>
                ) : (
                  isPendingInstall(ext.id) ? (
                    <Button 
                      onClick={() => handleInstallToggle(ext)}
                      style={{ backgroundColor: '#10b981', borderColor: '#10b981' }}
                    >
                      ⏳ Pending Install
                    </Button>
                  ) : (
                    <Button onClick={() => handleInstallToggle(ext)}>
                      Install
                    </Button>
                  )
                )}
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
