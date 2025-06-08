# Flask Primer: A 4-Page Getting Started Guide

## Page 1: Introduction and Basic Setup

### What is Flask?
Flask is a lightweight Python web framework that makes it easy to build web applications. It's called a "micro" framework because it doesn't require particular tools or libraries, giving you flexibility in how you structure your application.

### Why Choose Flask?
- **Simple and lightweight**: Minimal setup required
- **Flexible**: You choose your components
- **Pythonic**: Follows Python conventions
- **Great for beginners**: Easy to learn and understand
- **Scalable**: Can grow from simple to complex applications

### Basic Installation and Setup
```bash
# Install Flask
pip install flask

# Create your first app
touch app.py
```

### Your First Flask Application
```python
from flask import Flask

app = Flask(__name__)

@app.route('/')
def hello_world():
    return 'Hello, World!'

if __name__ == '__main__':
    app.run(debug=True)
```

### Running Your App
```bash
python app.py
```
Visit `http://localhost:5000` in your browser to see your app!

### Key Concepts
- **Routes**: URLs that your app responds to
- **View functions**: Python functions that handle requests
- **Templates**: HTML files that can include Python variables
- **Static files**: CSS, JavaScript, images that don't change

---

## Page 2: Routes, Templates, and Static Files

### Understanding Routes
Routes define what happens when users visit different URLs:

```python
from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def home():
    return 'Home Page'

@app.route('/about')
def about():
    return 'About Page'

@app.route('/user/<name>')
def user_profile(name):
    return f'Hello, {name}!'

@app.route('/post/<int:post_id>')
def show_post(post_id):
    return f'Post #{post_id}'
```

### HTTP Methods
```python
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Handle form submission
        return 'Processing login...'
    else:
        # Show login form
        return 'Login form here'
```

### Templates with Jinja2
Create a `templates/` folder and add HTML files:

**templates/base.html**:
```html
<!DOCTYPE html>
<html>
<head>
    <title>{% block title %}{% endblock %}</title>
</head>
<body>
    <nav>
        <a href="/">Home</a> | 
        <a href="/about">About</a>
    </nav>
    <main>
        {% block content %}{% endblock %}
    </main>
</body>
</html>
```

**templates/index.html**:
```html
{% extends "base.html" %}

{% block title %}Home Page{% endblock %}

{% block content %}
    <h1>Welcome, {{ username }}!</h1>
    <ul>
    {% for item in items %}
        <li>{{ item }}</li>
    {% endfor %}
    </ul>
{% endblock %}
```

**Using templates in Python**:
```python
@app.route('/')
def home():
    return render_template('index.html', 
                         username='John', 
                         items=['Apple', 'Banana', 'Orange'])
```

### Static Files
Create a `static/` folder for CSS, JavaScript, and images:

```html
<!-- In your template -->
<link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
<script src="{{ url_for('static', filename='script.js') }}"></script>
```

---

## Page 3: Forms, Requests, and Sessions

### Handling Forms
```python
from flask import Flask, request, render_template, redirect, url_for

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        message = request.form['message']
        
        # Process the form data
        print(f"Message from {name} ({email}): {message}")
        
        return redirect(url_for('thank_you'))
    
    return render_template('contact.html')

@app.route('/thank-you')
def thank_you():
    return 'Thank you for your message!'
```

**templates/contact.html**:
```html
{% extends "base.html" %}

{% block content %}
<form method="POST">
    <label>Name: <input type="text" name="name" required></label><br>
    <label>Email: <input type="email" name="email" required></label><br>
    <label>Message: <textarea name="message" required></textarea></label><br>
    <button type="submit">Send Message</button>
</form>
{% endblock %}
```

### Working with Sessions
Sessions let you store user data across requests:

```python
from flask import session

app.secret_key = 'your-secret-key-here'  # Required for sessions

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    if valid_login(username):  # Your validation logic
        session['username'] = username
        return redirect(url_for('dashboard'))
    return 'Invalid login'

@app.route('/dashboard')
def dashboard():
    if 'username' in session:
        return f'Welcome back, {session["username"]}!'
    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('home'))
```

### Request Data
```python
# URL parameters: /search?q=python
search_query = request.args.get('q')

# Form data
username = request.form.get('username')

# JSON data
data = request.get_json()

# Files
uploaded_file = request.files['file']

# Headers
user_agent = request.headers.get('User-Agent')
```

### Flash Messages
```python
from flask import flash

@app.route('/save', methods=['POST'])
def save_data():
    # Save logic here
    flash('Data saved successfully!', 'success')
    return redirect(url_for('dashboard'))
```

**In templates**:
```html
{% with messages = get_flashed_messages(with_categories=true) %}
    {% if messages %}
        {% for category, message in messages %}
            <div class="alert alert-{{ category }}">{{ message }}</div>
        {% endfor %}
    {% endif %}
{% endwith %}
```

---

## Page 4: Database Integration and Best Practices

### Database Setup with SQLAlchemy
```python
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///example.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Define a model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    
    def __repr__(self):
        return f'<User {self.username}>'

# Create tables
with app.app_context():
    db.create_all()
```

### Database Operations
```python
@app.route('/users')
def list_users():
    users = User.query.all()
    return render_template('users.html', users=users)

@app.route('/user/create', methods=['POST'])
def create_user():
    username = request.form['username']
    email = request.form['email']
    
    user = User(username=username, email=email)
    db.session.add(user)
    db.session.commit()
    
    flash('User created successfully!')
    return redirect(url_for('list_users'))

@app.route('/user/<int:user_id>')
def show_user(user_id):
    user = User.query.get_or_404(user_id)
    return render_template('user.html', user=user)
```

### Project Structure Best Practices
```
my_flask_app/
├── app.py              # Main application
├── models.py           # Database models
├── config.py           # Configuration settings
├── requirements.txt    # Dependencies
├── templates/          # HTML templates
│   ├── base.html
│   ├── index.html
│   └── users.html
├── static/            # CSS, JS, images
│   ├── css/
│   ├── js/
│   └── img/
└── instance/          # Instance-specific files
```

### Configuration Management
**config.py**:
```python
import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///app.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False
```

**Using configuration**:
```python
app.config.from_object('config.DevelopmentConfig')
```

### Error Handling
```python
@app.errorhandler(404)
def page_not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500
```

### Security Best Practices
1. **Always use HTTPS in production**
2. **Set a strong SECRET_KEY**
3. **Validate and sanitize user input**
4. **Use environment variables for sensitive data**
5. **Implement proper authentication and authorization**

### Deployment Preparation
```python
# requirements.txt
Flask==2.3.3
Flask-SQLAlchemy==3.0.5

# For production, add:
gunicorn==21.2.0
```

### Next Steps
- Learn about **Blueprints** for organizing larger applications
- Explore **Flask extensions** (Flask-Login, Flask-Mail, Flask-Admin)
- Study **API development** with Flask-RESTful
- Practice **testing** with pytest
- Learn about **deployment** options (Heroku, AWS, DigitalOcean)

### Useful Resources
- Official Flask Documentation: https://flask.palletsprojects.com/
- Flask Mega-Tutorial: https://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-i-hello-world
- Real Python Flask Tutorials: https://realpython.com/tutorials/flask/

---

**Remember**: Flask's philosophy is to start simple and add complexity as needed. This primer covers the fundamentals - practice building small projects to reinforce these concepts!