import React, { useState, useEffect, useMemo } from 'react';
import { useConfig } from '../context/ConfigContext';
import Button from '../components/common/Button';
import LoadingSpinner from '../components/common/LoadingSpinner';
import Card from '../components/common/Card';

const REGISTRY_URL = 'https://raw.githubusercontent.com/jbrinkw/luna-ext-store/main/registry.json';

export default function ExtensionStore() {
  const { currentState, updateExtension } = useConfig();
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
    return currentState?.extensions?.[extId] !== undefined;
  };

  const hasUpdate = (ext) => {
    const installed = currentState?.extensions?.[ext.id];
    if (!installed) return false;
    
    // Simple version comparison - could be improved
    return ext.version !== installed.version;
  };

  const handleInstall = (storeExt) => {
    if (isInstalled(storeExt.id)) {
      alert('Extension is already installed');
      return;
    }

    // Generate source string
    let source;
    if (storeExt.type === 'embedded') {
      source = `github:jbrinkw/luna-ext-store:${storeExt.path}`;
    } else {
      source = storeExt.source;
    }

    // Add to currentState
    updateExtension(storeExt.id, {
      enabled: true,
      source,
      config: {},
    });

    alert(`Added ${storeExt.name} to pending changes. Save to queue to install.`);
  };

  const handleUpdate = (storeExt) => {
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

    alert(`Added ${storeExt.name} update to pending changes. Save to queue to apply.`);
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
                      <Button onClick={() => handleUpdate(ext)}>
                        🔄 Update Available
                      </Button>
                    ) : (
                      <Button variant="secondary" disabled>
                        ✓ Installed
                      </Button>
                    )}
                  </>
                ) : (
                  <Button onClick={() => handleInstall(ext)}>
                    Install
                  </Button>
                )}
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
