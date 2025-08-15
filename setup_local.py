#!/usr/bin/env python3
"""
Local Setup Script for Product On-Time Analysis Tool
Run this script to install dependencies and set up the application locally
"""

import subprocess
import sys
import os

def install_package(package):
    """Install a package using pip"""
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

def setup_environment():
    """Set up the local environment"""
    print("Setting up Product On-Time Analysis Tool locally...")
    print("=" * 50)
    
    # List of required packages
    packages = [
        "Flask==3.0.0",
        "Flask-SQLAlchemy==3.1.1", 
        "psycopg2-binary==2.9.9",
        "SQLAlchemy==2.0.23",
        "requests==2.31.0",
        "beautifulsoup4==4.12.2",
        "lxml==4.9.3",
        "trafilatura==1.6.4",
        "Flask-Migrate==4.0.5"
    ]
    
    # Install packages
    print("Installing required packages...")
    for package in packages:
        try:
            print(f"Installing {package}...")
            install_package(package)
        except subprocess.CalledProcessError:
            print(f"Warning: Could not install {package}")
    
    # Create local configuration
    print("\nCreating local configuration...")
    local_config = '''# Local Configuration for Product On-Time Analysis
import os

# Use SQLite for local development (no database server required)
os.environ['DATABASE_URL'] = 'sqlite:///local_analysis.db'
os.environ['FLASK_SECRET_KEY'] = 'local-development-key-change-in-production'

print("Local configuration loaded - using SQLite database")
'''
    
    with open('local_config.py', 'w') as f:
        f.write(local_config)
    
    # Initialize database
    print("Initializing local database...")
    try:
        import local_config  # Load the configuration
        from main import app, db
        with app.app_context():
            db.create_all()
            print("✅ Database initialized successfully!")
    except Exception as e:
        print(f"Warning: Could not initialize database: {e}")
        print("You may need to run this manually after installation")
    
    print("\n" + "=" * 50)
    print("Setup Complete!")
    print("\nTo run your application:")
    print("1. python main.py")
    print("2. Open browser to http://localhost:5000")
    print("3. Click 'On Time Delivery Analysis' to start")
    print("\nYour analysis tool is ready for local use!")

if __name__ == "__main__":
    setup_environment()