import React from 'react';
import { NavLink } from 'react-router-dom';
import { useServices } from '../../context/ServicesContext';

export default function Sidebar({ isOpen, onClose }) {
  const { extensions } = useServices();
  
  const extensionsWithUI = extensions.filter(ext => ext.ui?.url);

  const handleLinkClick = () => {
    if (onClose) {
      onClose();
    }
  };

  return (
    <>
      {isOpen && <div className="menu-overlay" onClick={onClose}></div>}
      <div className={`slide-menu ${isOpen ? 'open' : ''}`}>
        <div className="menu-header">Navigation</div>
        
        <NavLink 
          to="/" 
          className={({ isActive }) => `menu-item ${isActive ? 'active' : ''}`}
          onClick={handleLinkClick}
        >
          <span className="menu-icon">🏠</span>
          Dashboard
        </NavLink>
        
        <NavLink 
          to="/extensions" 
          className={({ isActive }) => `menu-item ${isActive ? 'active' : ''}`}
          onClick={handleLinkClick}
        >
          <span className="menu-icon">📦</span>
          Extensions
        </NavLink>
        
        <NavLink 
          to="/queue" 
          className={({ isActive }) => `menu-item ${isActive ? 'active' : ''}`}
          onClick={handleLinkClick}
        >
          <span className="menu-icon">🔄</span>
          Updates
        </NavLink>
        
        <NavLink 
          to="/store" 
          className={({ isActive }) => `menu-item ${isActive ? 'active' : ''}`}
          onClick={handleLinkClick}
        >
          <span className="menu-icon">🏪</span>
          Store
        </NavLink>
        
        <NavLink 
          to="/secrets" 
          className={({ isActive }) => `menu-item ${isActive ? 'active' : ''}`}
          onClick={handleLinkClick}
        >
          <span className="menu-icon">🔑</span>
          Secrets
        </NavLink>
        
        <NavLink 
          to="/infrastructure" 
          className={({ isActive }) => `menu-item ${isActive ? 'active' : ''}`}
          onClick={handleLinkClick}
        >
          <span className="menu-icon">🏗️</span>
          Infrastructure
        </NavLink>
        
        <NavLink 
          to="/tools" 
          className={({ isActive }) => `menu-item ${isActive ? 'active' : ''}`}
          onClick={handleLinkClick}
        >
          <span className="menu-icon">🔧</span>
          Tool Manager
        </NavLink>
        
        <div className="menu-divider"></div>
        <div className="menu-section-title">Extension UIs</div>
        
        {extensionsWithUI.length === 0 ? (
          <div className="menu-item disabled">No extension UIs</div>
        ) : (
          extensionsWithUI.map(ext => (
            <NavLink 
              key={ext.name}
              to={`/ext/${ext.name}`}
              className={({ isActive }) => `menu-item ${isActive ? 'active' : ''}`}
              onClick={handleLinkClick}
            >
              <span className="menu-icon">📦</span>
              {ext.name}
            </NavLink>
          ))
        )}
      </div>
    </>
  );
}




