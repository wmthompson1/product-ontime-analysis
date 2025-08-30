"""
Advanced Semantic Layer for RAG-assisted SQL Generation with LangChain
Provides safe, context-aware natural language to SQL conversion
"""

import os
import re
import json
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

# LangChain imports (will work with existing dependencies)
try:
    from langchain.prompts import PromptTemplate, ChatPromptTemplate
    from langchain.schema import HumanMessage, SystemMessage
    try:
        from langchain_community.memory import ConversationBufferWindowMemory
    except ImportError:
        from langchain.memory import ConversationBufferWindowMemory
    try:
        from langchain_community.callbacks.manager import get_openai_callback
    except ImportError:
        from langchain.callbacks import get_openai_callback
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False

import openai
from schema_context import (
    SQL_SCHEMA_DESCRIPTION, 
    get_schema_context, 
    validate_sql_safety,
    schema_inspector
)

class QueryComplexity(Enum):
    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"

@dataclass
class QueryRequest:
    """Structured query request with context"""
    natural_language: str
    user_id: Optional[str] = None
    context: Optional[Dict] = None
    max_results: int = 100
    tables_hint: Optional[List[str]] = None

@dataclass
class QueryResult:
    """Structured query result with metadata"""
    sql_query: str
    parameters: List[Any]
    confidence_score: float
    complexity: QueryComplexity
    explanation: str
    safety_check: bool
    estimated_cost: Optional[float] = None

class SemanticLayer:
    """Advanced semantic layer with LangChain integration"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        openai.api_key = self.api_key
        
        # Simple conversation tracking (replaces deprecated memory)
        self.conversation_history = []
        self.max_history = 5  # Keep last 5 exchanges
        
        # Query templates for different complexity levels
        self.templates = self._initialize_templates()
        
        # Initialize vector store for schema similarity (if available)
        self.schema_embeddings = {}
        
    def _initialize_templates(self) -> Dict[str, str]:
        """Initialize prompt templates for different query types"""
        
        base_system = """You are an expert SQL assistant with deep knowledge of PostgreSQL and vector databases.
        
CRITICAL SAFETY RULES:
- Generate ONLY SELECT or WITH statements
- NEVER use DROP, DELETE, UPDATE, INSERT, ALTER, CREATE, TRUNCATE
- Use parameter placeholders (%s) for all user inputs
- Reference only tables in the provided schema
- Limit results appropriately to prevent resource exhaustion

Your responses must be valid PostgreSQL SQL that follows these constraints."""

        simple_template = """Schema Context:
{schema_context}

Generate a SQL query for: "{user_query}"

Response format:
SQL: [your SQL query with %s placeholders]
PARAMS: [list of parameter values]
EXPLANATION: [brief explanation of the query logic]
CONFIDENCE: [score 0.0-1.0]
"""

        complex_template = """Schema Context:
{schema_context}

Previous conversation context:
{conversation_history}

Complex query request: "{user_query}"

Additional context: {additional_context}

Consider:
1. Join requirements across multiple tables
2. Aggregation and grouping needs
3. Filtering and sorting requirements
4. Performance implications
5. Vector similarity search if relevant

Response format:
SQL: [optimized SQL query with %s placeholders]
PARAMS: [list of parameter values]
EXPLANATION: [detailed explanation including join strategy and performance notes]
CONFIDENCE: [score 0.0-1.0]
COMPLEXITY: [SIMPLE/MEDIUM/COMPLEX]
"""

        return {
            "simple": simple_template,
            "complex": complex_template,
            "system": base_system
        }
    
    def _classify_query_complexity(self, query: str) -> QueryComplexity:
        """Classify query complexity based on natural language patterns"""
        query_lower = query.lower()
        
        # Complex indicators
        complex_keywords = [
            'join', 'group by', 'having', 'subquery', 'aggregate', 
            'average', 'sum', 'count', 'similar to', 'embedding',
            'between', 'date range', 'multiple tables'
        ]
        
        # Medium indicators
        medium_keywords = [
            'where', 'and', 'or', 'order by', 'limit', 'filter',
            'sort', 'search', 'find', 'get all'
        ]
        
        complex_count = sum(1 for keyword in complex_keywords if keyword in query_lower)
        medium_count = sum(1 for keyword in medium_keywords if keyword in query_lower)
        
        if complex_count >= 2 or 'join' in query_lower:
            return QueryComplexity.COMPLEX
        elif complex_count >= 1 or medium_count >= 2:
            return QueryComplexity.MEDIUM
        else:
            return QueryComplexity.SIMPLE
    
    def _extract_table_hints(self, query: str) -> List[str]:
        """Extract potential table names from natural language"""
        table_hints = []
        query_lower = query.lower()
        
        # Known table patterns
        table_patterns = {
            r'\busers?\b': 'users',
            r'\bproducts?\b': 'products',
            r'\bcustomers?\b': 'customers',
            r'\borders?\b': 'orders',
            r'\baccounts?\b': 'accounts'
        }
        
        for pattern, table in table_patterns.items():
            if re.search(pattern, query_lower):
                table_hints.append(table)
        
        return list(set(table_hints))
    
    def _prepare_context(self, request: QueryRequest) -> Dict[str, str]:
        """Prepare context for prompt generation"""
        
        # Get schema context (enhanced if table hints available)
        if request.tables_hint:
            schema_context = get_schema_context(request.tables_hint)
        else:
            # Use table hints from NL analysis
            inferred_tables = self._extract_table_hints(request.natural_language)
            schema_context = get_schema_context(inferred_tables) if inferred_tables else SQL_SCHEMA_DESCRIPTION
        
        # Conversation history (simple tracking)
        conversation_history = ""
        if self.conversation_history:
            recent_exchanges = self.conversation_history[-2:]  # Last 2 exchanges
            conversation_history = "\n".join([
                f"Human: {exchange['query']}\nAssistant: Generated SQL for: {exchange['sql'][:100]}..."
                for exchange in recent_exchanges
            ])
        
        # Additional context
        additional_context = json.dumps(request.context or {}, indent=2)
        
        return {
            "schema_context": schema_context,
            "conversation_history": conversation_history,
            "additional_context": additional_context,
            "system_prompt": self.templates["system"]
        }
    
    def _generate_sql_with_openai(self, prompt: str) -> Dict[str, Any]:
        """Generate SQL using OpenAI with cost tracking"""
        
        try:
            if LANGCHAIN_AVAILABLE:
                with get_openai_callback() as cb:
                    response = openai.chat.completions.create(
                        model="gpt-4",
                        messages=[
                            {"role": "system", "content": self.templates["system"]},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.1,
                        max_tokens=1000
                    )
                    cost = cb.total_cost
            else:
                response = openai.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": self.templates["system"]},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.1,
                    max_tokens=1000
                )
                cost = None
            
            content = response.choices[0].message.content.strip()
            return {"content": content, "cost": cost}
            
        except Exception as e:
            raise Exception(f"OpenAI API error: {str(e)}")
    
    def _parse_response(self, response_content: str) -> Dict[str, Any]:
        """Parse structured response from LLM with improved error handling"""
        
        result = {
            "sql": "",
            "params": [],
            "explanation": "",
            "confidence": 0.85,  # Default confidence
            "complexity": QueryComplexity.SIMPLE
        }
        
        # Clean up response content
        response_content = response_content.strip()
        
        # First try to extract SQL from structured format
        lines = response_content.split('\n')
        current_section = None
        sql_lines = []
        
        for line in lines:
            line = line.strip()
            
            if line.startswith('SQL:'):
                sql_content = line[4:].strip()
                if sql_content:
                    result["sql"] = sql_content
                current_section = "sql"
            elif line.startswith('PARAMS:'):
                try:
                    params_str = line[7:].strip()
                    result["params"] = json.loads(params_str) if params_str else []
                except:
                    result["params"] = []
                current_section = "params"
            elif line.startswith('EXPLANATION:'):
                result["explanation"] = line[12:].strip()
                current_section = "explanation"
            elif line.startswith('CONFIDENCE:'):
                try:
                    result["confidence"] = float(line[11:].strip())
                except:
                    result["confidence"] = 0.85
            elif line.startswith('COMPLEXITY:'):
                try:
                    complexity_str = line[11:].strip().upper()
                    result["complexity"] = QueryComplexity(complexity_str.lower())
                except:
                    result["complexity"] = QueryComplexity.SIMPLE
            elif current_section and line:
                # Continue multi-line sections
                if current_section == "explanation":
                    result["explanation"] += " " + line
                elif current_section == "sql" and not any(line.startswith(x) for x in ["PARAMS:", "EXPLANATION:", "CONFIDENCE:"]):
                    result["sql"] += " " + line
        
        # If no structured SQL found, try to extract SQL from response
        if not result["sql"] or result["sql"] == "":
            # Look for SQL patterns in the response
            import re
            
            # Remove code block markers if present
            cleaned_content = response_content.replace('```sql', '').replace('```', '')
            
            # Find SELECT statements
            sql_pattern = r'(SELECT\s+.*?)(?=\n\n|\n[A-Z]+:|$)'
            sql_matches = re.findall(sql_pattern, cleaned_content, re.DOTALL | re.IGNORECASE)
            
            if sql_matches:
                # Take the first complete SELECT statement
                result["sql"] = sql_matches[0].strip()
                result["explanation"] = "Extracted SQL from LLM response"
            else:
                # Look for any SQL-like content
                lines_with_sql = [line for line in lines if 'SELECT' in line.upper() or 'FROM' in line.upper()]
                if lines_with_sql:
                    result["sql"] = ' '.join(lines_with_sql).strip()
                    result["explanation"] = "Reconstructed SQL from response fragments"
        
        # Clean up the SQL
        if result["sql"]:
            result["sql"] = result["sql"].strip().rstrip(';')
            if not result["explanation"]:
                result["explanation"] = "Generated SQL query for business intelligence analysis"
        
        return result
    
    def process_query(self, request: QueryRequest) -> QueryResult:
        """Main method to process natural language query into SQL"""
        
        # 1. Classify complexity
        complexity = self._classify_query_complexity(request.natural_language)
        
        # 2. Prepare context
        context = self._prepare_context(request)
        
        # 3. Select appropriate template
        template_name = "complex" if complexity != QueryComplexity.SIMPLE else "simple"
        template = self.templates[template_name]
        
        # 4. Format prompt - fix template key issues
        try:
            prompt = template.format(
                user_query=request.natural_language,
                **context
            )
        except KeyError as e:
            # Fallback formatting if template keys don't match
            prompt = template.format(
                user_query=request.natural_language,
                schema_context=context.get("schema_context", "")
            )
        
        # 5. Generate SQL
        try:
            response = self._generate_sql_with_openai(prompt)
            parsed = self._parse_response(response["content"])
            
            # 6. Safety validation
            is_safe, safety_message = validate_sql_safety(parsed["sql"])
            
            if not is_safe:
                raise Exception(f"Safety validation failed: {safety_message}")
            
            # 7. Store in conversation history (simple tracking)
            self.conversation_history.append({
                "query": request.natural_language,
                "sql": parsed["sql"],
                "confidence": parsed["confidence"]
            })
            # Keep only last 5 exchanges
            if len(self.conversation_history) > self.max_history:
                self.conversation_history = self.conversation_history[-self.max_history:]
            
            # 8. Return structured result
            return QueryResult(
                sql_query=parsed["sql"],
                parameters=parsed["params"],
                confidence_score=parsed["confidence"],
                complexity=parsed.get("complexity", complexity),
                explanation=parsed["explanation"],
                safety_check=is_safe,
                estimated_cost=response.get("cost")
            )
            
        except Exception as e:
            # Return safe fallback
            return QueryResult(
                sql_query="SELECT 'Error: Could not generate safe SQL' as error_message",
                parameters=[],
                confidence_score=0.0,
                complexity=complexity,
                explanation=f"Query processing failed: {str(e)}",
                safety_check=False
            )
    
    def get_query_suggestions(self, partial_query: str) -> List[str]:
        """Get query suggestions based on schema and partial input"""
        
        available_tables = schema_inspector.get_all_tables()
        suggestions = []
        
        partial_lower = partial_query.lower()
        
        # Basic query starters
        if len(partial_query) < 10:
            suggestions.extend([
                "Show me all users",
                "Find products similar to",
                "Count the number of",
                "Get users where email contains",
                "List products ordered by"
            ])
        
        # Table-specific suggestions
        for table in available_tables:
            if table.lower() in partial_lower:
                suggestions.extend([
                    f"Show all records from {table}",
                    f"Count records in {table}",
                    f"Find specific {table} where"
                ])
        
        return suggestions[:5]  # Limit to 5 suggestions

# Global semantic layer instance
semantic_layer = SemanticLayer()

def generate_sql_from_nl(nl_query: str, **kwargs) -> QueryResult:
    """Convenience function for backward compatibility"""
    request = QueryRequest(
        natural_language=nl_query,
        **kwargs
    )
    return semantic_layer.process_query(request)