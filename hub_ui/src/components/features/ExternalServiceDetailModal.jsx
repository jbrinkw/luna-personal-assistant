import { useState } from 'react';

/**
 * Modal for viewing detailed information about an external service
 * Shows tabs for Overview, Configuration, Provides, and Documentation
 */
export default function ExternalServiceDetailModal({ service, onInstall, onClose }) {
  const [activeTab, setActiveTab] = useState('overview');

  const definition = service.definition;
  const form = service.form;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg max-w-4xl w-full max-h-[85vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b">
          <div>
            <h2 className="text-2xl font-semibold">{definition.display_name}</h2>
            <p className="text-gray-600 text-sm mt-1">{definition.description}</p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 text-2xl"
          >
            ×
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b">
          <button
            onClick={() => setActiveTab('overview')}
            className={`px-6 py-3 font-medium ${
              activeTab === 'overview'
                ? 'text-blue-600 border-b-2 border-blue-600'
                : 'text-gray-600 hover:text-gray-800'
            }`}
          >
            Overview
          </button>
          <button
            onClick={() => setActiveTab('configuration')}
            className={`px-6 py-3 font-medium ${
              activeTab === 'configuration'
                ? 'text-blue-600 border-b-2 border-blue-600'
                : 'text-gray-600 hover:text-gray-800'
            }`}
          >
            Configuration
          </button>
          <button
            onClick={() => setActiveTab('provides')}
            className={`px-6 py-3 font-medium ${
              activeTab === 'provides'
                ? 'text-blue-600 border-b-2 border-blue-600'
                : 'text-gray-600 hover:text-gray-800'
            }`}
          >
            Provides
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-6">
          {activeTab === 'overview' && (
            <div className="space-y-4">
              <div>
                <h3 className="font-semibold text-lg mb-2">About</h3>
                <p className="text-gray-700">{definition.description}</p>
              </div>

              <div>
                <h3 className="font-semibold text-lg mb-2">Details</h3>
                <dl className="grid grid-cols-2 gap-3">
                  <div>
                    <dt className="text-sm font-medium text-gray-500">Name</dt>
                    <dd className="text-gray-900">{definition.name}</dd>
                  </div>
                  <div>
                    <dt className="text-sm font-medium text-gray-500">Category</dt>
                    <dd className="text-gray-900 capitalize">{definition.category}</dd>
                  </div>
                  <div>
                    <dt className="text-sm font-medium text-gray-500">Installation Timeout</dt>
                    <dd className="text-gray-900">{definition.install_timeout || 120} seconds</dd>
                  </div>
                  {definition.requires_sudo && (
                    <div>
                      <dt className="text-sm font-medium text-gray-500">Requires</dt>
                      <dd className="text-red-600">Sudo privileges</dd>
                    </div>
                  )}
                  {definition.ui && (
                    <>
                      <div>
                        <dt className="text-sm font-medium text-gray-500">UI Routing</dt>
                        <dd className="text-gray-900">
                          {definition.ui.base_path || 'ext_service'}/{definition.ui.slug || definition.name}
                        </dd>
                      </div>
                      <div>
                        <dt className="text-sm font-medium text-gray-500">UI Launch Mode</dt>
                        <dd className="text-gray-900">
                          {definition.ui.open_mode === 'new_tab' ? 'Opens in new tab' : 'Embeds in Hub'}
                        </dd>
                      </div>
                    </>
                  )}
                </dl>
              </div>

              {definition.required_vars && definition.required_vars.length > 0 && (
                <div>
                  <h3 className="font-semibold text-lg mb-2">Required Environment Variables</h3>
                  <div className="bg-yellow-50 border border-yellow-200 rounded p-3">
                    <p className="text-sm text-yellow-800 mb-2">
                      This service requires the following environment variables:
                    </p>
                    <ul className="list-disc list-inside text-sm text-yellow-900">
                      {definition.required_vars.map(varName => (
                        <li key={varName}><code>{varName}</code></li>
                      ))}
                    </ul>
                  </div>
                </div>
              )}
            </div>
          )}

          {activeTab === 'configuration' && (
            <div className="space-y-4">
              <div>
                <h3 className="font-semibold text-lg mb-2">Configuration Fields</h3>
                <p className="text-gray-600 text-sm mb-4">
                  These fields will be presented during installation:
                </p>
              </div>

              {form && form.fields && form.fields.length > 0 ? (
                <div className="space-y-3">
                  {form.fields.map(field => (
                    <div key={field.name} className="bg-gray-50 rounded p-4">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center">
                            <span className="font-medium">{field.label}</span>
                            {field.required && (
                              <span className="ml-2 text-xs bg-red-100 text-red-600 px-2 py-0.5 rounded">
                                Required
                              </span>
                            )}
                          </div>
                          <div className="text-sm text-gray-600 mt-1">
                            <span className="font-mono text-xs bg-gray-200 px-1 py-0.5 rounded mr-2">
                              {field.name}
                            </span>
                            <span className="text-gray-500">({field.type})</span>
                          </div>
                          {field.help && (
                            <p className="text-sm text-gray-600 mt-2">{field.help}</p>
                          )}
                          {field.default !== undefined && field.default !== '' && (
                            <p className="text-xs text-gray-500 mt-1">
                              Default: <code className="bg-gray-200 px-1 rounded">{String(field.default)}</code>
                            </p>
                          )}
                          {field.options && (
                            <p className="text-xs text-gray-500 mt-1">
                              Options: {field.options.join(', ')}
                            </p>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="bg-gray-50 rounded p-8 text-center text-gray-600">
                  No configuration required for this service.
                </div>
              )}
            </div>
          )}

          {activeTab === 'provides' && (
            <div className="space-y-4">
              <div>
                <h3 className="font-semibold text-lg mb-2">Environment Variables Provided</h3>
                <p className="text-gray-600 text-sm mb-4">
                  After installation, Luna writes these variables into your <code>.env</code> automatically:
                </p>
              </div>

              {definition.provides_vars && definition.provides_vars.length > 0 ? (
                <div className="space-y-2">
                  {definition.provides_vars.map(varName => (
                    <div key={varName} className="bg-green-50 border border-green-200 rounded p-3">
                      <code className="text-sm font-mono text-green-800">{varName}</code>
                    </div>
                  ))}
                  <p className="text-xs text-gray-500">
                    Need them elsewhere? Copy from the Infrastructure page after install.
                  </p>
                </div>
              ) : (
                <div className="bg-gray-50 rounded p-8 text-center text-gray-600">
                  This service does not provide any documented environment variables.
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex justify-between items-center p-6 border-t bg-gray-50">
          <div className="text-sm text-gray-600">
            {service.installed ? (
              <span className="text-green-600 font-medium">✓ Already installed</span>
            ) : (
              <span>Ready to install</span>
            )}
          </div>
          <div className="flex space-x-2">
            <button
              onClick={onClose}
              className="px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
            >
              Close
            </button>
            {!service.installed && (
              <button
                onClick={onInstall}
                className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
              >
                Install
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
