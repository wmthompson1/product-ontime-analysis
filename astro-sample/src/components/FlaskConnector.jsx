import { useState } from 'react';

export default function FlaskConnector() {
  const [connectionStatus, setConnectionStatus] = useState('Not tested');
  const [flaskResult, setFlaskResult] = useState(null);
  const [errorMessage, setErrorMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const testFlaskConnection = async () => {
    setIsLoading(true);
    setFlaskResult(null);
    setErrorMessage('');
    setConnectionStatus('Testing...');

    try {
      // Use the Astro API route that proxies to Flask
      const response = await fetch('/api/health');
      
      const data = await response.json();
      
      // Success
      setConnectionStatus('Connected');
      setFlaskResult(JSON.stringify(data, null, 2));
    } catch (error) {
      // Error
      setConnectionStatus('Error');
      setErrorMessage(error.message);
    } finally {
      setIsLoading(false);
    }
  };

  const getStatusColor = () => {
    switch (connectionStatus) {
      case 'Connected':
        return 'bg-green-100 text-green-800';
      case 'Error':
        return 'bg-red-100 text-red-800';
      case 'Testing...':
        return 'bg-yellow-100 text-yellow-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusIcon = () => {
    switch (connectionStatus) {
      case 'Connected':
        return '✅';
      case 'Error':
        return '❌';
      case 'Testing...':
        return '⏳';
      default:
        return '⏳';
    }
  };

  return (
    <div className="max-w-2xl mx-auto">
      <div className="bg-white rounded-lg p-6 shadow">
        <div className="flex items-center justify-between mb-4">
          <h4 className="text-lg font-semibold">Flask API Status</h4>
          <div className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusColor()}`}>
            {getStatusIcon()} {connectionStatus}
          </div>
        </div>
        
        <button
          onClick={testFlaskConnection}
          disabled={isLoading}
          className={`w-full mb-4 px-4 py-2 rounded transition-colors ${
            isLoading
              ? 'bg-gray-400 text-gray-200 cursor-not-allowed'
              : 'bg-blue-600 text-white hover:bg-blue-700'
          }`}
        >
          {isLoading ? 'Testing Connection...' : 'Test Flask Connection'}
        </button>
        
        {flaskResult && (
          <div className="p-3 rounded border bg-green-50 border-green-200">
            <h5 className="font-semibold text-green-800 mb-2">Response:</h5>
            <pre className="text-sm overflow-x-auto text-green-700">
              {flaskResult}
            </pre>
          </div>
        )}
        
        {errorMessage && (
          <div className="p-3 bg-red-50 border border-red-200 rounded">
            <p className="text-red-700 text-sm">
              <strong>Connection failed:</strong> {errorMessage}
            </p>
            <p className="text-red-600 text-xs mt-1">
              Make sure your Flask app is running on http://localhost:5000
            </p>
          </div>
        )}

        <div className="mt-4 text-sm text-gray-600">
          <p><strong>Expected endpoints:</strong></p>
          <ul className="mt-2 space-y-1 text-xs">
            <li>• GET /health - Health check</li>
            <li>• GET /api/users - Get users</li>
            <li>• POST /api/v1/convert - Semantic layer</li>
          </ul>
        </div>
      </div>
    </div>
  );
}