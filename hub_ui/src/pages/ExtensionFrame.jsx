import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useServices } from '../context/ServicesContext';
import Button from '../components/common/Button';

export default function ExtensionFrame() {
  const { name } = useParams();
  const navigate = useNavigate();
  const { extensions } = useServices();
  
  const extension = extensions.find(ext => ext.name === name);
  const url = extension?.ui?.url;

  if (!extension) {
    return (
      <div className="fullscreen-iframe-container">
        <div className="iframe-error">
          <p>Extension "{name}" not found</p>
          <Button onClick={() => navigate('/')}>Back to Dashboard</Button>
        </div>
      </div>
    );
  }

  if (!url) {
    return (
      <div className="fullscreen-iframe-container">
        <div className="iframe-error">
          <p>No UI available for this extension</p>
          <Button onClick={() => navigate('/')}>Back to Dashboard</Button>
        </div>
      </div>
    );
  }

  return (
    <div className="fullscreen-iframe-container">
      <iframe 
        className="fullscreen-iframe" 
        src={url} 
        title={`${name} UI`}
      />
    </div>
  );
}



