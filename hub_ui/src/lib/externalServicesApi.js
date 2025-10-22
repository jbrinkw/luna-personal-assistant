/**
 * External Services API Client
 * Handles all API calls for external services management
 */

// Use relative paths - all requests go through Caddy reverse proxy
const API_BASE = '/api/supervisor';

/**
 * Generic API call handler with error handling
 */
async function apiCall(endpoint, options = {}) {
  try {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || `Request failed with status ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error(`API call failed: ${endpoint}`, error);
    throw error;
  }
}

/**
 * Get list of all available service definitions from external_services/
 * @returns {Promise<Object>} Object with services array
 */
export async function getAvailableServices() {
  return apiCall('/api/external-services/available');
}

/**
 * Install a service with given configuration
 * @param {string} name - Service name
 * @param {Object} config - Configuration object
 * @returns {Promise<Object>} Installation result
 */
export async function installService(name, config) {
  return apiCall(`/api/external-services/${name}/install`, {
    method: 'POST',
    body: JSON.stringify({ config }),
  });
}

/**
 * Get registry contents with current statuses
 * @returns {Promise<Object>} Registry object mapping service names to data
 */
export async function getInstalledServices() {
  return apiCall('/api/external-services/installed');
}

/**
 * Get service definition, config form, installation status, and saved config
 * @param {string} name - Service name
 * @returns {Promise<Object>} Service details
 */
export async function getServiceDetails(name) {
  return apiCall(`/api/external-services/${name}`);
}

/**
 * Uninstall a service
 * @param {string} name - Service name
 * @param {boolean} removeData - Whether to remove data volumes
 * @returns {Promise<Object>} Uninstallation result
 */
export async function uninstallService(name, removeData = true) {
  return apiCall(`/api/external-services/${name}/uninstall`, {
    method: 'POST',
    body: JSON.stringify({ remove_data: removeData }),
  });
}

/**
 * Start a service
 * @param {string} name - Service name
 * @returns {Promise<Object>} Start result with status
 */
export async function startService(name) {
  return apiCall(`/api/external-services/${name}/start`, {
    method: 'POST',
  });
}

/**
 * Stop a service
 * @param {string} name - Service name
 * @returns {Promise<Object>} Stop result with status
 */
export async function stopService(name) {
  return apiCall(`/api/external-services/${name}/stop`, {
    method: 'POST',
  });
}

/**
 * Restart a service
 * @param {string} name - Service name
 * @returns {Promise<Object>} Restart result with status
 */
export async function restartService(name) {
  return apiCall(`/api/external-services/${name}/restart`, {
    method: 'POST',
  });
}

/**
 * Enable auto-start on boot for a service
 * @param {string} name - Service name
 * @returns {Promise<Object>} Enable result
 */
export async function enableService(name) {
  return apiCall(`/api/external-services/${name}/enable`, {
    method: 'POST',
  });
}

/**
 * Disable auto-start on boot for a service
 * @param {string} name - Service name
 * @returns {Promise<Object>} Disable result
 */
export async function disableService(name) {
  return apiCall(`/api/external-services/${name}/disable`, {
    method: 'POST',
  });
}

/**
 * Get current status of a service
 * @param {string} name - Service name
 * @returns {Promise<Object>} Status object
 */
export async function getServiceStatus(name) {
  return apiCall(`/api/external-services/${name}/status`);
}

/**
 * Get last N lines from service log file
 * @param {string} name - Service name
 * @param {number} lines - Number of lines to retrieve (default: 100)
 * @returns {Promise<Object>} Log content and path
 */
export async function getServiceLogs(name, lines = 100) {
  return apiCall(`/api/external-services/${name}/logs?lines=${lines}`);
}

/**
 * Upload a new external service definition
 * @param {Object} serviceDefinition - Service definition object
 * @returns {Promise<Object>} Upload result
 */
export async function uploadService(serviceDefinition) {
  return apiCall('/api/external-services/upload', {
    method: 'POST',
    body: JSON.stringify({ service_definition: serviceDefinition }),
  });
}

