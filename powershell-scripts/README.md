# PowerShell on Replit

This directory contains PowerShell scripts demonstrating various capabilities of PowerShell Core on the Replit platform.

## 🚀 Quick Start

### Run a Script

```bash
pwsh -File powershell-scripts/01_hello_world.ps1
```

Or make it executable and run directly:

```bash
chmod +x powershell-scripts/01_hello_world.ps1
./powershell-scripts/01_hello_world.ps1
```

### Interactive PowerShell

Start an interactive PowerShell session:

```bash
pwsh
```

Then you can run cmdlets directly:

```powershell
PS> Get-Date
PS> Get-ChildItem
PS> Write-Host "Hello from PowerShell!" -ForegroundColor Green
```

## 📁 Example Scripts

### 01_hello_world.ps1
Basic PowerShell script demonstrating:
- Colored output with `Write-Host`
- System information (`$PSVersionTable`)
- Environment variables
- Platform detection (`$IsLinux`)

**Run:**
```bash
pwsh -File powershell-scripts/01_hello_world.ps1
```

### 02_file_operations.ps1
File system operations:
- Creating directories
- Writing files
- Reading files
- File metadata

**Run:**
```bash
pwsh -File powershell-scripts/02_file_operations.ps1
```

### 03_data_processing.ps1
Data processing and analysis:
- Creating custom objects
- Filtering and grouping data
- Statistical calculations
- CSV export

**Run:**
```bash
pwsh -File powershell-scripts/03_data_processing.ps1
```

## 🛠️ PowerShell Capabilities

### What Works Well on Replit (Linux)

✅ **Core Cmdlets**: Get-ChildItem, Set-Location, Copy-Item, etc.  
✅ **Data Processing**: Where-Object, ForEach-Object, Select-Object  
✅ **File Operations**: Import-Csv, Export-Csv, Get-Content, Set-Content  
✅ **Text Processing**: String manipulation, regex, formatting  
✅ **Custom Objects**: [PSCustomObject], hashtables, arrays  
✅ **API Calls**: Invoke-RestMethod, Invoke-WebRequest  
✅ **JSON/XML**: ConvertTo-Json, ConvertFrom-Json  

### Limitations (Linux vs Windows)

⚠️ **Windows-specific cmdlets** won't work (registry, Windows services, etc.)  
⚠️ **Some PowerShell Gallery modules** may have Windows dependencies  
✅ **Cross-platform modules** work fine  

## 📊 Use Cases for Manufacturing/Business

### Data Processing
- CSV file manipulation
- Log analysis
- Report generation
- Data transformation

### Automation
- File backup scripts
- Data validation
- ETL pipelines
- Scheduled tasks

### Integration
- REST API calls
- Database queries (with appropriate modules)
- Web scraping
- Email automation

## 🔧 Advanced Usage

### Installing PowerShell Modules

```powershell
# Install a module from PowerShell Gallery
Install-Module -Name PSReadLine -Scope CurrentUser

# List installed modules
Get-Module -ListAvailable

# Import a module
Import-Module PSReadLine
```

### Creating Your Own Scripts

1. Create a new `.ps1` file in this directory
2. Add the shebang: `#!/usr/bin/env pwsh`
3. Write your PowerShell code
4. Make it executable: `chmod +x your-script.ps1`
5. Run it: `./powershell-scripts/your-script.ps1`

### Setting Up a Workflow

You can add a PowerShell workflow to run your main script automatically:

1. In Replit, configure a workflow with:
   - **Name**: PowerShell App
   - **Command**: `pwsh -File powershell-scripts/your-script.ps1`

## 📚 Resources

- [PowerShell Documentation](https://docs.microsoft.com/powershell/)
- [PowerShell Gallery](https://www.powershellgallery.com/)
- [PowerShell on GitHub](https://github.com/PowerShell/PowerShell)

## 💡 Tips

1. **Use `-NoProfile`** for faster script execution:
   ```bash
   pwsh -NoProfile -File script.ps1
   ```

2. **Check syntax** before running:
   ```bash
   pwsh -NoProfile -Command "Get-Command -Syntax Write-Host"
   ```

3. **Error handling** with try/catch:
   ```powershell
   try {
       Get-Content "nonexistent.txt"
   } catch {
       Write-Host "Error: $_" -ForegroundColor Red
   }
   ```

4. **Parameter support** for scripts:
   ```powershell
   param(
       [string]$InputFile,
       [int]$Count = 10
   )
   ```

Happy scripting with PowerShell on Replit! 🎉
