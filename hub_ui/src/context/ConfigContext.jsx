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
  const [queuedState, setQueuedState] = useState(null);
  const [installedExtensions, setInstalledExtensions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [coreUpdateInfo, setCoreUpdateInfo] = useState(null);

  // Load master config from server
  const loadMasterConfig = async () => {
    try {
      setLoading(true);
      const config = await ConfigAPI.getMaster();
      
      // If there's a stale pending_update in the config, validate it
      if (config.luna?.pending_update) {
        try {
          const updateCheck = await CoreAPI.checkUpdates();
          if (!updateCheck.update_available) {
            // Core is up to date, remove the stale pending_update
            console.log('Removing stale pending_update from master config');
            if (config.luna) {
              delete config.luna.pending_update;
              if (Object.keys(config.luna).length === 0) {
                delete config.luna;
              }
            }
            // Save the cleaned config back to the server
            await ConfigAPI.updateMaster(config);
          }
        } catch (error) {
          console.warn('Failed to validate pending_update on load:', error);
        }
      }
      
      setOriginalState(config);
      
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

    // If queue is effectively empty, delete it
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


  const checkForCoreUpdates = async () => {
    try {
      const result = await CoreAPI.checkUpdates();
      setCoreUpdateInfo(result);
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

  // Update extension - immediately persists to queue
  const updateExtension = async (name, data) => {
    try {
      const queue = ensureQueueDraft();
      const master = queue.master_config;
      
      if (!master.extensions) {
        master.extensions = {};
      }
      
      if (!master.extensions[name]) {
        master.extensions[name] = {};
      }
      
      master.extensions[name] = {
        ...master.extensions[name],
        ...data,
      };

      // Determine operation type
      const originalExt = originalState?.extensions?.[name];
      const isInstalledOnDisk = installedExtensions.some(ext => ext.name === name);
      
      // Remove any existing operations for this extension
      queue.operations = queue.operations.filter(op => op.target !== name);
      
      if (!originalExt) {
        // New extension - install operation
        if (master.extensions[name].source) {
          queue.operations.push({
            type: 'install',
            target: name,
            source: master.extensions[name].source,
          });
        }
      } else if (!isInstalledOnDisk || master.extensions[name].source !== originalExt.source) {
        // Source changed or not on disk - install/update operation
        if (master.extensions[name].source) {
          queue.operations.push({
            type: isInstalledOnDisk ? 'update' : 'install',
            target: name,
            source: master.extensions[name].source,
          });
        }
      }
      
      await persistQueueState(queue);
    } catch (error) {
      console.error('Failed to update extension:', error);
      throw error;
    }
  };

  // Delete extension - immediately persists to queue
  const deleteExtension = async (name) => {
    try {
      const queue = ensureQueueDraft();
      const master = queue.master_config;
      
      if (master.extensions && master.extensions[name]) {
        delete master.extensions[name];
        if (Object.keys(master.extensions).length === 0) {
          delete master.extensions;
        }
      }
      
      // Remove any existing operations for this extension
      queue.operations = queue.operations.filter(op => op.target !== name);
      
      // Add delete operation if extension exists in original state
      if (originalState?.extensions?.[name]) {
        queue.operations.push({
          type: 'delete',
          target: name,
        });
      }
      
      await persistQueueState(queue);
    } catch (error) {
      console.error('Failed to delete extension:', error);
      throw error;
    }
  };

  // Update tool config - immediately persists to queue
  const updateTool = async (toolName, config) => {
    try {
      const queue = ensureQueueDraft();
      const master = queue.master_config;
      
      if (!master.tool_configs) {
        master.tool_configs = {};
      }

      if (config === null) {
        if (master.tool_configs[toolName]) {
          delete master.tool_configs[toolName];
        }
        if (Object.keys(master.tool_configs).length === 0) {
          delete master.tool_configs;
        }
      } else {
        master.tool_configs[toolName] = deepClone(config);
      }
      
      await persistQueueState(queue);
    } catch (error) {
      console.error('Failed to update tool config:', error);
      throw error;
    }
  };

  // Add core update - immediately persists to queue
  const addCoreUpdate = async (targetVersion) => {
    if (!targetVersion) return;
    try {
      const queue = ensureQueueDraft();
      const master = queue.master_config;
      
      if (!master.luna) {
        master.luna = deepClone(originalState?.luna || {});
      }
      master.luna.pending_update = targetVersion;
      
      // Remove any existing core update operations
      queue.operations = queue.operations.filter(op => op.type !== 'update_core');
      
      // Add new core update operation
      queue.operations.push({
        type: 'update_core',
        target_version: targetVersion,
      });
      
      await persistQueueState(queue);
    } catch (error) {
      console.error('Failed to add core update:', error);
      throw error;
    }
  };

  // Remove core update - immediately persists to queue
  const removeCoreUpdate = async () => {
    try {
      const queue = ensureQueueDraft();
      const master = queue.master_config;
      
      if (master.luna && master.luna.pending_update) {
        delete master.luna.pending_update;
        if (Object.keys(master.luna).length === 0) {
          delete master.luna;
        }
      }
      
      // Remove core update operation
      queue.operations = queue.operations.filter(op => op.type !== 'update_core');
      
      await persistQueueState(queue);
    } catch (error) {
      console.error('Failed to remove core update:', error);
      throw error;
    }
  };

  // Remove individual item from queue - immediately persists
  const removeQueueItem = async (operation) => {
    if (!queuedState) return;
    try {
      const queue = deepClone(queuedState);
      const master = queue.master_config;
      
      // Remove the operation from the operations array
      if (operation.type === 'update_core') {
        queue.operations = queue.operations.filter(op => op.type !== 'update_core');
        // Revert master_config luna.pending_update
        if (master.luna) {
          delete master.luna.pending_update;
          if (Object.keys(master.luna).length === 0) {
            delete master.luna;
          }
        }
      } else {
        // For extension operations, filter by target
        queue.operations = queue.operations.filter(op => 
          !(op.target === operation.target && op.type === operation.type)
        );
        
        // Revert master_config to original state for this extension
        const target = operation.target;
        if (operation.type === 'delete') {
          // Restore deleted extension
          if (originalState?.extensions?.[target]) {
            if (!master.extensions) {
              master.extensions = {};
            }
            master.extensions[target] = deepClone(originalState.extensions[target]);
          }
        } else if (operation.type === 'install') {
          // Remove installed extension from master config if not in original
          if (!originalState?.extensions?.[target]) {
            if (master.extensions) {
              delete master.extensions[target];
              if (Object.keys(master.extensions).length === 0) {
                delete master.extensions;
              }
            }
          } else {
            // Restore to original
            master.extensions[target] = deepClone(originalState.extensions[target]);
          }
        } else if (operation.type === 'update') {
          // Restore to original state
          if (originalState?.extensions?.[target]) {
            master.extensions[target] = deepClone(originalState.extensions[target]);
          }
        }
      }
      
      await persistQueueState(queue);
    } catch (error) {
      console.error('Failed to remove queue item:', error);
      throw error;
    }
  };

  // Delete saved queue
  const deleteQueue = async () => {
    await QueueAPI.delete();
    setQueuedState(null);
  };

  const value = {
    originalState,
    queuedState,
    loading,
    updateExtension,
    deleteExtension,
    updateTool,
    addCoreUpdate,
    removeCoreUpdate,
    removeQueueItem,
    deleteQueue,
    checkForCoreUpdates,
    clearCoreUpdateInfo,
    coreUpdateInfo,
    loadMasterConfig,
  };

  return (
    <ConfigContext.Provider value={value}>
      {children}
    </ConfigContext.Provider>
  );
};



