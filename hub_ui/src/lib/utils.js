// Deep clone helper
export function deepClone(obj) {
  return JSON.parse(JSON.stringify(obj));
}

// Mask secret values (show first 4 and last 4 chars)
export function maskValue(value) {
  if (!value || value.length < 12) {
    return '********';
  }
  return `${value.substring(0, 4)}...${value.substring(value.length - 4)}`;
}

// Format date to relative time (e.g., "2m ago", "1h ago")
export function formatRelativeTime(timestamp) {
  const now = Date.now();
  const diff = now - timestamp;
  
  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(diff / 3600000);
  const days = Math.floor(diff / 86400000);
  
  if (minutes < 1) return 'just now';
  if (minutes < 60) return `${minutes}m ago`;
  if (hours < 24) return `${hours}h ago`;
  return `${days}d ago`;
}

// Format uptime in human-readable form
export function formatUptime(seconds) {
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  
  if (days > 0) return `${days}d ${hours}h`;
  if (hours > 0) return `${hours}h ${minutes}m`;
  return `${minutes}m`;
}

// Validate environment variable key format
export function validateKeyFormat(key) {
  return /^[A-Z_][A-Z0-9_]*$/.test(key);
}

// Compare versions (MM-DD-YY format)
export function compareVersions(v1, v2) {
  if (!v1 || !v2) return 0;
  
  try {
    const [m1, d1, y1] = v1.split('-').map(Number);
    const [m2, d2, y2] = v2.split('-').map(Number);
    
    const date1 = new Date(2000 + y1, m1 - 1, d1);
    const date2 = new Date(2000 + y2, m2 - 1, d2);
    
    return date1 - date2;
  } catch (error) {
    return 0;
  }
}

// Check if version1 is newer than version2
export function isNewerVersion(v1, v2) {
  return compareVersions(v1, v2) > 0;
}

// Debounce function for search inputs
export function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

// Activity tracking helpers
const ACTIVITY_STORAGE_KEY = 'luna_activity_log';
const MAX_ACTIVITIES = 50;

export function addActivity(type, message) {
  const activities = getActivities();
  activities.unshift({
    id: Date.now(),
    type,
    message,
    timestamp: Date.now(),
  });
  
  // Keep only last MAX_ACTIVITIES
  if (activities.length > MAX_ACTIVITIES) {
    activities.splice(MAX_ACTIVITIES);
  }
  
  localStorage.setItem(ACTIVITY_STORAGE_KEY, JSON.stringify(activities));
}

export function getActivities(limit = 10) {
  try {
    const stored = localStorage.getItem(ACTIVITY_STORAGE_KEY);
    const activities = stored ? JSON.parse(stored) : [];
    return activities.slice(0, limit);
  } catch (error) {
    return [];
  }
}

export function clearActivities() {
  localStorage.removeItem(ACTIVITY_STORAGE_KEY);
}




