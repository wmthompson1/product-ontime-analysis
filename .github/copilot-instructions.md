# GitHub Copilot Instructions

## Project Overview
This is a Python-based project focused on data analysis, AI/LangChain applications, and product delivery/on-time analysis. The project includes various entry points for different AI workflows, data processing pipelines, and analysis tools.

## Code Style and Standards

### Python Style
- Follow PEP 8 style guidelines for Python code
- Use type hints where appropriate to improve code clarity
- Use descriptive variable and function names
- Add docstrings to all functions, classes, and modules using Google-style docstrings
- Keep functions focused and modular

### File Organization
- Entry point files follow the naming pattern `{number}_Entry_Point_{description}.py`
- Test files should be prefixed with `test_`
- Keep related functionality together in appropriately named modules

## Dependencies and Environment

### Python Version
- Requires Python >= 3.11

### Key Dependencies
- LangChain and related AI libraries (OpenAI, NLTK, etc.)
- Data analysis: pandas, numpy, openpyxl, xlrd
- Web frameworks: Flask, Flask-SQLAlchemy, Flask-Migrate
- Database: PostgreSQL (psycopg2-binary), ArangoDB (nx-arangodb)
- Web scraping: requests, beautifulsoup4, trafilatura, lxml
- Utilities: python-dotenv for environment variables

### Installing Dependencies
- Use `pip install -r requirements.txt` to install dependencies
- Environment variables should be stored in `.env` file (never commit secrets)

## Testing and Quality

### Testing Approach
- Test files are located in the root directory with `test_` prefix
- Write unit tests for new functionality
- Run tests before committing changes

### Documentation
- Document complex algorithms and business logic
- Include usage examples in docstrings
- Keep README files up to date when adding new features

## AI/LangChain Development

### LangChain Patterns
- Use structured approaches for RAG (Retrieval-Augmented Generation) implementations
- Follow established patterns for graph-based workflows
- Implement proper error handling and logging for AI operations
- Use environment variables for API keys (OpenAI, etc.)

### Data Processing
- Handle CSV and Excel files using pandas for consistency
- Implement proper data validation and error handling
- Use appropriate data cleansing techniques for manufacturing/delivery data

## Security Best Practices

### API Keys and Secrets
- Never hardcode API keys, tokens, or credentials
- Always use environment variables via python-dotenv
- Add `.env` files to `.gitignore`

### Data Handling
- Validate and sanitize user inputs
- Use parameterized queries for database operations
- Be cautious with file uploads and external data sources

## Database Operations

### SQL Best Practices
- Use SQLAlchemy ORM for database operations when possible
- Always use parameterized queries to prevent SQL injection
- Implement proper transaction handling

### Graph Databases
- Use nx-arangodb for graph operations
- Follow NetworkX patterns for graph data structures

## Deployment and Configuration

### Replit Deployment
- The project includes Replit configuration files
- Follow deployment guides in markdown documentation files

### Flask Applications
- Use Flask best practices for web applications
- Implement proper error handling and logging
- Use Flask-Migrate for database migrations

## Common Patterns

### Entry Point Scripts
- Entry point scripts should be executable and include proper main guards
- Include clear usage instructions in docstrings
- Handle command-line arguments appropriately

### Data Analysis Scripts
- Use pandas for data manipulation
- Include clear statistical methods documentation
- Provide sample data generation when appropriate

## File Patterns to Note
- `.py` files: Python source code
- `.txt` files: Data files or documentation
- `.csv` files: Sample data for analysis
- `.json` files: Configuration or data files
- `.md` files: Documentation (markdown)

## Naming Conventions
- Use snake_case for Python module files, variables, and functions
- Use PascalCase for class names
- Use UPPERCASE for constants
- Configuration files and scripts may follow their respective conventions (e.g., `.md` for markdown, `.json` for JSON)

## Error Handling
- Use try-except blocks for operations that may fail
- Provide meaningful error messages
- Log errors appropriately for debugging

## Version Control
- Write clear, descriptive commit messages
- Keep commits focused on a single logical change
- Don't commit temporary files, build artifacts, or sensitive data
