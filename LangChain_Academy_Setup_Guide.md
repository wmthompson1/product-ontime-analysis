# LangChain Academy Ambient Agents - Installation Guide

## Overview

This guide helps you install and explore LangChain Academy's official ambient agents code alongside your existing Frank Kane Advanced RAG implementation. Perfect for extending your Berkeley Haas capstone with cutting-edge agent patterns.

## Quick Installation Options

### Option 1: Official LangChain Academy Repository
```bash
# Clone the official ambient agents repository
git clone https://github.com/langchain-ai/agents-from-scratch.git
cd agents-from-scratch

# Install in development mode (recommended for exploration)
pip install -e .

# Or install specific dependencies
pip install langchain langgraph langchain-openai langsmith
```

### Option 2: Alternative Academy Repository
```bash
# Alternative official repository
git clone https://github.com/langchain-ai/ambient-agent-101.git
cd ambient-agent-101

# Follow same installation pattern
pip install -e .
```

## Environment Configuration

Create a `.env` file with LangChain Academy standard variables:

```bash
# LangSmith Configuration (as per academy docs)
LANGSMITH_API_KEY=your_langsmith_api_key
LANGSMITH_TRACING=true
LANGSMITH_PROJECT="ambient-agent-workshop"
LANGSMITH_ENDPOINT=https://api.smith.langchain.com

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key

# Optional: Anthropic for Claude models
ANTHROPIC_API_KEY=your_anthropic_api_key
```

## Core Dependencies (Academy Standard)

```bash
# Essential LangChain Academy packages
pip install langchain>=0.1.0
pip install langgraph>=0.0.40
pip install langsmith>=0.0.80
pip install langchain-openai>=0.0.8

# For email integration (advanced)
pip install google-auth google-auth-oauthlib google-auth-httplib2
pip install google-api-python-client

# For search tools
pip install tavily-python
```

## Project Structure (Academy Pattern)

Your integration would follow this structure:
```
project/
├── src/
│   ├── email_assistant/
│   │   ├── __init__.py
│   │   ├── email_assistant.py          # Basic agent
│   │   ├── email_assistant_hitl.py     # Human-in-the-loop
│   │   ├── email_assistant_memory.py   # Memory integration
│   │   └── tools.py                    # Agent tools
│   └── manufacturing_assistant/        # Your adaptation
│       ├── manufacturing_agent.py      # Manufacturing-focused agent
│       ├── manufacturing_tools.py      # Manufacturing tools
│       └── ambient_monitor.py          # Ambient monitoring
├── tests/
│   └── test_notebooks.py
├── notebooks/                          # Jupyter exploration
├── .env                                # Environment variables
└── pyproject.toml
```

## Integration with Your Frank Kane Implementation

### Connecting Ambient Agents with Advanced RAG

```python
# In your 007_Entry_Point_Ambient_Agents.py
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from langchain_openai import ChatOpenAI

# Import your existing Frank Kane components
from Entry_Point_001_few_shot import FewShotSQLGenerator
from 004_Entry_Point_Kane_Complete_RAG import FrankKaneCompleteRAG

class IntegratedManufacturingAgent:
    def __init__(self):
        # LangGraph agent for ambient monitoring
        self.memory = MemorySaver()
        self.model = ChatOpenAI(model="gpt-4")
        
        # Your Frank Kane Advanced RAG system
        self.rag_system = FrankKaneCompleteRAG()
        
        # Create integrated agent
        self.agent = create_react_agent(
            self.model,
            tools=[self.manufacturing_query_tool],
            checkpointer=self.memory
        )
    
    def manufacturing_query_tool(self, query: str) -> str:
        """Tool that uses your Frank Kane RAG system"""
        result = self.rag_system.generate_ragas_enhanced_sql(query)
        return result["enhanced_result"]["explanation"]
```

## Testing Your Installation

### Basic Test
```python
# Test basic LangChain Academy patterns
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI

model = ChatOpenAI(model="gpt-3.5-turbo")
agent = create_react_agent(model, [])

# Simple test
config = {"configurable": {"thread_id": "test_session"}}
response = agent.invoke(
    {"messages": [{"role": "user", "content": "Hello"}]}, 
    config
)
print(response)
```

### Manufacturing Integration Test
```python
# Test your manufacturing ambient agent
from 007_Entry_Point_Ambient_Agents import ManufacturingAmbientAgent

agent = ManufacturingAmbientAgent()
agent.start_ambient_monitoring()
```

## LangChain Academy Course Progression

The official course follows this 4-stage progression:

### 1. Basic Agent (`email_assistant.py`)
- Simple tool calling
- Email triage and response
- Foundation patterns

### 2. Human-in-the-Loop (`email_assistant_hitl.py`)
- Review patterns for sensitive actions
- Agent Inbox interface
- Approval workflows

### 3. Memory Integration (`email_assistant_memory.py`)
- LangGraph Store for persistent memories
- Learning from user feedback
- Pattern recognition

### 4. Production Integration (`email_assistant_gmail.py`)
- Full Gmail API integration
- Production deployment
- Scalable architecture

## Adaptation for Manufacturing (Your Innovation)

You've already implemented these patterns for manufacturing:

### Manufacturing-Specific Adaptations
- **Quality Alerts** → Email notifications
- **Equipment Monitoring** → Ambient sensing
- **Supply Chain Events** → Proactive management
- **Safety Protocols** → Critical decision points

### Your Berkeley Haas Value-Add
- Frank Kane Advanced RAG integration
- RAGAS evaluation for quality assurance
- Manufacturing domain expertise
- Professional LangSmith monitoring

## Next Steps for Exploration

### Immediate Next Steps
1. **Clone Official Repo**: `git clone https://github.com/langchain-ai/agents-from-scratch.git`
2. **Run Academy Examples**: Test email assistant patterns
3. **Adapt Patterns**: Apply to your manufacturing use cases
4. **Integrate Systems**: Connect with your Frank Kane RAG implementation

### Advanced Exploration
1. **LangGraph Store**: Persistent memory patterns
2. **Multi-Agent Systems**: Coordinate multiple manufacturing agents
3. **Production Deployment**: Scale your ambient monitoring
4. **Custom Tools**: Build manufacturing-specific agent tools

## Resources for Continued Learning

### Official LangChain Academy
- **Course**: [Building Ambient Agents with LangGraph](https://academy.langchain.com/courses/ambient-agents)
- **GitHub**: [agents-from-scratch](https://github.com/langchain-ai/agents-from-scratch)
- **Documentation**: [LangGraph Docs](https://langchain-ai.github.io/langgraph/)

### Community Examples
- **Email Automation**: [Multi-agent customer support](https://github.com/kaymen99/langgraph-email-automation)
- **Production Patterns**: [Top 5 LangGraph Agents](https://blog.langchain.com/top-5-langgraph-agents-in-production-2024/)

### Your Project Integration
- Your implementation in `007_Entry_Point_Ambient_Agents.py` already demonstrates core patterns
- Ready for integration with official LangChain Academy code
- Perfect foundation for Berkeley Haas capstone extension

## Installation Success Indicators

You'll know your installation is working when:
- ✅ LangSmith tracing appears in your dashboard
- ✅ Basic agent patterns execute successfully  
- ✅ Your manufacturing agents integrate with LangGraph
- ✅ Memory patterns learn from manufacturing events
- ✅ Human-in-the-loop workflows function properly

Your systematic Entry Point approach (001-007) now provides the complete spectrum from educational demos to production-ready ambient agents - exactly what's needed for advanced Berkeley Haas capstone work.