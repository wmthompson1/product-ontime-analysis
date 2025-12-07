This project uses npm scripts defined in package.json for local development. Here's what's available:

## Quick Start
1. Run `npm run setup` to install all Node.js and Python dependencies
2. Create a `.env` file with these variables:
   - DATABASE_URL (PostgreSQL connection string)
   - OPENAI_API_KEY
   - TAVILY_API_KEY
   - HUGGINGFACE_TOKEN

## Development Commands
- `npm run dev` - Start Flask (port 5000) + Astro (port 4321) together
- `npm run dev:all` - Start Flask + Astro + HF Space (port 8000)
- `npm run flask` - Flask backend only
- `npm run astro` - Astro frontend only
- `npm run hf-space` - Hugging Face MCP server only

## Testing
- `npm run test:api` - Test Flask API health endpoint
- `npm run test:mcp` - Test HF Space MCP discovery endpoint
- `npm run hf-space:test` - Run full MCP test suite

## Setup Commands
- `npm run setup:node` - Install Node dependencies only
- `npm run setup:python` - Install Python dependencies only
- `npm run clean` - Remove node_modules and cache files

Port allocation: Flask=5000, Astro=4321, HF Space=8000
