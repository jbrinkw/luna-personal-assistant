// Use relative paths - all requests go through Caddy reverse proxy
const SUPERVISOR_API = '/api/supervisor';
const AGENT_API = '/api/agent';

// Helper for fetch with error handling
async function fetchJSON(url, options = {}) {
  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('API Error:', error);
    throw error;
  }
}

export const ConfigAPI = {
  getMaster: () => fetchJSON(`${SUPERVISOR_API}/config/master`),
  
  getExtension: (name) => fetchJSON(`${SUPERVISOR_API}/config/extension/${name}`),
  
  updateMaster: (config) => fetchJSON(`${SUPERVISOR_API}/config/master`, {
    method: 'PUT',
    body: JSON.stringify(config),
  }),
  
  updateExtension: (name, data) => fetchJSON(`${SUPERVISOR_API}/config/master/extensions/${name}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }),
  
  updateTool: (toolName, config) => fetchJSON(`${SUPERVISOR_API}/config/master/tool/${toolName}`, {
    method: 'PATCH',
    body: JSON.stringify(config),
  }),
  
  syncConfig: () => fetchJSON(`${SUPERVISOR_API}/config/sync`, {
    method: 'POST',
  }),
};

export const ExtensionsAPI = {
  // Use Supervisor API for extensions list (has correct port info)
  list: () => fetchJSON(`${SUPERVISOR_API}/extensions`),
  
  getStatus: (name) => fetchJSON(`${SUPERVISOR_API}/extensions`).then(data => 
    data.extensions.find(ext => ext.name === name) || null
  ),
  
  upload: async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await fetch(`${SUPERVISOR_API}/extensions/upload`, {
      method: 'POST',
      body: formData,
    });
    
    if (!response.ok) {
      throw new Error(`Upload failed: ${response.statusText}`);
    }
    
    return await response.json();
  },
  
  restartUI: (name) => fetchJSON(`${AGENT_API}/extensions/${name}/ui/restart`, {
    method: 'POST',
  }),
};

export const QueueAPI = {
  getCurrent: async () => {
    try {
      return await fetchJSON(`${SUPERVISOR_API}/queue/current`);
    } catch (error) {
      // Queue might not exist, return null
      return null;
    }
  },
  
  save: (queue) => fetchJSON(`${SUPERVISOR_API}/queue/save`, {
    method: 'POST',
    body: JSON.stringify(queue),
  }),
  
  delete: () => fetchJSON(`${SUPERVISOR_API}/queue/current`, {
    method: 'DELETE',
  }),
  
  status: () => fetchJSON(`${SUPERVISOR_API}/queue/status`),
};

export const ServicesAPI = {
  getStatus: () => fetchJSON(`${SUPERVISOR_API}/services/status`),
  
  restart: (name, service) => fetchJSON(`${AGENT_API}/extensions/${name}/services/${service}/restart`, {
    method: 'POST',
  }),
  
  start: (name, service) => fetchJSON(`${SUPERVISOR_API}/services/${name}.${service}/start`, {
    method: 'POST',
  }),
  
  stop: (name, service) => fetchJSON(`${SUPERVISOR_API}/services/${name}.${service}/stop`, {
    method: 'POST',
  }),
};

export const ToolsAPI = {
  discover: (extension = null) => {
    const url = extension 
      ? `${SUPERVISOR_API}/tools/discover?extension=${extension}`
      : `${SUPERVISOR_API}/tools/discover`;
    return fetchJSON(url);
  },
  
  list: (options = {}) => {
    const params = new URLSearchParams(options);
    return fetchJSON(`${SUPERVISOR_API}/tools/list?${params}`);
  },
  
  validate: (toolName, args) => fetchJSON(`${SUPERVISOR_API}/tools/validate/${toolName}`, {
    method: 'POST',
    body: JSON.stringify(args),
  }),
  
  execute: (toolName, args) => fetchJSON(`${SUPERVISOR_API}/tools/execute/${toolName}`, {
    method: 'POST',
    body: JSON.stringify(args),
  }),
};

export const KeysAPI = {
  list: async () => {
    try {
      return await fetchJSON(`${SUPERVISOR_API}/keys/list`);
    } catch (error) {
      return {};
    }
  },
  
  set: (key, value) => fetchJSON(`${SUPERVISOR_API}/keys/set`, {
    method: 'POST',
    body: JSON.stringify({ key, value }),
  }),
  
  delete: (key) => fetchJSON(`${SUPERVISOR_API}/keys/delete`, {
    method: 'POST',
    body: JSON.stringify({ key }),
  }),
  
  uploadEnv: async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await fetch(`${SUPERVISOR_API}/keys/upload-env`, {
      method: 'POST',
      body: formData,
    });
    
    if (!response.ok) {
      throw new Error(`Upload failed: ${response.statusText}`);
    }
    
    return await response.json();
  },
  
  required: () => fetchJSON(`${SUPERVISOR_API}/keys/required`),
};

export const SystemAPI = {
  health: async () => {
    try {
      const response = await fetch(`${SUPERVISOR_API}/health`);
      return response.ok;
    } catch (error) {
      return false;
    }
  },
  
  restart: () => fetchJSON(`${SUPERVISOR_API}/restart`, {
    method: 'POST',
  }),
  
  shutdown: () => fetchJSON(`${SUPERVISOR_API}/shutdown`, {
    method: 'POST',
  }),
  
  getPorts: () => fetchJSON(`${SUPERVISOR_API}/ports`),
  
  getModels: () => fetchJSON(`${AGENT_API}/v1/models`),
};

export const CoreAPI = {
  checkUpdates: () => fetchJSON(`${SUPERVISOR_API}/core/check-updates`, {
    method: 'POST',
  }),
};
