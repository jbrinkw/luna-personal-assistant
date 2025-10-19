import React from 'react';

export default function LoadingSpinner({ size = 'md', message = '' }) {
  return (
    <div className={`loading-spinner loading-spinner-${size}`}>
      <div className="spinner"></div>
      {message && <p className="loading-message">{message}</p>}
    </div>
  );
}



