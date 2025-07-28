import React, { useState, useEffect } from 'react';

const FlaskConnector = () => {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [connectionStatus, setConnectionStatus] = useState('disconnected');
  const [newUser, setNewUser] = useState({ name: '', email: '' });
  const [createLoading, setCreateLoading] = useState(false);

  // Flask API base URL
  const API_BASE = 'http://localhost:5000';

  // Test connection to Flask backend
  const testConnection = async () => {
    try {
      const response = await fetch(`${API_BASE}/health`);
      if (response.ok) {
        setConnectionStatus('connected');
        setError(null);
        return true;
      } else {
        throw new Error(`HTTP ${response.status}`);
      }
    } catch (err) {
      setConnectionStatus('error');
      setError(`Connection failed: ${err.message}`);
      return false;
    }
  };

  // Fetch users from Flask API
  const fetchUsers = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`${API_BASE}/api/users`);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const data = await response.json();
      setUsers(Array.isArray(data) ? data : []);
      setConnectionStatus('connected');
    } catch (err) {
      setError(`Failed to fetch users: ${err.message}`);
      setConnectionStatus('error');
      setUsers([]);
    } finally {
      setLoading(false);
    }
  };

  // Create new user
  const createUser = async (e) => {
    e.preventDefault();
    setCreateLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE}/api/users`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(newUser),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const createdUser = await response.json();
      setUsers([...users, createdUser]);
      setNewUser({ name: '', email: '' });
      setConnectionStatus('connected');
    } catch (err) {
      setError(`Failed to create user: ${err.message}`);
      setConnectionStatus('error');
    } finally {
      setCreateLoading(false);
    }
  };

  // Test semantic layer endpoint
  const testSemanticLayer = async () => {
    setLoading(true);
    setError(null);

    try {
      // Test the semantic layer from your Flask app
      const response = await fetch(`${API_BASE}/api/v1/convert`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: 'Show me all users',
          execute: true
        }),
      });

      if (response.ok) {
        const result = await response.json();
        setError(null);
        alert(`Semantic Layer Test Successful!\nSQL: ${result.sql_query}\nConfidence: ${result.confidence_score}`);
      } else {
        throw new Error(`Semantic layer not available: ${response.status}`);
      }
    } catch (err) {
      setError(`Semantic layer test failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  // Test connection on component mount
  useEffect(() => {
    testConnection();
  }, []);

  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      <h3 className="text-2xl font-bold mb-6 text-center">Live Flask Integration</h3>
      
      {/* Connection Status */}
      <div className="mb-6 p-4 rounded-lg border">
        <div className="flex items-center justify-between mb-4">
          <h4 className="text-lg font-semibold">Connection Status</h4>
          <div className={`px-3 py-1 rounded-full text-sm font-medium ${
            connectionStatus === 'connected' 
              ? 'bg-green-100 text-green-800' 
              : connectionStatus === 'error'
              ? 'bg-red-100 text-red-800'
              : 'bg-gray-100 text-gray-800'
          }`}>
            {connectionStatus === 'connected' && '✅ Connected'}
            {connectionStatus === 'error' && '❌ Error'}
            {connectionStatus === 'disconnected' && '⏳ Disconnected'}
          </div>
        </div>
        
        <div className="flex space-x-2">
          <button 
            onClick={testConnection}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors text-sm"
          >
            Test Connection
          </button>
          <button 
            onClick={fetchUsers}
            disabled={loading}
            className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 disabled:bg-gray-400 transition-colors text-sm"
          >
            {loading ? 'Loading...' : 'Fetch Users'}
          </button>
          <button 
            onClick={testSemanticLayer}
            disabled={loading}
            className="px-4 py-2 bg-purple-600 text-white rounded hover:bg-purple-700 disabled:bg-gray-400 transition-colors text-sm"
          >
            Test Semantic Layer
          </button>
        </div>

        {error && (
          <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded">
            <p className="text-red-700 text-sm">
              <strong>Error:</strong> {error}
            </p>
            <p className="text-red-600 text-xs mt-1">
              Make sure your Flask app is running on port 5000
            </p>
          </div>
        )}
      </div>

      {/* Create User Form */}
      <div className="mb-6 p-4 bg-gray-50 rounded-lg">
        <h4 className="text-lg font-semibold mb-4">Create New User</h4>
        <form onSubmit={createUser} className="space-y-4">
          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Name
              </label>
              <input
                type="text"
                value={newUser.name}
                onChange={(e) => setNewUser({...newUser, name: e.target.value})}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Enter user name"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Email
              </label>
              <input
                type="email"
                value={newUser.email}
                onChange={(e) => setNewUser({...newUser, email: e.target.value})}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Enter user email"
                required
              />
            </div>
          </div>
          <button
            type="submit"
            disabled={createLoading || connectionStatus !== 'connected'}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 transition-colors"
          >
            {createLoading ? 'Creating...' : 'Create User'}
          </button>
        </form>
      </div>

      {/* Users List */}
      <div className="mb-6">
        <h4 className="text-lg font-semibold mb-4">Users from Flask Database</h4>
        
        {loading ? (
          <div className="text-center py-8">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            <p className="mt-2 text-gray-600">Loading users...</p>
          </div>
        ) : users.length > 0 ? (
          <div className="space-y-2">
            {users.map((user) => (
              <div key={user.id} className="p-3 bg-gray-50 rounded-lg border">
                <div className="flex justify-between items-center">
                  <div>
                    <h5 className="font-medium">{user.name}</h5>
                    <p className="text-sm text-gray-600">{user.email}</p>
                  </div>
                  <div className="text-sm text-gray-500">
                    ID: {user.id}
                  </div>
                </div>
              </div>
            ))}
            <div className="text-sm text-gray-500 text-center">
              Total users: {users.length}
            </div>
          </div>
        ) : (
          <div className="text-center py-8 text-gray-500">
            <p>No users found. Try creating one or check your Flask connection.</p>
          </div>
        )}
      </div>

      {/* API Endpoints Info */}
      <div className="p-4 bg-blue-50 rounded-lg">
        <h4 className="text-lg font-semibold mb-3 text-blue-800">Flask API Endpoints</h4>
        <div className="space-y-2 text-sm">
          <div className="flex items-center">
            <span className="inline-block w-16 px-2 py-1 bg-green-100 text-green-800 rounded text-xs mr-3">GET</span>
            <code className="text-blue-700">/health</code>
            <span className="text-gray-600 ml-2">- Health check</span>
          </div>
          <div className="flex items-center">
            <span className="inline-block w-16 px-2 py-1 bg-green-100 text-green-800 rounded text-xs mr-3">GET</span>
            <code className="text-blue-700">/api/users</code>
            <span className="text-gray-600 ml-2">- Get all users</span>
          </div>
          <div className="flex items-center">
            <span className="inline-block w-16 px-2 py-1 bg-blue-100 text-blue-800 rounded text-xs mr-3">POST</span>
            <code className="text-blue-700">/api/users</code>
            <span className="text-gray-600 ml-2">- Create new user</span>
          </div>
          <div className="flex items-center">
            <span className="inline-block w-16 px-2 py-1 bg-purple-100 text-purple-800 rounded text-xs mr-3">POST</span>
            <code className="text-blue-700">/api/v1/convert</code>
            <span className="text-gray-600 ml-2">- Semantic layer</span>
          </div>
        </div>
      </div>

      {/* Framework Explanation */}
      <div className="mt-6 p-4 bg-gradient-to-r from-purple-50 to-blue-50 rounded-lg">
        <h4 className="font-semibold mb-2">Framework Integration in Action</h4>
        <p className="text-sm text-gray-700">
          This React component demonstrates Astro's "island architecture" - it only loads JavaScript 
          where needed (this interactive section), while the rest of the page remains static HTML. 
          The component seamlessly communicates with your Flask backend using standard HTTP requests.
        </p>
      </div>
    </div>
  );
};

export default FlaskConnector;