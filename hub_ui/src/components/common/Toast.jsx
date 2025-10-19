import React from 'react';

export default function Toast({ message, type = 'info', onClose }) {
  return (
    <div className={`toast toast-${type}`}>
      <span className="toast-message">{message}</span>
      {onClose && (
        <button className="toast-close" onClick={onClose}>
          ×
        </button>
      )}
    </div>
  );
}

export function ToastContainer({ toasts, onClose }) {
  return (
    <div className="toast-container">
      {toasts.map(toast => (
        <Toast
          key={toast.id}
          message={toast.message}
          type={toast.type}
          onClose={() => onClose(toast.id)}
        />
      ))}
    </div>
  );
}



