import os
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

# Create Flask app and database
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or "a secret key"
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

db = SQLAlchemy(model_class=Base)
db.init_app(app)

# Import and initialize models
from models import create_user_model
User = create_user_model(db)

# Create tables
with app.app_context():
    db.create_all()

@app.route('/')
def hello():
    return "Hello World! Database is connected."

@app.route('/api/users', methods=['GET'])
def get_users():
    """Get all users from database"""
    users = User.query.all()
    return jsonify([{
        'id': user.id,
        'name': user.name,
        'email': user.email
    } for user in users])

@app.route('/api/users', methods=['POST'])
def create_user():
    """Create a new user"""
    data = request.get_json()
    
    if not data or 'name' not in data or 'email' not in data:
        return jsonify({'error': 'Name and email are required'}), 400
    
    user = User(name=data['name'], email=data['email'])
    db.session.add(user)
    db.session.commit()
    
    return jsonify({
        'id': user.id,
        'name': user.name,
        'email': user.email
    }), 201

@app.route('/api/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    """Get a specific user"""
    user = User.query.get_or_404(user_id)
    return jsonify({
        'id': user.id,
        'name': user.name,
        'email': user.email
    })

@app.route('/api/users/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    """Update a user"""
    user = User.query.get_or_404(user_id)
    data = request.get_json()
    
    if 'name' in data:
        user.name = data['name']
    if 'email' in data:
        user.email = data['email']
    
    db.session.commit()
    
    return jsonify({
        'id': user.id,
        'name': user.name,
        'email': user.email
    })

@app.route('/api/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    """Delete a user"""
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    
    return jsonify({'message': 'User deleted successfully'}), 200

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'database': 'connected',
        'timestamp': db.session.execute(db.text('SELECT NOW()')).scalar()
    })

@app.route('/demo', methods=['GET'])
def demo_page():
    """Demo page with form to test endpoints"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Flask API Demo</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .endpoint { margin: 20px 0; padding: 15px; border: 1px solid #ddd; }
            button { padding: 10px 15px; margin: 5px; background: #007bff; color: white; border: none; cursor: pointer; }
            button:hover { background: #0056b3; }
            input, textarea { padding: 8px; margin: 5px; width: 200px; border: 1px solid #ddd; }
            pre { background: #f5f5f5; padding: 10px; overflow-x: auto; border: 1px solid #ddd; }
            .success { color: green; }
            .error { color: red; }
        </style>
    </head>
    <body>
        <h1>Flask API Demo</h1>
        
        <div class="endpoint">
            <h3>Create User (POST /api/users)</h3>
            <input type="text" id="name" placeholder="Name">
            <input type="email" id="email" placeholder="Email">
            <button onclick="createUser()">Create User</button>
        </div>
        
        <div class="endpoint">
            <h3>Get All Users (GET /api/users)</h3>
            <button onclick="getUsers()">Get Users</button>
        </div>
        
        <div class="endpoint">
            <h3>Health Check (GET /api/health)</h3>
            <button onclick="healthCheck()">Check Health</button>
        </div>
        
        <div id="result">
            <h3>Response:</h3>
            <pre id="response">Click a button to test the API...</pre>
        </div>
        
        <script>
        async function createUser() {
            const name = document.getElementById('name').value;
            const email = document.getElementById('email').value;
            
            if (!name || !email) {
                document.getElementById('response').textContent = 'Please enter both name and email';
                return;
            }
            
            try {
                const response = await fetch('/api/users', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({name, email})
                });
                
                const data = await response.json();
                document.getElementById('response').textContent = JSON.stringify(data, null, 2);
                
                // Clear inputs on success
                if (response.ok) {
                    document.getElementById('name').value = '';
                    document.getElementById('email').value = '';
                }
            } catch (error) {
                document.getElementById('response').textContent = 'Error: ' + error.message;
            }
        }
        
        async function getUsers() {
            try {
                const response = await fetch('/api/users');
                const data = await response.json();
                document.getElementById('response').textContent = JSON.stringify(data, null, 2);
            } catch (error) {
                document.getElementById('response').textContent = 'Error: ' + error.message;
            }
        }
        
        async function healthCheck() {
            try {
                const response = await fetch('/api/health');
                const data = await response.json();
                document.getElementById('response').textContent = JSON.stringify(data, null, 2);
            } catch (error) {
                document.getElementById('response').textContent = 'Error: ' + error.message;
            }
        }
        </script>
    </body>
    </html>
    """
    return html

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)