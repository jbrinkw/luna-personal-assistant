import React, { createContext, useContext, useState, useEffect } from 'react';
import { SystemAPI } from '../lib/api';

const SystemContext = createContext();

export const useSystem = () => {
  const context = useContext(SystemContext);
  if (!context) {
    throw new Error('useSystem must be used within SystemProvider');
  }
  return context;
};

export const SystemProvider = ({ children }) => {
  const [health, setHealth] = useState('checking');
  const [version, setVersion] = useState('unknown');
  const [uptime, setUptime] = useState(0);
  const [ports, setPorts] = useState({ core: {}, extensions: {}, services: {} });

  const refreshHealth = async () => {
    const isHealthy = await SystemAPI.health();
    setHealth(isHealthy ? 'online' : 'offline');
  };

  const loadSystemInfo = async () => {
    try {
      const portsData = await SystemAPI.getPorts();
      setPorts(portsData);
    } catch (error) {
      console.error('Failed to load system info:', error);
    }
  };

  useEffect(() => {
    // Initial load
    refreshHealth();
    loadSystemInfo();

    // Poll health every 10 seconds
    const healthInterval = setInterval(refreshHealth, 10000);

    // Update system info every 30 seconds
    const infoInterval = setInterval(loadSystemInfo, 30000);

    return () => {
      clearInterval(healthInterval);
      clearInterval(infoInterval);
    };
  }, []);

  const value = {
    health,
    version,
    uptime,
    ports,
    refreshHealth,
    loadSystemInfo,
  };

  return (
    <SystemContext.Provider value={value}>
      {children}
    </SystemContext.Provider>
  );
};




