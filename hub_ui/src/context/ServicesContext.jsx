import React, { createContext, useContext, useState, useEffect } from 'react';
import { ServicesAPI, ExtensionsAPI } from '../lib/api';

const ServicesContext = createContext();

export const useServices = () => {
  const context = useContext(ServicesContext);
  if (!context) {
    throw new Error('useServices must be used within ServicesProvider');
  }
  return context;
};

export const ServicesProvider = ({ children }) => {
  const [services, setServices] = useState({});
  const [extensions, setExtensions] = useState([]);
  const [loading, setLoading] = useState(true);

  const refreshServices = async () => {
    try {
      const servicesData = await ServicesAPI.getStatus();
      setServices(servicesData.services || {});
    } catch (error) {
      console.error('Failed to refresh services:', error);
      setServices({});
    }
  };

  const refreshExtensions = async () => {
    try {
      const data = await ExtensionsAPI.list();
      setExtensions(Array.isArray(data.extensions) ? data.extensions : []);
    } catch (error) {
      console.error('Failed to refresh extensions:', error);
      setExtensions([]);
    }
  };

  const refresh = async () => {
    setLoading(true);
    await Promise.all([refreshServices(), refreshExtensions()]);
    setLoading(false);
  };

  useEffect(() => {
    // Initial load
    refresh();

    // Poll every 30 seconds
    const interval = setInterval(refresh, 30000);

    return () => clearInterval(interval);
  }, []);

  const restartService = async (extensionName, serviceName) => {
    try {
      await ServicesAPI.restart(extensionName, serviceName);
      // Refresh after a short delay to allow restart
      setTimeout(refreshServices, 2000);
    } catch (error) {
      console.error('Failed to restart service:', error);
      throw error;
    }
  };

  const startService = async (extensionName, serviceName) => {
    try {
      await ServicesAPI.start(extensionName, serviceName);
      setTimeout(refreshServices, 2000);
    } catch (error) {
      console.error('Failed to start service:', error);
      throw error;
    }
  };

  const stopService = async (extensionName, serviceName) => {
    try {
      await ServicesAPI.stop(extensionName, serviceName);
      setTimeout(refreshServices, 2000);
    } catch (error) {
      console.error('Failed to stop service:', error);
      throw error;
    }
  };

  const restartUI = async (extensionName) => {
    try {
      await ExtensionsAPI.restartUI(extensionName);
      setTimeout(refreshExtensions, 2000);
    } catch (error) {
      console.error('Failed to restart UI:', error);
      throw error;
    }
  };

  const value = {
    services,
    extensions,
    loading,
    refreshServices,
    refreshExtensions,
    refresh,
    restartService,
    startService,
    stopService,
    restartUI,
  };

  return (
    <ServicesContext.Provider value={value}>
      {children}
    </ServicesContext.Provider>
  );
};



