import { useState } from 'react';
import { installService } from '../../lib/externalServicesApi';

/**
 * Modal for configuring and installing an external service
 * Dynamically generates form fields based on config-form.json
 */
export default function ExternalServiceConfigModal({ service, onSuccess, onClose }) {
  const [config, setConfig] = useState(() => {
    // Initialize config with default values from form fields
    const initialConfig = {};
    if (service.form && service.form.fields) {
      service.form.fields.forEach(field => {
        initialConfig[field.name] = field.default !== undefined ? field.default : '';
      });
    }
    return initialConfig;
  });
  
  const [installing, setInstalling] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);
  const [installResult, setInstallResult] = useState(null);

  const handleFieldChange = (fieldName, value) => {
    setConfig(prev => ({ ...prev, [fieldName]: value }));
  };

  const validateRequired = () => {
    if (!service.form || !service.form.fields) return true;
    
    for (const field of service.form.fields) {
      if (field.required && !config[field.name]) {
        return false;
      }
    }
    return true;
  };

  const handleInstall = async () => {
    if (!validateRequired()) {
      setError('Please fill in all required fields');
      return;
    }

    setInstalling(true);
    setError(null);

    try {
      const result = await installService(service.definition.name, config);
      setInstallResult(result);
      setSuccess(true);
      
      // Call success callback after a short delay to show result
      setTimeout(() => {
        if (onSuccess) onSuccess();
      }, 2000);
    } catch (err) {
      setError(err.message || 'Installation failed');
      setInstalling(false);
    }
  };

  const copyToClipboard = async (text) => {
    try {
      await navigator.clipboard.writeText(text);
      alert('Configuration copied to clipboard');
    } catch (err) {
      alert('Failed to copy to clipboard');
    }
  };

  const formatConfigForClipboard = (cfg) => {
    return Object.entries(cfg)
      .map(([key, value]) => `${key}=${value}`)
      .join('\n');
  };

  const renderField = (field) => {
    const value = config[field.name];

    switch (field.type) {
      case 'text':
        return (
          <input
            type="text"
            value={value || ''}
            onChange={(e) => handleFieldChange(field.name, e.target.value)}
            className="w-full px-3 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder={field.default}
            required={field.required}
          />
        );

      case 'password':
        return (
          <input
            type="password"
            value={value || ''}
            onChange={(e) => handleFieldChange(field.name, e.target.value)}
            className="w-full px-3 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="Enter password"
            required={field.required}
          />
        );

      case 'number':
        return (
          <input
            type="number"
            value={value || ''}
            onChange={(e) => handleFieldChange(field.name, parseInt(e.target.value) || '')}
            className="w-full px-3 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder={field.default}
            required={field.required}
          />
        );

      case 'checkbox':
        return (
          <label className="flex items-center space-x-2">
            <input
              type="checkbox"
              checked={value || false}
              onChange={(e) => handleFieldChange(field.name, e.target.checked)}
              className="rounded"
            />
            <span>Enable</span>
          </label>
        );

      case 'select':
        return (
          <select
            value={value || ''}
            onChange={(e) => handleFieldChange(field.name, e.target.value)}
            className="w-full px-3 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
            required={field.required}
          >
            <option value="">Select...</option>
            {field.options && field.options.map(option => (
              <option key={option} value={option}>{option}</option>
            ))}
          </select>
        );

      default:
        return (
          <input
            type="text"
            value={value || ''}
            onChange={(e) => handleFieldChange(field.name, e.target.value)}
            className="w-full px-3 py-2 border rounded"
            required={field.required}
          />
        );
    }
  };

  if (success && installResult) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg p-6 max-w-2xl w-full max-h-[80vh] overflow-auto">
          <div className="mb-4">
            <div className="flex items-center text-green-600 mb-2">
              <svg className="w-6 h-6 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              <h2 className="text-xl font-semibold">Installation Successful!</h2>
            </div>
            <p className="text-gray-600">
              {service.definition.display_name} has been installed successfully.
            </p>
          </div>

          <div className="bg-gray-50 rounded p-4 mb-4">
            <h3 className="font-semibold mb-2">Configuration:</h3>
            <pre className="text-sm overflow-auto max-h-60 bg-white p-2 rounded">
              {JSON.stringify(installResult.config, null, 2)}
            </pre>
          </div>

          <div className="bg-blue-50 border border-blue-200 rounded p-4 mb-4">
            <p className="text-sm text-blue-800">
              💡 You can add these values to your .env file if extensions require them.
            </p>
          </div>

          <div className="flex justify-between">
            <button
              onClick={() => copyToClipboard(formatConfigForClipboard(installResult.config))}
              className="px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
            >
              Copy to Clipboard
            </button>
            <button
              onClick={onClose}
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 max-w-2xl w-full max-h-[80vh] overflow-auto">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-2xl font-semibold">
            Install {service.definition.display_name}
          </h2>
          <button
            onClick={onClose}
            disabled={installing}
            className="text-gray-500 hover:text-gray-700 text-2xl"
          >
            ×
          </button>
        </div>

        <p className="text-gray-600 mb-6">
          {service.definition.description}
        </p>

        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
            {error}
          </div>
        )}

        {service.form && service.form.fields && service.form.fields.length > 0 ? (
          <div className="space-y-4 mb-6">
            {service.form.fields.map(field => (
              <div key={field.name}>
                <label className="block mb-1">
                  <span className="font-medium">
                    {field.label}
                    {field.required && <span className="text-red-500 ml-1">*</span>}
                  </span>
                </label>
                {renderField(field)}
                {field.help && (
                  <p className="text-sm text-gray-500 mt-1">{field.help}</p>
                )}
              </div>
            ))}
          </div>
        ) : (
          <div className="bg-gray-50 rounded p-4 mb-6 text-center text-gray-600">
            No configuration required for this service.
          </div>
        )}

        <div className="flex justify-end space-x-2">
          <button
            onClick={onClose}
            disabled={installing}
            className="px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300 disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={handleInstall}
            disabled={installing || !validateRequired()}
            className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50"
          >
            {installing ? (
              <>
                <span className="inline-block animate-spin mr-2">⏳</span>
                Installing...
              </>
            ) : (
              'Start Installation'
            )}
          </button>
        </div>

        {installing && (
          <div className="mt-4 text-sm text-gray-600 text-center">
            Installation may take up to {service.definition.install_timeout || 120} seconds...
          </div>
        )}
      </div>
    </div>
  );
}

