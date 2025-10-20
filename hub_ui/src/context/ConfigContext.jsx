import React, { createContext, useContext, useState, useEffect, useMemo } from 'react';
import { ConfigAPI, QueueAPI, ExtensionsAPI } from '../lib/api';
import { deepClone } from '../lib/utils';

const ConfigContext = createContext();

export const useConfig = () => {
  const context = useContext(ConfigContext);
  if (!context) {
    throw new Error('useConfig must be used within ConfigProvider');
  }
  return context;
};

export const ConfigProvider = ({ children }) => {
  const [originalState, setOriginalState] = useState(null);
  const [currentState, setCurrentState] = useState(null);
  const [queuedState, setQueuedState] = useState(null);
  const [installedExtensions, setInstalledExtensions] = useState([]);
  const [loading, setLoading] = useState(true);

  // Load master config from server
  const loadMasterConfig = async () => {
    try {
      setLoading(true);
      const config = await ConfigAPI.getMaster();
      setOriginalState(config);
      setCurrentState(deepClone(config));
      
      // Load list of actually installed extensions (on disk)
      const extsData = await ExtensionsAPI.list();
      setInstalledExtensions(extsData.extensions || []);
      
      // Check for existing queue
      const queue = await QueueAPI.getCurrent();
      setQueuedState(queue);
    } catch (error) {
      console.error('Failed to load master config:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadMasterConfig();
  }, []);

  // Update extension in current state
  const updateExtension = (name, data) => {
    setCurrentState(prev => {
      const updated = deepClone(prev);
      if (!updated.extensions) {
        updated.extensions = {};
      }
      
      if (!updated.extensions[name]) {
        updated.extensions[name] = {};
      }
      
      updated.extensions[name] = {
        ...updated.extensions[name],
        ...data,
      };
      
      return updated;
    });
  };

  // Delete extension from current state
  const deleteExtension = (name) => {
    setCurrentState(prev => {
      const updated = deepClone(prev);
      if (updated.extensions && updated.extensions[name]) {
        delete updated.extensions[name];
      }
      return updated;
    });
  };

  // Update tool config in current state
  const updateTool = (toolName, config) => {
    setCurrentState(prev => {
      const updated = deepClone(prev);
      if (!updated.tool_configs) {
        updated.tool_configs = {};
      }
      updated.tool_configs[toolName] = {
        ...updated.tool_configs[toolName],
        ...config,
      };
      return updated;
    });
  };

  // Calculate pending changes
  const pendingChanges = useMemo(() => {
    if (!originalState || !currentState) return [];
    
    const changes = [];
    
    // Check for new, updated, or deleted extensions
    const originalExts = originalState.extensions || {};
    const currentExts = currentState.extensions || {};
    
    // Helper to check if extension is actually installed on disk
    const isInstalledOnDisk = (name) => {
      return installedExtensions.some(ext => ext.name === name);
    };
    
    // New or updated extensions
    Object.keys(currentExts).forEach(name => {
      const existsOnDisk = isInstalledOnDisk(name);
      
      if (!originalExts[name]) {
        // Not in original config at all → install
        changes.push({ type: 'install', target: name });
      } else if (!existsOnDisk) {
        // In config but not on disk → install (even if source changed)
        // This handles reinstalls of extensions that were deleted
        if (currentExts[name].source !== originalExts[name].source) {
          changes.push({ type: 'install', target: name });
        }
      } else if (currentExts[name].source !== originalExts[name].source) {
        // On disk and source changed → update
        changes.push({ type: 'update', target: name });
      } else if (currentExts[name].enabled !== originalExts[name].enabled) {
        changes.push({ type: 'config', target: name, detail: 'enabled status' });
      }
    });
    
    // Deleted extensions
    Object.keys(originalExts).forEach(name => {
      if (!currentExts[name]) {
        changes.push({ type: 'delete', target: name });
      }
    });
    
    // Tool config changes
    const originalTools = originalState.tool_configs || {};
    const currentTools = currentState.tool_configs || {};
    
    Object.keys(currentTools).forEach(toolName => {
      const orig = originalTools[toolName];
      const curr = currentTools[toolName];
      
      if (!orig || 
          orig.enabled_in_mcp !== curr.enabled_in_mcp || 
          orig.passthrough !== curr.passthrough) {
        changes.push({ type: 'tool_config', target: toolName });
      }
    });
    
    return changes;
  }, [originalState, currentState, installedExtensions]);

  // Save current state to queue
  const saveToQueue = async () => {
    const operations = [];
    
    // Generate operations from pending changes
    pendingChanges.forEach(change => {
      // Only process install/update/delete operations (not config changes)
      if (change.type === 'install' || change.type === 'update') {
        const extension = currentState.extensions[change.target];
        const source = extension?.source;
        
        // Validate that source exists for install/update operations
        if (!source || source.trim() === '') {
          console.warn(`Skipping ${change.type} for ${change.target}: no source specified`);
          return;
        }
        
        operations.push({
          type: change.type,
          source: source,
          target: change.target,
        });
      } else if (change.type === 'delete') {
        // Delete operations don't need source
        operations.push({
          type: change.type,
          target: change.target,
        });
      }
      // Note: 'config' type changes (like enabled status) are NOT converted to operations
      // They are only reflected in the master_config update
    });
    
    const queue = {
      operations,
      master_config: currentState,
    };
    
    await QueueAPI.save(queue);
    setQueuedState(queue);
    
    return queue;
  };

  // Revert all changes to original state
  const revertChanges = () => {
    setCurrentState(deepClone(originalState));
  };

  // Delete saved queue
  const deleteQueue = async () => {
    await QueueAPI.delete();
    setQueuedState(null);
  };

  const value = {
    originalState,
    currentState,
    queuedState,
    loading,
    pendingChanges,
    updateExtension,
    deleteExtension,
    updateTool,
    saveToQueue,
    revertChanges,
    deleteQueue,
    loadMasterConfig,
    hasChanges: pendingChanges.length > 0,
  };

  return (
    <ConfigContext.Provider value={value}>
      {children}
    </ConfigContext.Provider>
  );
};




