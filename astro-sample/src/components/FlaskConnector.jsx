import { useState, useEffect } from 'react';

export default function FlaskConnector() {
  const [connectionStatus, setConnectionStatus] = useState('testing');
  const [flaskData, setFlaskData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    testConnection();
  }, []);

  const testConnection = async () => {
    setConnectionStatus('testing');
    setError(null);
    
    // Try multiple endpoints to find the working Flask server
    const endpoints = [
      '/api/test',
      'http://localhost:5000/api/test',
      'http://127.0.0.1:5000/api/test',
      `${window.location.protocol}//${window.location.hostname}:5000/api/test`
    ];
    
    for (const endpoint of endpoints) {
      try {
        const response = await fetch(endpoint, {
          mode: 'cors',
          credentials: 'omit',
          headers: {
            'Accept': 'text/html,application/json,*/*'
          }
        });
        
        if (response.ok) {
          const data = await response.text();
          setFlaskData(data);
          setConnectionStatus('connected');
          return;
        }
      } catch (err) {
        // Continue to next endpoint
        continue;
      }
    }
    
    // If all endpoints failed
    setError('Cannot connect to Flask server. Make sure it\'s running on port 5000.');
    setConnectionStatus('failed');
  };

  const getStatusColor = () => {
    switch (connectionStatus) {
      case 'connected': return 'text-green-600 bg-green-50 border-green-200';
      case 'failed': return 'text-red-600 bg-red-50 border-red-200';
      default: return 'text-blue-600 bg-blue-50 border-blue-200';
    }
  };

  const getStatusIcon = () => {
    switch (connectionStatus) {
      case 'connected': return '✅';
      case 'failed': return '❌';
      default: return '🔄';
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      <h3 className="text-2xl font-bold mb-6 text-center">API Connection Test</h3>
      
      <div className={`border-2 rounded-lg p-6 mb-6 ${getStatusColor()}`}>
        <div className="flex items-center justify-between mb-4">
          <span className="font-semibold">Flask Backend Status</span>
          <span className="text-2xl">{getStatusIcon()}</span>
        </div>
        
        <div className="text-sm">
          <strong>Endpoint:</strong> http://localhost:5000/<br/>
          <strong>Status:</strong> {connectionStatus}
          {error && (
            <>
              <br/><strong>Error:</strong> {error}
            </>
          )}
        </div>
      </div>

      {flaskData && (
        <div className="bg-gray-50 rounded-lg p-4 mb-6">
          <h4 className="font-semibold mb-2">Response from Flask:</h4>
          <pre className="text-sm bg-white p-3 rounded border overflow-x-auto">
            {flaskData}
          </pre>
        </div>
      )}

      <div className="flex justify-center space-x-4">
        <button 
          onClick={testConnection}
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 transition-colors"
          disabled={connectionStatus === 'testing'}
        >
          {connectionStatus === 'testing' ? 'Testing...' : 'Test Connection'}
        </button>
        
        <button 
          onClick={() => window.open('http://localhost:5000/', '_blank')}
          className="bg-gray-600 text-white px-4 py-2 rounded hover:bg-gray-700 transition-colors"
        >
          Open Flask App
        </button>
      </div>

      <div className="mt-6 text-sm text-gray-600">
        <h4 className="font-semibold mb-2">How it works:</h4>
        <ul className="space-y-1">
          <li>1. Astro generates this static page</li>
          <li>2. React component loads on the client</li>
          <li>3. JavaScript makes API call to Flask backend</li>
          <li>4. Flask returns data from port 5000</li>
        </ul>
      </div>
    </div>
  );
}