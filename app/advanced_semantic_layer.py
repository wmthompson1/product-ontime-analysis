"""
Advanced Semantic Layer with RAG and RAGAS Evaluation
Based on Frank Kane's Advanced RAG techniques for improved SQL generation
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import asyncio

# Core LangChain imports
from langchain.prompts import PromptTemplate, ChatPromptTemplate, FewShotPromptTemplate
from langchain.schema import HumanMessage, SystemMessage, AIMessage
from langchain.memory import ConversationBufferWindowMemory
from langchain.chains import LLMChain
from langchain.output_parsers import PydanticOutputParser
from langchain.callbacks import get_openai_callback

# Advanced RAG components
try:
    from langchain.retrievers import BM25Retriever
    from langchain.vectorstores import FAISS
    from langchain.embeddings import OpenAIEmbeddings
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False

# RAGAS evaluation
try:
    from ragas import evaluate
    from ragas.metrics import (
        answer_relevancy,
        faithfulness,
        context_recall,
        context_precision,
        answer_correctness,
        answer_similarity
    )
    from datasets import Dataset
    RAGAS_AVAILABLE = True
except ImportError:
    RAGAS_AVAILABLE = False

import openai
from semantic_layer import QueryComplexity, QueryRequest, QueryResult, SemanticLayer
from schema_context import get_schema_context, validate_sql_safety

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class SQLExample:
    """Training example for few-shot prompting"""
    natural_language: str
    sql_query: str
    explanation: str
    complexity: str
    domain: str
    confidence: float = 1.0

@dataclass
class EvaluationMetrics:
    """RAGAS evaluation metrics for SQL generation"""
    answer_relevancy: float
    faithfulness: float
    context_recall: float
    context_precision: float
    answer_correctness: float
    answer_similarity: float
    sql_accuracy: float
    execution_success: bool

class AdvancedSemanticLayer(SemanticLayer):
    """Enhanced semantic layer with RAG and RAGAS evaluation"""
    
    def __init__(self):
        super().__init__()
        self.sql_examples = []
        self.retriever = None
        self.embeddings = None
        self.vectorstore = None
        self.evaluation_history = []
        
        # Initialize RAG components if available
        if RAG_AVAILABLE:
            self._initialize_rag_components()
        
        # Load training examples
        self._load_training_examples()
        
        # Enhanced prompt templates
        self._setup_advanced_templates()
    
    def _initialize_rag_components(self):
        """Initialize RAG retrieval components"""
        try:
            self.embeddings = OpenAIEmbeddings()
            logger.info("Initialized OpenAI embeddings for RAG")
        except Exception as e:
            logger.warning(f"Could not initialize embeddings: {e}")
            self.embeddings = None
    
    def _load_training_examples(self):
        """Load high-quality SQL examples for few-shot learning"""
        self.sql_examples = [
            SQLExample(
                natural_language="Show suppliers with delivery performance below 95%",
                sql_query="""
                SELECT 
                    s.supplier_name,
                    AVG(d.ontime_rate) as avg_delivery_performance,
                    COUNT(d.delivery_id) as total_deliveries,
                    s.contract_value
                FROM suppliers s
                JOIN daily_deliveries d ON s.supplier_id = d.supplier_id
                WHERE d.delivery_date >= CURRENT_DATE - INTERVAL '90 days'
                GROUP BY s.supplier_id, s.supplier_name, s.contract_value
                HAVING AVG(d.ontime_rate) < 0.95
                ORDER BY avg_delivery_performance ASC, s.contract_value DESC
                """,
                explanation="Identifies underperforming suppliers with recent delivery data, grouped by supplier with contract value for prioritization",
                complexity="medium",
                domain="supply_chain"
            ),
            SQLExample(
                natural_language="Find products with defect rates trending upward",
                sql_query="""
                WITH monthly_defects AS (
                    SELECT 
                        product_line,
                        DATE_TRUNC('month', production_date) as month,
                        AVG(defect_rate) as monthly_defect_rate
                    FROM production_quality
                    WHERE production_date >= CURRENT_DATE - INTERVAL '6 months'
                    GROUP BY product_line, DATE_TRUNC('month', production_date)
                ),
                trend_analysis AS (
                    SELECT 
                        product_line,
                        month,
                        monthly_defect_rate,
                        LAG(monthly_defect_rate) OVER (PARTITION BY product_line ORDER BY month) as prev_month_rate
                    FROM monthly_defects
                )
                SELECT 
                    product_line,
                    COUNT(*) as months_analyzed,
                    AVG(monthly_defect_rate) as avg_defect_rate,
                    (monthly_defect_rate - prev_month_rate) as trend_change
                FROM trend_analysis
                WHERE prev_month_rate IS NOT NULL
                    AND monthly_defect_rate > prev_month_rate
                GROUP BY product_line, monthly_defect_rate, prev_month_rate
                HAVING COUNT(*) >= 2
                ORDER BY trend_change DESC
                """,
                explanation="Uses window functions to identify products with consistently increasing defect rates over multiple months",
                complexity="complex",
                domain="quality_control"
            ),
            SQLExample(
                natural_language="Calculate overall equipment effectiveness for production lines",
                sql_query="""
                SELECT 
                    pl.line_name,
                    pl.theoretical_capacity,
                    AVG(pm.availability_rate) as availability,
                    AVG(pm.performance_rate) as performance,
                    AVG(pm.quality_rate) as quality,
                    (AVG(pm.availability_rate) * AVG(pm.performance_rate) * AVG(pm.quality_rate)) as oee_score,
                    CASE 
                        WHEN (AVG(pm.availability_rate) * AVG(pm.performance_rate) * AVG(pm.quality_rate)) >= 0.85 
                        THEN 'World Class'
                        WHEN (AVG(pm.availability_rate) * AVG(pm.performance_rate) * AVG(pm.quality_rate)) >= 0.60 
                        THEN 'Acceptable'
                        ELSE 'Needs Improvement'
                    END as oee_classification
                FROM production_lines pl
                JOIN production_metrics pm ON pl.line_id = pm.line_id
                WHERE pm.measurement_date >= CURRENT_DATE - INTERVAL '30 days'
                GROUP BY pl.line_id, pl.line_name, pl.theoretical_capacity
                ORDER BY oee_score DESC
                """,
                explanation="Calculates OEE (Overall Equipment Effectiveness) using the standard formula: Availability × Performance × Quality",
                complexity="medium",
                domain="production_efficiency"
            ),
            SQLExample(
                natural_language="Show NCM trends with root cause analysis",
                sql_query="""
                SELECT 
                    nc.product_line,
                    nc.failure_mode,
                    COUNT(*) as ncm_incidents,
                    AVG(nc.cost_impact) as avg_cost_impact,
                    STRING_AGG(DISTINCT nc.root_cause, ', ') as common_root_causes,
                    ROUND(
                        COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (PARTITION BY nc.product_line),
                        2
                    ) as percentage_of_line_ncm
                FROM non_conformant_materials nc
                WHERE nc.incident_date >= CURRENT_DATE - INTERVAL '90 days'
                    AND nc.status = 'CLOSED'
                GROUP BY nc.product_line, nc.failure_mode
                HAVING COUNT(*) >= 3
                ORDER BY nc.product_line, ncm_incidents DESC
                """,
                explanation="Analyzes Non-Conformant Material incidents with root cause categorization and cost impact assessment",
                complexity="medium",
                domain="quality_control"
            )
        ]
        
        # Create retriever from examples if RAG is available
        if RAG_AVAILABLE and self.embeddings:
            try:
                self._create_example_retriever()
            except Exception as e:
                logger.warning(f"Vector retrieval disabled, using fallback: {str(e)}")
                self.retriever = None
                self._setup_fallback_retriever()
    
    def _create_example_retriever(self):
        """Create vector store retriever from SQL examples"""
        try:
            # Prepare documents for vectorization
            documents = []
            for example in self.sql_examples:
                doc_text = f"Query: {example.natural_language}\nSQL: {example.sql_query}\nExplanation: {example.explanation}\nDomain: {example.domain}"
                documents.append(doc_text)
            
            # Create vector store
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=100
            )
            splits = text_splitter.create_documents(documents)
            
            if 'FAISS' in globals():
                self.vectorstore = FAISS.from_documents(splits, self.embeddings)
                self.retriever = self.vectorstore.as_retriever(
                    search_type="similarity",
                    search_kwargs={"k": 3}
                )
            else:
                raise ImportError("FAISS not available")
            logger.info("Created vector store retriever with SQL examples")
            
        except Exception as e:
            logger.warning(f"Could not create retriever: {e}")
            self.retriever = None
            self._setup_fallback_retriever()
    
    def _setup_advanced_templates(self):
        """Setup enhanced prompt templates with few-shot examples"""
        
        # Few-shot example template
        example_template = """
        Human Query: {natural_language}
        SQL Query: {sql_query}
        Explanation: {explanation}
        Domain: {domain}
        """
        
        example_prompt = PromptTemplate(
            input_variables=["natural_language", "sql_query", "explanation", "domain"],
            template=example_template
        )
        
        # Main system prompt with RAG context
        system_prompt = """You are an expert SQL assistant specializing in manufacturing and supply chain analytics.

CRITICAL RULES:
- Generate ONLY SELECT or WITH statements
- Use proper PostgreSQL syntax with explicit JOIN conditions
- Include appropriate aggregations and window functions for analytics
- Add business logic for manufacturing KPIs (OEE, NCM, OTD, etc.)
- Use parameter placeholders (%s) for dynamic values
- Include meaningful column aliases and sorting

MANUFACTURING DOMAIN KNOWLEDGE:
- NCM = Non-Conformant Material (quality defects)
- OTD = On-Time Delivery (supply chain performance)  
- OEE = Overall Equipment Effectiveness (Availability × Performance × Quality)
- DPMO = Defects Per Million Opportunities
- MTBF = Mean Time Between Failures

RESPONSE FORMAT:
SQL: [PostgreSQL query with proper business logic]
EXPLANATION: [Business context and query logic]
CONFIDENCE: [0.0-1.0 score]
COMPLEXITY: [simple|medium|complex]

{context}

Generate a SQL query for manufacturing analytics:"""

        # Create few-shot prompt template
        self.few_shot_template = FewShotPromptTemplate(
            examples=[asdict(ex) for ex in self.sql_examples[:3]],  # Use top 3 examples
            example_prompt=example_prompt,
            prefix=system_prompt,
            suffix="Human Query: {user_query}\n\nSQL:",
            input_variables=["user_query", "context"]
        )
        
        # Enhanced system template for RAG
        self.templates["advanced_system"] = system_prompt
        self.templates["few_shot"] = self.few_shot_template
    
    def _setup_fallback_retriever(self):
        """Setup simple keyword-based retriever when FAISS is not available"""
        logger.info("Setting up fallback retriever using keyword matching")
        
        # Create simple keyword-based retriever
        self.fallback_examples = {}
        for example in self.sql_examples:
            # Index by domain and key terms
            domain = example.domain
            if domain not in self.fallback_examples:
                self.fallback_examples[domain] = []
            self.fallback_examples[domain].append(example)
        
        logger.info(f"Fallback retriever configured with {len(self.sql_examples)} examples across {len(self.fallback_examples)} domains")
    
    def _retrieve_similar_examples(self, query: str, domain: str = None) -> List[Dict]:
        """Retrieve similar examples using fallback keyword matching"""
        if self.retriever:
            # Use vector retriever if available
            try:
                docs = self.retriever.get_relevant_documents(query)
                return [{"content": doc.page_content} for doc in docs[:3]]
            except Exception as e:
                logger.warning(f"Vector retrieval failed, using fallback: {e}")
        
        # Use fallback keyword matching
        if not hasattr(self, 'fallback_examples'):
            return []
        
        # Simple keyword matching
        query_lower = query.lower()
        keywords = ["supplier", "delivery", "mtbf", "oee", "ncm", "defect", "quality", "equipment", "reliability"]
        
        # Try domain-specific examples first
        examples = []
        if domain and domain in self.fallback_examples:
            examples.extend(self.fallback_examples[domain][:2])
        
        # Add examples from other domains if needed
        for d, exs in self.fallback_examples.items():
            if d != domain and len(examples) < 3:
                examples.extend(exs[:1])
        
        return [{"content": f"Query: {ex.natural_language}\nSQL: {ex.sql_query}\nExplanation: {ex.explanation}"} 
                for ex in examples[:3]]
    
    def _retrieve_similar_examples(self, query: str, k: int = 3) -> List[str]:
        """Retrieve similar SQL examples using RAG"""
        if not self.retriever:
            return []
        
        try:
            docs = self.retriever.get_relevant_documents(query)
            return [doc.page_content for doc in docs[:k]]
        except Exception as e:
            logger.warning(f"Error retrieving examples: {e}")
            return []
    
    def generate_advanced_sql(self, request: QueryRequest) -> QueryResult:
        """Generate SQL using advanced RAG techniques"""
        
        # 1. Retrieve similar examples
        similar_examples = self._retrieve_similar_examples(request.natural_language)
        
        # 2. Build enhanced context
        schema_context = get_schema_context(request.tables_hint)
        
        rag_context = ""
        if similar_examples:
            rag_context = "\n\nSIMILAR EXAMPLES:\n" + "\n".join(similar_examples)
        
        full_context = schema_context + rag_context
        
        # 3. Use few-shot prompting with RAG context
        try:
            if hasattr(self.few_shot_template, 'format'):
                prompt = self.few_shot_template.format(
                    user_query=request.natural_language,
                    context=full_context
                )
            else:
                # Fallback to standard template
                prompt = self.templates["complex"].format(
                    user_query=request.natural_language,
                    schema_context=full_context
                )
            
            # 4. Generate SQL with OpenAI
            response = self._generate_sql_with_openai(prompt)
            parsed = self._parse_response(response["content"])
            
            # 5. Enhanced safety validation
            is_safe, safety_message = validate_sql_safety(parsed["sql"])
            
            if not is_safe:
                logger.warning(f"Safety validation failed: {safety_message}")
                return self._create_fallback_result(request, safety_message)
            
            # 6. Create enhanced result
            result = QueryResult(
                sql_query=parsed["sql"],
                parameters=parsed["params"],
                confidence_score=parsed["confidence"],
                complexity=parsed.get("complexity", QueryComplexity.MEDIUM),
                explanation=parsed["explanation"],
                safety_check=is_safe,
                estimated_cost=response.get("cost")
            )
            
            # 7. Log for evaluation
            self._log_generation(request, result, rag_context)
            
            return result
            
        except Exception as e:
            logger.error(f"Advanced SQL generation failed: {e}")
            return self._create_fallback_result(request, str(e))
    
    def _create_fallback_result(self, request: QueryRequest, error_msg: str) -> QueryResult:
        """Create safe fallback result"""
        return QueryResult(
            sql_query="SELECT 'Query generation failed' as status, %s as error_message",
            parameters=[error_msg],
            confidence_score=0.0,
            complexity=QueryComplexity.SIMPLE,
            explanation=f"Could not generate SQL: {error_msg}",
            safety_check=False
        )
    
    def _log_generation(self, request: QueryRequest, result: QueryResult, context: str):
        """Log generation for later evaluation"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "natural_language": request.natural_language,
            "generated_sql": result.sql_query,
            "confidence": result.confidence_score,
            "complexity": result.complexity.value if hasattr(result.complexity, 'value') else str(result.complexity),
            "explanation": result.explanation,
            "context_used": len(context),
            "safety_check": result.safety_check
        }
        self.evaluation_history.append(log_entry)
    
    async def evaluate_with_ragas(self, test_queries: List[Dict]) -> Dict[str, float]:
        """Evaluate SQL generation quality using RAGAS metrics"""
        if not RAGAS_AVAILABLE:
            logger.warning("RAGAS not available for evaluation")
            return {}
        
        try:
            # Prepare evaluation dataset
            questions = []
            generated_answers = []
            ground_truths = []
            contexts = []
            
            for test_case in test_queries:
                # Generate SQL for test query
                request = QueryRequest(
                    natural_language=test_case["query"],
                    tables_hint=test_case.get("tables", [])
                )
                result = self.generate_advanced_sql(request)
                
                questions.append(test_case["query"])
                generated_answers.append(result.sql_query)
                ground_truths.append(test_case.get("expected_sql", result.sql_query))
                contexts.append(test_case.get("context", ""))
            
            # Create RAGAS dataset
            dataset = Dataset.from_dict({
                "question": questions,
                "answer": generated_answers,
                "contexts": [[ctx] for ctx in contexts],
                "ground_truth": ground_truths
            })
            
            # Run evaluation
            metrics = [
                answer_relevancy,
                faithfulness,
                context_recall,
                context_precision,
                answer_correctness
            ]
            
            evaluation_result = evaluate(dataset, metrics=metrics)
            
            logger.info("RAGAS evaluation completed")
            return evaluation_result
            
        except Exception as e:
            logger.error(f"RAGAS evaluation failed: {e}")
            return {}
    
    def get_performance_insights(self) -> Dict[str, Any]:
        """Analyze performance from evaluation history"""
        if not self.evaluation_history:
            return {"message": "No evaluation data available"}
        
        # Calculate performance metrics
        total_queries = len(self.evaluation_history)
        successful_queries = sum(1 for entry in self.evaluation_history if entry["safety_check"])
        avg_confidence = sum(entry["confidence"] for entry in self.evaluation_history) / total_queries
        
        complexity_distribution = {}
        for entry in self.evaluation_history:
            complexity = entry["complexity"]
            complexity_distribution[complexity] = complexity_distribution.get(complexity, 0) + 1
        
        return {
            "total_queries": total_queries,
            "success_rate": successful_queries / total_queries,
            "average_confidence": avg_confidence,
            "complexity_distribution": complexity_distribution,
            "rag_enabled": RAG_AVAILABLE and self.retriever is not None,
            "ragas_available": RAGAS_AVAILABLE,
            "recent_queries": self.evaluation_history[-5:] if len(self.evaluation_history) >= 5 else self.evaluation_history
        }

# Global instance
advanced_semantic_layer = AdvancedSemanticLayer()

def create_test_evaluation_set() -> List[Dict]:
    """Create test set for RAGAS evaluation"""
    return [
        {
            "query": "Show suppliers with poor delivery performance affecting our production schedule",
            "expected_sql": "SELECT supplier_name, AVG(ontime_rate) FROM suppliers s JOIN daily_deliveries d ON s.supplier_id = d.supplier_id WHERE d.delivery_date >= CURRENT_DATE - INTERVAL '30 days' GROUP BY supplier_name HAVING AVG(ontime_rate) < 0.95",
            "context": "Supply chain analysis for production planning",
            "tables": ["suppliers", "daily_deliveries"]
        },
        {
            "query": "Find product lines with NCM rates above industry benchmarks", 
            "expected_sql": "SELECT product_line, AVG(defect_rate) FROM production_quality WHERE date >= CURRENT_DATE - INTERVAL '90 days' GROUP BY product_line HAVING AVG(defect_rate) > 0.025",
            "context": "Quality control analysis for compliance reporting",
            "tables": ["production_quality"]
        },
        {
            "query": "Calculate OEE trends for critical manufacturing equipment",
            "expected_sql": "SELECT equipment_id, DATE_TRUNC('week', date) as week, AVG(availability * performance * quality) as oee FROM equipment_metrics WHERE date >= CURRENT_DATE - INTERVAL '12 weeks' AND equipment_type = 'critical' GROUP BY equipment_id, week ORDER BY week",
            "context": "Equipment effectiveness monitoring for maintenance planning", 
            "tables": ["equipment_metrics"]
        }
    ]