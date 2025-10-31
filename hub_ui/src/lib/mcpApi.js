// MCP API - Remote MCP Server Management
const SUPERVISOR_API = '/api/supervisor';

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
      const errorText = await response.text();
      throw new Error(`HTTP ${response.status}: ${errorText || response.statusText}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('MCP API Error:', error);
    throw error;
  }
}

export const MCPApi = {
  // Add or update a remote MCP server
  async addServer(url) {
    return fetchJSON(`${SUPERVISOR_API}/remote-mcp/add`, {
      method: 'POST',
      body: JSON.stringify({ url }),
    });
  },
  
  // List all remote MCP servers
  async listServers() {
    return fetchJSON(`${SUPERVISOR_API}/remote-mcp/list`);
  },
  
  // Update server or tool enabled status
  async updateServer(serverId, updates) {
    return fetchJSON(`${SUPERVISOR_API}/remote-mcp/${encodeURIComponent(serverId)}`, {
      method: 'PATCH',
      body: JSON.stringify(updates),
    });
  },
  
  // Delete a remote MCP server
  async deleteServer(serverId) {
    return fetchJSON(`${SUPERVISOR_API}/remote-mcp/${encodeURIComponent(serverId)}`, {
      method: 'DELETE',
    });
  },
  
  // Get all tools from all sources
  async getAllTools() {
    return fetchJSON(`${SUPERVISOR_API}/tools/all`);
  },
};

