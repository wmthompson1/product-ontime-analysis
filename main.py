# Adding a new route to integrate Claude sample via iframe.
import os
from flask import Flask, request, jsonify, send_from_directory, render_template
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Create Flask app and database
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or "a secret key"

# Add CORS headers to all responses
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE')
    return response
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
    from datetime import datetime
    return render_template('index.html', current_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))


@app.route('/health')
@app.route('/api/health')
def health_check():
    """Health check endpoint for API testing"""
    return jsonify({
        'status': 'healthy',
        'message': 'Flask API is running successfully!',
        'version': '1.0',
        'timestamp': '2025-07-28T02:25:00Z'
    })


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
    return jsonify({'id': user.id, 'name': user.name, 'email': user.email})


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

    return jsonify({'id': user.id, 'name': user.name, 'email': user.email})


@app.route('/api/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    """Delete a user"""
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()

    return jsonify({'message': 'User deleted successfully'}), 200


@app.route('/my_model/<filename>', methods=['GET', 'OPTIONS'])
def serve_model_files(filename):
    """Serve Teachable Machine model files"""
    if request.method == 'OPTIONS':
        # Handle CORS preflight
        response = app.make_default_options_response()
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response

    try:
        from flask import Response
        import mimetypes

        # Set proper content type based on file extension
        if filename.endswith('.json'):
            mimetype = 'application/json'
        elif filename.endswith('.bin'):
            mimetype = 'application/octet-stream'
        else:
            mimetype = mimetypes.guess_type(filename)[0] or 'application/octet-stream'

        response = send_from_directory('my_model', filename, mimetype=mimetype)

        # Add CORS headers to allow cross-origin requests
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'

        return response
    except FileNotFoundError:
        return jsonify({'error': 'Model file not found'}), 404





@app.route('/audio-classifier', methods=['GET'])
def audio_classifier():
    """Audio classification page using Teachable Machine model"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Audio Classification Demo</title>
        <style>
            body { 
                font-family: Arial, sans-serif; 
                margin: 40px; 
                background-color: #f5f5f5; 
            }
            .container { 
                max-width: 800px; 
                margin: 0 auto; 
                background: white; 
                padding: 30px; 
                border-radius: 10px; 
                box-shadow: 0 2px 10px rgba(0,0,0,0.1); 
            }
            button { 
                padding: 15px 30px; 
                margin: 10px; 
                background: #007bff; 
                color: white; 
                border: none; 
                cursor: pointer; 
                border-radius: 5px; 
                font-size: 16px; 
            }
            button:hover { background: #0056b3; }
            button:disabled { background: #cccccc; cursor: not-allowed; }
            .status { 
                padding: 10px; 
                margin: 10px 0; 
                border-radius: 5px; 
                font-weight: bold; 
            }
            .listening { background-color: #d4edda; color: #155724; }
            .stopped { background-color: #f8d7da; color: #721c24; }
            .prediction { 
                margin: 10px 0; 
                padding: 15px; 
                background: #f8f9fa; 
                border-left: 4px solid #007bff; 
                border-radius: 4px; 
            }
            .prediction-item { 
                margin: 5px 0; 
                padding: 8px; 
                background: white; 
                border-radius: 4px; 
                border: 1px solid #e9ecef; 
            }
            .high-confidence { background-color: #d1ecf1; }
            .prediction-log { 
                max-height: 300px; 
                overflow-y: auto; 
                border: 1px solid #ddd; 
                padding: 10px; 
                margin-top: 20px; 
                background: #f8f9fa; 
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎤 Audio Classification Demo</h1>
            <p>Click "Start Listening" to begin audio classification using your trained Teachable Machine model.</p>

            <div id="status" class="status stopped">Status: Not listening</div>

            <button id="startBtn" onclick="startListening()">Start Listening</button>
            <button id="stopBtn" onclick="stopListening()" disabled>Stop Listening</button>

            <div id="predictions" class="prediction">
                <h3>Current Predictions:</h3>
                <div id="label-container">Click "Start Listening" to see predictions...</div>
            </div>

            <div class="prediction-log">
                <h3>Prediction Log:</h3>
                <div id="log-container"></div>
            </div>
        </div>

        <script src="https://cdn.jsdelivr.net/npm/@tensorflow/tfjs@1.3.1/dist/tf.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/@tensorflow-models/speech-commands@0.4.0/dist/speech-commands.min.js"></script>

        <script type="text/javascript">
            // Construct absolute URLs for the model files
            const baseURL = window.location.origin;
            const URL = baseURL + "/my_model/";
            let recognizer = null;
            let isListening = false;

            async function createModel() {
                try {
                    console.log("Starting model creation...");
                    const checkpointURL = URL + "model.json";
                    const metadataURL = URL + "metadata.json";

                    console.log("Model URLs:", { checkpointURL, metadataURL });

                    // Test if files are accessible
                    const modelResponse = await fetch(checkpointURL);
                    const metadataResponse = await fetch(metadataURL);

                    console.log("Model fetch status:", modelResponse.status);
                    console.log("Metadata fetch status:", metadataResponse.status);

                    if (!modelResponse.ok) {
                        throw new Error(`Failed to fetch model.json: ${modelResponse.status}`);
                    }
                    if (!metadataResponse.ok) {
                        throw new Error(`Failed to fetch metadata.json: ${metadataResponse.status}`);
                    }

                    recognizer = speechCommands.create(
                        "BROWSER_FFT",
                        undefined,
                        checkpointURL,
                        metadataURL
                    );

                    console.log("Created recognizer, loading model...");
                    await recognizer.ensureModelLoaded();
                    console.log("Model loaded successfully");
                    return recognizer;
                } catch (error) {
                    console.error("Detailed error loading model:", error);
                    console.error("Error stack:", error.stack);
                    document.getElementById('status').innerHTML = 
                        `<span style="color: red;">Error: ${error.message}</span>`;
                    return null;
                }
            }

            async function startListening() {
                if (!recognizer) {
                    document.getElementById('status').textContent = "Loading model...";
                    recognizer = await createModel();
                    if (!recognizer) return;
                }

                const classLabels = recognizer.wordLabels();
                const labelContainer = document.getElementById("label-container");
                labelContainer.innerHTML = '';

                for (let i = 0; i < classLabels.length; i++) {
                    const div = document.createElement("div");
                    div.className = "prediction-item";
                    div.id = `prediction-${i}`;
                    labelContainer.appendChild(div);
                }

                recognizer.listen(result => {
                    const scores = result.scores;
                    const timestamp = new Date().toLocaleTimeString();
                    let maxScore = 0;
                    let maxIndex = 0;

                    // Update current predictions
                    for (let i = 0; i < classLabels.length; i++) {
                        const confidence = (scores[i] * 100).toFixed(1);
                        const predictionDiv = document.getElementById(`prediction-${i}`);
                        predictionDiv.innerHTML = `${classLabels[i]}: ${confidence}%`;

                        // Highlight high confidence predictions
                        if (scores[i] > 0.7) {
                            predictionDiv.classList.add('high-confidence');
                        } else {
                            predictionDiv.classList.remove('high-confidence');
                        }

                        if (scores[i] > maxScore) {
                            maxScore = scores[i];
                            maxIndex = i;
                        }
                    }

                    // Log prediction if confidence is high
                    if (maxScore > 0.75) {
                        logPrediction(classLabels[maxIndex], maxScore, timestamp);

                        // Send to Flask API
                        sendPredictionToAPI({
                            label: classLabels[maxIndex],
                            confidence: maxScore,
                            timestamp: timestamp,
                            all_scores: scores.map((score, idx) => ({
                                label: classLabels[idx],
                                confidence: score
                            }))
                        });
                    }
                }, {
                    includeSpectrogram: true,
                    probabilityThreshold: 0.75,
                    invokeCallbackOnNoiseAndUnknown: true,
                    overlapFactor: 0.50
                });

                isListening = true;
                document.getElementById('startBtn').disabled = true;
                document.getElementById('stopBtn').disabled = false;
                document.getElementById('status').className = 'status listening';
                document.getElementById('status').textContent = 'Status: Listening for audio...';
            }

            function stopListening() {
                if (recognizer && isListening) {
                    recognizer.stopListening();
                    isListening = false;
                    document.getElementById('startBtn').disabled = false;
                    document.getElementById('stopBtn').disabled = true;
                    document.getElementById('status').className = 'status stopped';
                    document.getElementById('status').textContent = 'Status: Stopped listening';
                }
            }

            function logPrediction(label, confidence, timestamp) {
                const logContainer = document.getElementById('log-container');
                const logEntry = document.createElement('div');
                logEntry.innerHTML = `
                    <strong>${timestamp}</strong>: Detected "${label}" 
                    (${(confidence * 100).toFixed(1)}% confidence)
                `;
                logEntry.style.margin = '5px 0';
                logEntry.style.padding = '5px';
                logEntry.style.backgroundColor = 'white';
                logEntry.style.borderRadius = '3px';

                logContainer.insertBefore(logEntry, logContainer.firstChild);

                // Keep only last 20 entries
                while (logContainer.children.length > 20) {
                    logContainer.removeChild(logContainer.lastChild);
                }
            }

            async function sendPredictionToAPI(prediction) {
                try {
                    const response = await fetch('/api/audio-prediction', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify(prediction)
                    });

                    if (!response.ok) {
                        console.warn('Failed to log prediction to API');
                    }
                } catch (error) {
                    console.warn('Error sending prediction to API:', error);
                }
            }

            // Initialize on page load
            window.addEventListener('load', () => {
                console.log('Audio classification page loaded');
            });
        </script>
    </body>
    </html>
    """
    return html


@app.route('/api/model-debug', methods=['GET'])
def debug_model_files():
    """Debug endpoint to check model files"""
    import os
    model_dir = 'my_model'

    try:
        files = os.listdir(model_dir)
        file_info = {}

        for file in files:
            file_path = os.path.join(model_dir, file)
            file_info[file] = {
                'exists': os.path.exists(file_path),
                'size': os.path.getsize(file_path) if os.path.exists(file_path) else 0,
                'url': f'/my_model/{file}'
            }

        return jsonify({
            'model_directory': model_dir,
            'files': file_info,
            'expected_files': ['model.json', 'metadata.json', 'weights.bin']
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/audio-prediction', methods=['POST'])
def log_audio_prediction():
    """API endpoint to log audio predictions"""
    try:
        data = request.get_json()

        # Log prediction (you could save to database here)
        print(f"Audio Prediction: {data['label']} ({data['confidence']:.3f}) at {data['timestamp']}")

        # You could store this in your database like:
        # prediction = AudioPrediction(
        #     label=data['label'],
        #     confidence=data['confidence'],
        #     timestamp=data['timestamp']
        # )
        # db.session.add(prediction)
        # db.session.commit()

        return jsonify({
            'status': 'success',
            'message': 'Prediction logged successfully'
        }), 200

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


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

        <div style="margin: 20px 0; padding: 15px; background: #e9ecef; border-radius: 5px;">
            <h3>🎤 Audio Classification</h3>
            <p>Try our Teachable Machine audio classifier:</p>
            <a href="/audio-classifier" style="display: inline-block; padding: 10px 20px; background: #28a745; color: white; text-decoration: none; border-radius: 5px;">Open Audio Classifier</a>
        </div>

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

@app.route('/framework-demo')
def framework_demo():
    """Embedded framework demo page"""
    import os
    
    # Use the internal network address that's confirmed working in console logs
    # Both Flask (172.31.125.66:5000) and Astro (172.31.125.66:3000) are on same network
    astro_url = "http://172.31.125.66:3000"
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>JavaScript Framework Demo</title>
        <style>
            body {{ margin: 0; padding: 20px; font-family: Arial, sans-serif; }}
            .header {{ background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
            .iframe-container {{ width: 100%; height: 80vh; border: 1px solid #ddd; border-radius: 8px; overflow: hidden; position: relative; }}
            iframe {{ width: 100%; height: 100%; border: none; }}
            .info {{ background: #e3f2fd; padding: 15px; border-radius: 8px; margin-bottom: 20px; }}
            .connection-status {{ background: #fff3cd; padding: 10px; border-radius: 8px; margin-bottom: 20px; border-left: 4px solid #ffc107; }}
            .loading {{ position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); text-align: center; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>JavaScript Framework Integration Demo</h1>
            <p>This demonstrates how your Teachable Machine concepts can be extended with modern JavaScript frameworks.</p>
            <a href="/" style="color: #007bff; text-decoration: none;">← Back to Main App</a>
        </div>

        <div class="connection-status">
            <strong>Connection Status:</strong> 
            <span id="status">Testing connection to Astro server...</span>
        </div>

        <div class="info">
            <strong>Integration Notes:</strong>
            <ul>
                <li>The demo below shows how frameworks simplify complex interactions</li>
                <li>Your Flask app provides the API backend</li>
                <li>The framework handles the interactive frontend</li>
                <li>Both can work together seamlessly</li>
            </ul>
        </div>

        <div class="iframe-container">
            <div class="loading" id="loading">
                <p>🔄 Loading Astro Framework Demo...</p>
                <p><small>If this takes too long, the Astro server might not be running.</small></p>
            </div>
            <iframe src="{astro_url}" title="JavaScript Framework Demo" onload="document.getElementById('loading').style.display='none'; document.getElementById('status').textContent='Connected to Astro server';" onerror="document.getElementById('status').textContent='Failed to connect to Astro server';"></iframe>
        </div>

        <script>
            // Test connection and update status
            setTimeout(() => {{
                fetch('{astro_url}')
                    .then(response => {{
                        if (response.ok) {{
                            document.getElementById('status').textContent = 'Connected to Astro server ✅';
                            document.querySelector('.connection-status').style.background = '#d4edda';
                            document.querySelector('.connection-status').style.borderColor = '#28a745';
                        }} else {{
                            throw new Error('Server responded with error');
                        }}
                    }})
                    .catch(error => {{
                        document.getElementById('status').textContent = 'Cannot connect to Astro server ❌ - Make sure both servers are running';
                        document.querySelector('.connection-status').style.background = '#f8d7da';
                        document.querySelector('.connection-status').style.borderColor = '#dc3545';
                    }});
            }}, 2000);
        </script>
    </body>
    </html>
    """

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)