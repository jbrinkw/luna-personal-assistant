import React from 'react';

export default function Card({ children, className = '', onClick }) {
  return (
    <div 
      className={`card ${className}`}
      onClick={onClick}
      style={onClick ? { cursor: 'pointer' } : {}}
    >
      {children}
    </div>
  );
}

export function CardTitle({ children, className = '' }) {
  return <div className={`card-title ${className}`}>{children}</div>;
}

export function CardContent({ children, className = '' }) {
  return <div className={`card-content ${className}`}>{children}</div>;
}




