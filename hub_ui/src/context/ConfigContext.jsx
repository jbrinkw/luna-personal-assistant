import React, { createContext, useContext, useState, useEffect, useMemo } from 'react';
import { ConfigAPI, QueueAPI, ExtensionsAPI, CoreAPI } from '../lib/api';
import { deepClone } from '../lib/utils';

const stableStringify = (value) => {
  if (value === null || typeof value !== 'object') {
    return JSON.stringify(value);
  }
  if (Array.isArray(value)) {
    return `[${value.map(item => stableStringify(item)).join(',')}]`;
  }
  const entries = Object.keys(value).sort().map(key => `${JSON.stringify(key)}:${stableStringify(value[key])}`);
  return `{${entries.join(',')}}`;
};

const configsEqual = (a, b) => stableStringify(a) === stableStringify(b);

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
  const [coreUpdateInfo, setCoreUpdateInfo] = useState(null);

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

  const ensureQueueDraft = () => {
    const base = queuedState ? deepClone(queuedState) : {
      operations: [],
      master_config: deepClone(originalState || {}),
    };
    if (!base.master_config) {
      base.master_config = deepClone(originalState || {});
    }
    if (!base.operations) {
      base.operations = [];
    }
    return base;
  };

  const persistQueueState = async (queue) => {
    if (!queue) return null;
    const safeQueue = deepClone(queue);
    safeQueue.operations = safeQueue.operations || [];
    safeQueue.master_config = safeQueue.master_config || {};

    if (
      originalState &&
      configsEqual(safeQueue.master_config, originalState) &&
      safeQueue.operations.length === 0
    ) {
      try {
        await QueueAPI.delete();
        setQueuedState(null);
      } catch (error) {
        console.error('Failed to delete empty queue:', error);
        throw error;
      }
      return null;
    }

    safeQueue.created_at = new Date().toISOString();
    await QueueAPI.save(safeQueue);
    setQueuedState(safeQueue);
    return safeQueue;
  };

  const revertChangeInCurrentState = (change) => {
    setCurrentState(prev => {
      if (!prev) return prev;
      const updated = deepClone(prev);
      switch (change.type) {
        case 'install':
        case 'update':
        case 'config': {
          if (originalState?.extensions?.[change.target]) {
            if (!updated.extensions) {
              updated.extensions = {};
            }
            updated.extensions[change.target] = deepClone(originalState.extensions[change.target]);
          } else if (updated.extensions) {
            delete updated.extensions[change.target];
            if (Object.keys(updated.extensions).length === 0) {
              delete updated.extensions;
            }
          }
          break;
        }
        case 'delete': {
          if (!updated.extensions) {
            updated.extensions = {};
          }
          if (originalState?.extensions?.[change.target]) {
            updated.extensions[change.target] = deepClone(originalState.extensions[change.target]);
          }
          break;
        }
        case 'tool_config': {
          if (!updated.tool_configs) {
            updated.tool_configs = {};
          }
          if (originalState?.tool_configs?.[change.target]) {
            updated.tool_configs[change.target] = deepClone(originalState.tool_configs[change.target]);
          } else if (updated.tool_configs) {
            delete updated.tool_configs[change.target];
            if (Object.keys(updated.tool_configs).length === 0) {
              delete updated.tool_configs;
            }
          }
          break;
        }
        case 'update_core': {
          if (updated.luna) {
            delete updated.luna.pending_update;
            if (Object.keys(updated.luna).length === 0) {
              delete updated.luna;
            }
          }
          break;
        }
        default:
          break;
      }
      return updated;
    });
  };

  const applySavedChangeToCurrentState = (change, sourceState) => {
    setCurrentState(prev => {
      const base = prev ? deepClone(prev) : deepClone(originalState || {});
      switch (change.type) {
        case 'install':
        case 'update':
        case 'config': {
          const extData = sourceState?.extensions?.[change.target];
          if (!extData) return base;
          if (!base.extensions) {
            base.extensions = {};
          }
          base.extensions[change.target] = deepClone(extData);
          return base;
        }
        case 'delete': {
          if (base.extensions) {
            delete base.extensions[change.target];
            if (Object.keys(base.extensions).length === 0) {
              delete base.extensions;
            }
          }
          return base;
        }
        case 'tool_config': {
          const toolData = sourceState?.tool_configs?.[change.target];
          if (!base.tool_configs) {
            base.tool_configs = {};
          }
          if (toolData) {
            base.tool_configs[change.target] = deepClone(toolData);
          } else {
            delete base.tool_configs[change.target];
          }
          if (base.tool_configs && Object.keys(base.tool_configs).length === 0) {
            delete base.tool_configs;
          }
          return base;
        }
        case 'update_core': {
          const version = sourceState?.luna?.pending_update || change.detail;
          if (!base.luna) {
            base.luna = deepClone(originalState?.luna || {});
          }
          if (version) {
            base.luna.pending_update = version;
          } else if (base.luna) {
            delete base.luna.pending_update;
          }
          return base;
        }
        default:
          return base;
      }
    });
  };

  const stageChangeToQueue = async (change) => {
    if (!originalState || !currentState) return null;
    try {
      const queue = ensureQueueDraft();
      const master = deepClone(queue.master_config || {});
      queue.operations = queue.operations || [];

      const removeOpsForTarget = (target) => {
        queue.operations = queue.operations.filter(op => op.target !== target);
      };

      if (change.type === 'install' || change.type === 'update') {
        const extension = currentState.extensions?.[change.target];
        if (!extension) {
          console.warn(`Cannot stage ${change.type} for ${change.target}: missing extension`);
          return null;
        }
        removeOpsForTarget(change.target);
        queue.operations.push({
          type: change.type,
          target: change.target,
          source: extension.source,
        });
        if (!master.extensions) {
          master.extensions = {};
        }
        master.extensions[change.target] = deepClone(extension);
      } else if (change.type === 'delete') {
        removeOpsForTarget(change.target);
        queue.operations.push({
          type: 'delete',
          target: change.target,
        });
        if (master.extensions) {
          delete master.extensions[change.target];
          if (Object.keys(master.extensions).length === 0) {
            delete master.extensions;
          }
        }
      } else if (change.type === 'config') {
        const extension = currentState.extensions?.[change.target];
        if (extension) {
          if (!master.extensions) {
            master.extensions = {};
          }
          master.extensions[change.target] = deepClone(extension);
        }
      } else if (change.type === 'tool_config') {
        const toolConfig = currentState.tool_configs?.[change.target];
        if (!master.tool_configs) {
          master.tool_configs = {};
        }
        if (toolConfig) {
          master.tool_configs[change.target] = deepClone(toolConfig);
        } else {
          delete master.tool_configs[change.target];
          if (Object.keys(master.tool_configs).length === 0) {
            delete master.tool_configs;
          }
        }
      } else if (change.type === 'update_core') {
        const version = currentState.luna?.pending_update;
        if (!version) {
          console.warn('No pending core update to stage');
          return null;
        }
        queue.operations = queue.operations.filter(op => op.type !== 'update_core');
        queue.operations.push({
          type: 'update_core',
          target_version: version,
        });
        if (!master.luna) {
          master.luna = deepClone(originalState?.luna || {});
        }
        master.luna.pending_update = version;
      } else {
        console.warn('Unknown change type:', change.type);
        return null;
      }

      queue.master_config = master;
      const result = await persistQueueState(queue);
      revertChangeInCurrentState(change);
      return result;
    } catch (error) {
      console.error('Failed to stage change:', error);
      throw error;
    }
  };

  const unstageQueueItem = async (change) => {
    if (!queuedState || !originalState) return null;
    try {
      const queue = deepClone(queuedState);
      const master = deepClone(queue.master_config || {});
      const stagedMaster = queuedState.master_config || {};
      queue.operations = queue.operations || [];

      const removeOpsForTarget = (target) => {
        queue.operations = queue.operations.filter(op => op.target !== target);
      };

      if (change.type === 'install' || change.type === 'update') {
        const stagedExtension = stagedMaster.extensions?.[change.target];
        removeOpsForTarget(change.target);
        if (master.extensions) {
          if (originalState.extensions?.[change.target]) {
            master.extensions[change.target] = deepClone(originalState.extensions[change.target]);
          } else {
            delete master.extensions[change.target];
            if (Object.keys(master.extensions).length === 0) {
              delete master.extensions;
            }
          }
        }
        queue.master_config = master;
        const result = await persistQueueState(queue);
        if (stagedExtension) {
          applySavedChangeToCurrentState(change, stagedMaster);
        }
        return result;
      } else if (change.type === 'delete') {
        removeOpsForTarget(change.target);
        if (!master.extensions) {
          master.extensions = {};
        }
        if (originalState.extensions?.[change.target]) {
          master.extensions[change.target] = deepClone(originalState.extensions[change.target]);
        }
        queue.master_config = master;
        const result = await persistQueueState(queue);
        setCurrentState(prev => {
          if (!prev) return prev;
          const updated = deepClone(prev);
          if (updated.extensions) {
            delete updated.extensions[change.target];
            if (Object.keys(updated.extensions).length === 0) {
              delete updated.extensions;
            }
          }
          return updated;
        });
        return result;
      } else if (change.type === 'config') {
        if (master.extensions && originalState.extensions?.[change.target]) {
          master.extensions[change.target] = deepClone(originalState.extensions[change.target]);
        }
        queue.master_config = master;
        const result = await persistQueueState(queue);
        applySavedChangeToCurrentState(change, stagedMaster);
        return result;
      } else if (change.type === 'tool_config') {
        if (master.tool_configs) {
          if (originalState.tool_configs?.[change.target]) {
            master.tool_configs[change.target] = deepClone(originalState.tool_configs[change.target]);
          } else {
            delete master.tool_configs[change.target];
          }
          if (Object.keys(master.tool_configs).length === 0) {
            delete master.tool_configs;
          }
        }
        queue.master_config = master;
        const result = await persistQueueState(queue);
        applySavedChangeToCurrentState(change, stagedMaster);
        return result;
      } else if (change.type === 'update_core') {
        const stagedVersion = stagedMaster.luna?.pending_update || change.detail;
        queue.operations = queue.operations.filter(op => op.type !== 'update_core');
        if (master.luna) {
          delete master.luna.pending_update;
          if (Object.keys(master.luna).length === 0) {
            delete master.luna;
          }
        }
        queue.master_config = master;
        const result = await persistQueueState(queue);
        if (stagedVersion) {
          applySavedChangeToCurrentState({ type: 'update_core', detail: stagedVersion }, { luna: { pending_update: stagedVersion } });
        }
        return result;
      }

      console.warn('Unknown queued change type:', change.type);
      return null;
    } catch (error) {
      console.error('Failed to unstage queued item:', error);
      throw error;
    }
  };

  const checkForCoreUpdates = async () => {
    try {
      const result = await CoreAPI.checkUpdates();
      setCoreUpdateInfo(result);
      if (result.update_available) {
        const targetVersion = result.remote?.version || result.remote?.commit;
        if (targetVersion && currentState?.luna?.pending_update !== targetVersion) {
          addCoreUpdate(targetVersion);
        }
      }
      return result;
    } catch (error) {
      console.error('Failed to check core updates:', error);
      setCoreUpdateInfo({ error: error.message });
      throw error;
    }
  };

  const clearCoreUpdateInfo = () => {
    setCoreUpdateInfo(null);
  };

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

      if (config === null) {
        if (updated.tool_configs[toolName]) {
          delete updated.tool_configs[toolName];
        }
        if (Object.keys(updated.tool_configs).length === 0) {
          delete updated.tool_configs;
        }
        return updated;
      }

      updated.tool_configs[toolName] = deepClone(config);
      return updated;
    });
  };

  // Add core update to current state
  const addCoreUpdate = (targetVersion) => {
    if (!targetVersion) return;
    setCurrentState(prev => {
      const updated = deepClone(prev);
      if (!updated.luna) {
        updated.luna = deepClone(originalState?.luna || {});
      }
      updated.luna.pending_update = targetVersion;
      return updated;
    });
  };

  // Remove core update from current state
  const removeCoreUpdate = () => {
    setCurrentState(prev => {
      const updated = deepClone(prev);
      if (updated.luna && updated.luna.pending_update) {
        delete updated.luna.pending_update;
      }
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
    
    // Core update check
    const currentPendingUpdate = currentState.luna?.pending_update;
    if (currentPendingUpdate) {
      changes.push({ 
        type: 'update_core', 
        target: 'Luna Core',
        detail: currentPendingUpdate 
      });
    }
    
    return changes;
  }, [originalState, currentState, installedExtensions]);

  // Save current state to queue
  const saveToQueue = async () => {
    const operations = [];
    
    // Generate operations from pending changes
    pendingChanges.forEach(change => {
      if (change.type === 'install' || change.type === 'update') {
        const extension = currentState.extensions[change.target];
        const source = extension?.source;
        
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
        operations.push({
          type: change.type,
          target: change.target,
        });
      } else if (change.type === 'update_core') {
        operations.push({
          type: 'update_core',
          target_version: change.detail,
        });
      }
    });
    
    const queue = {
      operations,
      master_config: deepClone(currentState),
    };
    
    const saved = await persistQueueState(queue);
    return saved || queue;
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
    addCoreUpdate,
    removeCoreUpdate,
    stageChangeToQueue,
    unstageQueueItem,
    saveToQueue,
    revertChanges,
    deleteQueue,
    checkForCoreUpdates,
    clearCoreUpdateInfo,
    coreUpdateInfo,
    loadMasterConfig,
    hasChanges: pendingChanges.length > 0,
  };

  return (
    <ConfigContext.Provider value={value}>
      {children}
    </ConfigContext.Provider>
  );
};



