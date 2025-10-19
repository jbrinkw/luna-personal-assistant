import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useConfig } from '../context/ConfigContext';
import { useServices } from '../context/ServicesContext';
import { ToolsAPI, ConfigAPI, ServicesAPI } from '../lib/api';
import Button from '../components/common/Button';
import StatusIndicator from '../components/common/StatusIndicator';
import LoadingSpinner from '../components/common/LoadingSpinner';

export default function ExtensionDetail() {
  const { name } = useParams();
  const navigate = useNavigate();
  const { currentState, updateTool } = useConfig();
  const { extensions, restartService } = useServices();
  
  const [activeTab, setActiveTab] = useState('tools');
  const [tools, setTools] = useState([]);
  const [extConfig, setExtConfig] = useState(null);
  const [loading, setLoading] = useState(true);

  const extension = extensions.find(ext => ext.name === name);

  useEffect(() => {
    loadExtensionData();
  }, [name]);

  const loadExtensionData = async () => {
    try {
      setLoading(true);
      const [toolsData, configData] = await Promise.all([
        ToolsAPI.discover(name).catch(() => ({ tools: [] })),
        ConfigAPI.getExtension(name).catch(() => null),
      ]);
      
      setTools(toolsData.tools || []);
      setExtConfig(configData);
    } catch (error) {
      console.error('Failed to load extension data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleToolConfigChange = (toolName, field, value) => {
    const currentToolConfig = currentState?.tool_configs?.[toolName] || {};
    updateTool(toolName, {
      ...currentToolConfig,
      [field]: value,
    });
  };

  const handleServiceRestart = async (serviceName) => {
    try {
      await restartService(name, serviceName);
      alert(`Restarted ${serviceName}`);
    } catch (error) {
      alert(`Failed to restart ${serviceName}: ${error.message}`);
    }
  };

  if (loading) {
    return (
      <div className="page-container">
        <LoadingSpinner message="Loading extension details..." />
      </div>
    );
  }

  if (!extension) {
    return (
      <div className="page-container">
        <h1>Extension Not Found</h1>
        <p>The extension "{name}" was not found.</p>
        <Button onClick={() => navigate('/extensions')}>Back to Extensions</Button>
      </div>
    );
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <Button variant="secondary" onClick={() => navigate('/extensions')}>
            ← Back
          </Button>
          <h1>{extension.name}</h1>
          {extConfig?.version && <p className="page-subtitle">Version {extConfig.version}</p>}
        </div>
      </div>

      <div className="tabs">
        <button 
          className={`tab ${activeTab === 'tools' ? 'active' : ''}`}
          onClick={() => setActiveTab('tools')}
        >
          Tools
        </button>
        <button 
          className={`tab ${activeTab === 'services' ? 'active' : ''}`}
          onClick={() => setActiveTab('services')}
        >
          Services
        </button>
        <button 
          className={`tab ${activeTab === 'about' ? 'active' : ''}`}
          onClick={() => setActiveTab('about')}
        >
          About
        </button>
      </div>

      <div className="tab-content">
        {activeTab === 'tools' && (
          <ToolsTab 
            tools={tools} 
            currentState={currentState}
            onConfigChange={handleToolConfigChange}
          />
        )}
        
        {activeTab === 'services' && (
          <ServicesTab 
            extension={extension}
            onRestart={handleServiceRestart}
          />
        )}
        
        {activeTab === 'about' && (
          <AboutTab 
            extension={extension}
            config={extConfig}
          />
        )}
      </div>
    </div>
  );
}

function ToolsTab({ tools, currentState, onConfigChange }) {
  if (tools.length === 0) {
    return (
      <div className="empty-state">
        <p>No tools found in this extension</p>
      </div>
    );
  }

  return (
    <div className="tools-list">
      {tools.map(tool => {
        const toolConfig = currentState?.tool_configs?.[tool.name] || {};
        const enabledInMcp = toolConfig.enabled_in_mcp !== false;
        const passthrough = toolConfig.passthrough === true;

        return (
          <div key={tool.name} className="tool-card">
            <div className="tool-header">
              <h3>{tool.name}</h3>
            </div>
            <div className="tool-body">
              <p className="tool-description">{tool.description || 'No description available'}</p>
              
              <div className="tool-controls">
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={enabledInMcp}
                    onChange={(e) => onConfigChange(tool.name, 'enabled_in_mcp', e.target.checked)}
                  />
                  <span>Enabled in MCP</span>
                </label>
                
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={passthrough}
                    onChange={(e) => onConfigChange(tool.name, 'passthrough', e.target.checked)}
                  />
                  <span>Passthrough Mode</span>
                </label>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function ServicesTab({ extension, onRestart }) {
  const services = extension.services || [];

  if (services.length === 0) {
    return (
      <div className="empty-state">
        <p>No services in this extension</p>
      </div>
    );
  }

  return (
    <div className="services-list">
      {services.map(service => (
        <div key={service.name} className="service-card">
          <div className="service-header">
            <h3>{service.name}</h3>
            <StatusIndicator status={service.status || 'unknown'} />
          </div>
          <div className="service-body">
            <div className="service-info">
              <div className="info-row">
                <span className="info-label">Status:</span>
                <span className="info-value">{service.status || 'unknown'}</span>
              </div>
              {service.port && (
                <div className="info-row">
                  <span className="info-label">Port:</span>
                  <span className="info-value">{service.port}</span>
                </div>
              )}
              {service.pid && (
                <div className="info-row">
                  <span className="info-label">PID:</span>
                  <span className="info-value">{service.pid}</span>
                </div>
              )}
            </div>
            
            <div className="service-actions">
              <Button size="sm" onClick={() => onRestart(service.name)}>
                Restart
              </Button>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

function AboutTab({ extension, config }) {
  return (
    <div className="about-content">
      <div className="about-section">
        <h2>Information</h2>
        <div className="info-grid">
          <div className="info-item">
            <span className="info-label">Name:</span>
            <span className="info-value">{extension.name}</span>
          </div>
          {config?.version && (
            <div className="info-item">
              <span className="info-label">Version:</span>
              <span className="info-value">{config.version}</span>
            </div>
          )}
          <div className="info-item">
            <span className="info-label">Tools:</span>
            <span className="info-value">{extension.tool_count || 0}</span>
          </div>
          <div className="info-item">
            <span className="info-label">Services:</span>
            <span className="info-value">{extension.services?.length || 0}</span>
          </div>
        </div>
      </div>

      {config?.required_secrets && config.required_secrets.length > 0 && (
        <div className="about-section">
          <h2>Required Secrets</h2>
          <ul className="secrets-list">
            {config.required_secrets.map(secret => (
              <li key={secret}>
                <code>{secret}</code>
              </li>
            ))}
          </ul>
          <p className="help-text">
            Configure these secrets in the <a href="/secrets">Secrets Manager</a>
          </p>
        </div>
      )}

      {config?.source && (
        <div className="about-section">
          <h2>Source</h2>
          <p><code>{config.source}</code></p>
        </div>
      )}
    </div>
  );
}
