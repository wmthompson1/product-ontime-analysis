# Local Installation Guide: Product On-Time Analysis Tool
## Running Your Statistical Analysis Application on Your Local Machine

---

## Prerequisites

### Required Software
1. **Python 3.11** or higher
   - Download from: https://www.python.org/downloads/
   - During installation, check "Add Python to PATH"

2. **Git** (for downloading the project)
   - Download from: https://git-scm.com/downloads
   - Or download as ZIP file from Replit

3. **Text Editor** (optional but recommended)
   - VS Code: https://code.visualstudio.com/
   - PyCharm Community: https://www.jetbrains.com/pycharm/

### System Requirements
- Operating System: Windows 10+, macOS 10.14+, or Linux
- RAM: 4GB minimum (8GB recommended)
- Storage: 500MB free space
- Internet connection (for initial setup only)

---

## Installation Methods

### Method 1: Download from Replit (Recommended)

1. **Download Project Files**
   - In your Replit workspace, click the three dots menu (⋯)
   - Select "Download as ZIP"
   - Extract the ZIP file to your desired location (e.g., `C:\Projects\OnTimeAnalysis`)

2. **Navigate to Project Directory**
   ```bash
   cd C:\Projects\OnTimeAnalysis
   # Or on Mac/Linux: cd /path/to/OnTimeAnalysis
   ```

### Method 2: Git Clone (Advanced Users)

```bash
# If your Replit has Git integration
git clone [your-replit-git-url] OnTimeAnalysis
cd OnTimeAnalysis
```

---

## Setup Instructions

### Step 1: Create Virtual Environment (Recommended)

**Windows:**
```cmd
python -m venv venv
venv\Scripts\activate
```

**Mac/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 2: Install Dependencies

```bash
pip install flask flask-sqlalchemy psycopg2-binary sqlalchemy requests beautifulsoup4 lxml trafilatura
```

**Or if you have the requirements file:**
```bash
pip install -r requirements.txt
```

### Step 3: Database Setup Options

**Option A: SQLite (Simplest - No Database Server Required)**

Create a file called `local_config.py`:
```python
# local_config.py
import os
os.environ['DATABASE_URL'] = 'sqlite:///local_analysis.db'
os.environ['FLASK_SECRET_KEY'] = 'your-secret-key-here'
```

**Option B: PostgreSQL (Full Database)**
1. Install PostgreSQL locally
2. Create database: `createdb ontime_analysis`
3. Set environment variables:
```bash
export DATABASE_URL="postgresql://username:password@localhost/ontime_analysis"
export FLASK_SECRET_KEY="your-secret-key-here"
```

### Step 4: Initialize Database

```bash
python -c "
from main import app, db
with app.app_context():
    db.create_all()
    print('Database initialized successfully!')
"
```

---

## Running the Application

### Start the Application

```bash
python main.py
```

**Expected Output:**
```
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:5000
 * Running on http://[your-ip]:5000
 * Debug mode: on
```

### Access Your Application

Open your web browser and navigate to:
- **Local access:** http://localhost:5000
- **Network access:** http://127.0.0.1:5000

You'll see the main page with buttons for:
- Defect Rate Analysis
- **On Time Delivery Analysis** ← Your main tool
- Audio Classifier
- API Demo

---

## Using Your Analysis Tool

### Quick Test with Sample Data

1. Click **"On Time Delivery Analysis"**
2. Click **"Download Sample Data"** to get a CSV template
3. Click **"Upload and Analyze"** to test with sample data
4. Review the statistical analysis results

### Using Your Own Data

**CSV Format Required:**
```csv
date,total_received,received_late
2024-01-01,100,5
2024-01-02,95,3
2024-01-03,110,8
```

**Column Definitions:**
- `date`: Date of delivery measurement (YYYY-MM-DD)
- `total_received`: Total products received that day
- `received_late`: Number of products received late

### Analysis Results Include:
- Overall on-time delivery rate with 95% confidence interval
- Daily performance analysis identifying problem dates
- Margin of error validation (≤5% requirement)
- Z-test results for statistical significance
- Process control assessment for quality improvement

---

## File Structure

Your local installation includes:

```
OnTimeAnalysis/
├── main.py                      # Main Flask application
├── ontime_delivery_analyzer.py  # Statistical analysis engine
├── simple_defect_analyzer.py    # Defect rate analysis tool
├── models.py                    # Database models
├── templates/                   # Web interface templates
│   ├── base.html
│   └── index.html
├── sample_ontime_data.csv       # Sample data for testing
├── sample_defect_data.csv       # Sample defect data
└── local_analysis.db           # SQLite database (if using SQLite)
```

---

## Troubleshooting

### Common Issues and Solutions

**1. "Module not found" errors**
```bash
# Ensure virtual environment is activated
source venv/bin/activate  # Mac/Linux
# or
venv\Scripts\activate     # Windows

# Reinstall dependencies
pip install -r requirements.txt
```

**2. Database connection errors**
- Check DATABASE_URL environment variable
- Ensure PostgreSQL is running (if using PostgreSQL)
- Try SQLite option for simplicity

**3. Port already in use**
```python
# Edit main.py, change the last line to:
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)  # Changed port
```

**4. Permission errors on Windows**
- Run command prompt as Administrator
- Or use PowerShell with execution policy: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`

### Performance Optimization

**For Large Datasets:**
- Use PostgreSQL instead of SQLite
- Increase CSV file size limits in main.py
- Consider adding data caching for repeated analyses

**For Multiple Users:**
- Use PostgreSQL for concurrent access
- Consider deploying to local network server
- Set up proper authentication if needed

---

## Customization Options

### Modify Analysis Parameters

Edit `ontime_delivery_analyzer.py`:
```python
# Change confidence level (default 95%)
confidence_level = 0.99  # for 99% confidence

# Modify baseline rate expectation
baseline_rate = 0.95  # expect 95% on-time delivery
```

### Add Company Branding

Edit `templates/base.html`:
```html
<title>Your Company - Delivery Analysis</title>
<h1>Your Company Name - Statistical Analysis</h1>
```

### Export Results to Excel

Add to your analysis workflow:
```python
import pandas as pd

# After analysis, export results
df = pd.DataFrame(your_analysis_data)
df.to_excel('delivery_analysis_results.xlsx', index=False)
```

---

## Backup and Maintenance

### Regular Backups
```bash
# Backup SQLite database
cp local_analysis.db backup_$(date +%Y%m%d).db

# Backup CSV data
mkdir -p backups/csv_data
cp *.csv backups/csv_data/
```

### Updates and Improvements
- Keep your Python packages updated: `pip install --upgrade flask`
- Regularly backup your analysis data
- Consider version control with Git for code changes

### Security Considerations
- Change the default secret key in production
- Use environment variables for sensitive data
- Keep your Python installation updated for security patches

---

## Next Steps

1. **Test Installation**: Run the sample analysis to verify everything works
2. **Prepare Your Data**: Format your delivery data in the required CSV format
3. **Run Analysis**: Upload your data and generate statistical reports
4. **Integrate with Workflow**: Schedule regular analyses for your delivery data
5. **Advanced Features**: Explore additional statistical options and customizations

Your Product On-Time Analysis tool is now ready to run independently on your local machine, providing professional statistical analysis for your manufacturing delivery performance monitoring.