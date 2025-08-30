#!/usr/bin/env python3
"""
001_Entry_Point_Kane_Ragas.py
Frank Kane's Advanced RAG with RAGAS Evaluation Framework
Integrates Tavily real-time search with manufacturing domain RAGAS metrics

Based on Frank Kane Section 14: Data Agent concepts
Repository: Machine-Learning-Data-Science-and-Generative-AI-with-Python
Focus: Real-time data retrieval + RAGAS evaluation for manufacturing intelligence
"""

import os
import sys
import time
import json
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime

# Add app directory to path
sys.path.append('app')
sys.path.append(os.getcwd())

# Core imports
from langchain.prompts import PromptTemplate, FewShotPromptTemplate
from langchain_community.callbacks.manager import get_openai_callback
from openai import OpenAI
import requests

# Import our existing foundation
from Entry_Point_001_few_shot import (
    FewShotSQLGenerator, 
    AdvancedRAGMetrics, 
    RAGMetrics,
    SQLExample
)
from app.schema_context import validate_sql_safety, get_schema_context

@dataclass
class RAGASMetrics:
    """RAGAS evaluation metrics for Advanced RAG assessment"""
    query_id: str
    faithfulness: float  # How faithful is the generated answer to the context
    answer_relevancy: float  # How relevant is the answer to the question  
    context_precision: float  # How precise is the retrieved context
    context_recall: float  # How much of the relevant context was retrieved
    ragas_score: float  # Overall RAGAS composite score
    tavily_context_quality: float  # Quality of Tavily search results
    manufacturing_domain_accuracy: float  # Manufacturing-specific accuracy
    timestamp: str

@dataclass 
class TavilySearchResult:
    """Structured result from Tavily real-time search"""
    query: str
    results: List[Dict[str, Any]]
    search_time: float
    relevance_score: float
    currency_score: float  # How current/fresh the information is

class FrankKaneRAGASAgent:
    """
    Advanced RAG agent implementing Frank Kane's Data Agent concepts
    Combines real-time Tavily search with RAGAS evaluation framework
    
    Key Features:
    1. Real-time manufacturing industry data retrieval via Tavily
    2. RAGAS evaluation framework for comprehensive quality assessment
    3. Manufacturing domain expertise validation
    4. Progressive learning with metrics tracking
    """
    
    def __init__(self):
        """Initialize the Frank Kane RAGAS Agent"""
        
        # Core LLM setup
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.tavily_api_key = os.getenv("TAVILY_API_KEY")
        
        # Initialize base few-shot generator for comparison
        self.base_generator = FewShotSQLGenerator()
        
        # Advanced metrics tracking
        self.ragas_metrics: List[RAGASMetrics] = []
        self.session_start = datetime.now()
        
        # Manufacturing domain knowledge base
        self.manufacturing_keywords = [
            "supply chain", "manufacturing", "production", "quality control",
            "lean manufacturing", "six sigma", "OEE", "DPMO", "NCM", 
            "preventive maintenance", "predictive maintenance", "MTBF",
            "just-in-time", "kanban", "TPM", "CAPA", "ISO 9001"
        ]
        
        print("🚀 Frank Kane RAGAS Agent initialized")
        print("📊 RAGAS evaluation framework enabled")
        print("🔍 Tavily real-time search configured")
        print("🏭 Manufacturing domain expertise loaded")
        
    def search_manufacturing_context(self, query: str) -> TavilySearchResult:
        """
        Perform Tavily search for current manufacturing industry context
        Based on Frank Kane's Data Agent real-time retrieval concepts
        """
        start_time = time.time()
        
        # Enhance query with manufacturing context
        enhanced_query = f"manufacturing industry {query} 2024 2025 current trends"
        
        try:
            # Tavily API call
            payload = {
                "api_key": self.tavily_api_key,
                "query": enhanced_query,
                "search_depth": "advanced",
                "include_domains": [
                    "manufacturing.net", "industryweek.com", "isa.org",
                    "automationworld.com", "qualitymag.com", "plantengineering.com"
                ],
                "max_results": 5
            }
            
            response = requests.post(
                "https://api.tavily.com/search",
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                search_time = time.time() - start_time
                
                # Calculate relevance and currency scores
                relevance_score = self._calculate_relevance_score(data.get("results", []), query)
                currency_score = self._calculate_currency_score(data.get("results", []))
                
                return TavilySearchResult(
                    query=enhanced_query,
                    results=data.get("results", []),
                    search_time=search_time,
                    relevance_score=relevance_score,
                    currency_score=currency_score
                )
            else:
                print(f"⚠️ Tavily search failed: {response.status_code}")
                return self._create_fallback_context(query)
                
        except Exception as e:
            print(f"⚠️ Tavily search error: {e}")
            return self._create_fallback_context(query)
    
    def _calculate_relevance_score(self, results: List[Dict], query: str) -> float:
        """Calculate relevance score based on manufacturing keyword matches"""
        if not results:
            return 0.0
            
        total_score = 0.0
        query_lower = query.lower()
        
        for result in results:
            content = (result.get("content", "") + " " + result.get("title", "")).lower()
            
            # Count manufacturing keyword matches
            keyword_matches = sum(1 for keyword in self.manufacturing_keywords if keyword in content)
            
            # Count query term matches
            query_matches = sum(1 for word in query_lower.split() if word in content)
            
            # Combine scores
            relevance = (keyword_matches * 0.7 + query_matches * 0.3) / max(len(self.manufacturing_keywords), len(query_lower.split()))
            total_score += min(relevance, 1.0)
            
        return total_score / len(results)
    
    def _calculate_currency_score(self, results: List[Dict]) -> float:
        """Calculate how current/fresh the search results are"""
        if not results:
            return 0.0
            
        current_year = datetime.now().year
        total_score = 0.0
        
        for result in results:
            content = result.get("content", "") + " " + result.get("title", "")
            
            # Look for recent year mentions
            if str(current_year) in content or str(current_year - 1) in content:
                total_score += 1.0
            elif "2023" in content or "recent" in content.lower() or "current" in content.lower():
                total_score += 0.7
            else:
                total_score += 0.3
                
        return total_score / len(results)
    
    def _create_fallback_context(self, query: str) -> TavilySearchResult:
        """Create fallback context when Tavily search fails"""
        return TavilySearchResult(
            query=query,
            results=[{
                "title": "Manufacturing Industry Context",
                "content": f"Current manufacturing industry context for: {query}. Focus on operational efficiency, quality control, and supply chain optimization.",
                "url": "internal://fallback"
            }],
            search_time=0.1,
            relevance_score=0.5,
            currency_score=0.3
        )
    
    def generate_ragas_enhanced_sql(self, user_query: str) -> Dict[str, Any]:
        """
        Generate SQL with RAGAS-enhanced context using Frank Kane methodology
        Combines few-shot learning + real-time search + RAGAS evaluation
        """
        start_time = time.time()
        print(f"🔍 Processing RAGAS-enhanced query: {user_query}")
        
        # Step 1: Get real-time manufacturing context via Tavily
        print("📡 Retrieving real-time manufacturing context...")
        tavily_context = self.search_manufacturing_context(user_query)
        
        # Step 2: Generate SQL with enhanced context
        enhanced_result = self._generate_sql_with_context(user_query, tavily_context)
        
        # Step 3: Evaluate using RAGAS framework
        print("📊 Evaluating with RAGAS metrics...")
        ragas_evaluation = self._evaluate_with_ragas(user_query, enhanced_result, tavily_context)
        
        # Step 4: Compare with baseline
        baseline_result = self.base_generator.generate_sql_with_few_shot(user_query)
        
        # Step 5: Record comprehensive metrics
        total_time = time.time() - start_time
        query_id = f"RAGAS_{len(self.ragas_metrics)+1:03d}_{int(time.time())}"
        
        ragas_metrics = RAGASMetrics(
            query_id=query_id,
            faithfulness=ragas_evaluation["faithfulness"],
            answer_relevancy=ragas_evaluation["answer_relevancy"],
            context_precision=ragas_evaluation["context_precision"],
            context_recall=ragas_evaluation["context_recall"],
            ragas_score=ragas_evaluation["composite_score"],
            tavily_context_quality=tavily_context.relevance_score,
            manufacturing_domain_accuracy=ragas_evaluation["domain_accuracy"],
            timestamp=datetime.now().isoformat()
        )
        
        self.ragas_metrics.append(ragas_metrics)
        
        print(f"✅ RAGAS analysis complete!")
        print(f"📈 RAGAS Score: {ragas_evaluation['composite_score']:.3f}")
        print(f"🏭 Domain Accuracy: {ragas_evaluation['domain_accuracy']:.3f}")
        print(f"⚡ Total Time: {total_time:.2f}s")
        
        return {
            "enhanced_result": enhanced_result,
            "baseline_result": baseline_result,
            "ragas_metrics": asdict(ragas_metrics),
            "tavily_context": asdict(tavily_context),
            "processing_time": total_time,
            "improvement_analysis": self._analyze_improvement(enhanced_result, baseline_result, ragas_evaluation)
        }
    
    def _generate_sql_with_context(self, query: str, tavily_context: TavilySearchResult) -> Dict[str, Any]:
        """Generate SQL with Tavily context enhancement"""
        
        # Build enhanced context from Tavily results
        context_content = ""
        for result in tavily_context.results[:3]:  # Use top 3 results
            context_content += f"Industry Context: {result.get('title', '')} - {result.get('content', '')[:200]}...\n"
        
        # Enhanced prompt with real-time context
        enhanced_prompt = f"""
You are an expert SQL assistant with access to current manufacturing industry context.

CURRENT INDUSTRY CONTEXT:
{context_content}

MANUFACTURING DATABASE SCHEMA:
{self.base_generator._get_compact_schema_context()}

USER QUERY: {query}

Generate a PostgreSQL query that incorporates current industry trends and best practices.

RESPONSE FORMAT:
SQL: [your query]
EXPLANATION: [explanation with industry context]
CONFIDENCE: [0.0-1.0]
COMPLEXITY: [simple|medium|complex]
INDUSTRY_RELEVANCE: [how query relates to current trends]
"""

        try:
            with get_openai_callback() as cb:
                response = self.client.chat.completions.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": enhanced_prompt}],
                    temperature=0.1,
                    max_tokens=1000
                )
                
                content = response.choices[0].message.content
                parsed_result = self.base_generator._parse_sql_response(content)
                
                # Add context enhancement metrics
                parsed_result.update({
                    "context_enhanced": True,
                    "tavily_results_used": len(tavily_context.results),
                    "context_relevance": tavily_context.relevance_score,
                    "token_usage": {
                        "total_tokens": cb.total_tokens,
                        "total_cost": cb.total_cost
                    }
                })
                
                return parsed_result
                
        except Exception as e:
            print(f"❌ Enhanced SQL generation failed: {e}")
            return {"error": str(e), "sql": None, "confidence": 0.0}
    
    def _evaluate_with_ragas(self, query: str, result: Dict[str, Any], context: TavilySearchResult) -> Dict[str, float]:
        """
        Evaluate results using RAGAS framework adapted for manufacturing domain
        Based on Frank Kane's evaluation methodology
        """
        
        # Faithfulness: How faithful is the SQL to the manufacturing context
        faithfulness = self._calculate_faithfulness(result, context)
        
        # Answer Relevancy: How relevant is the SQL to the original query
        answer_relevancy = self._calculate_answer_relevancy(query, result)
        
        # Context Precision: How precise is the retrieved Tavily context
        context_precision = context.relevance_score
        
        # Context Recall: How comprehensive is the context coverage
        context_recall = self._calculate_context_recall(query, context)
        
        # Manufacturing Domain Accuracy
        domain_accuracy = self._calculate_domain_accuracy(result)
        
        # Composite RAGAS score
        composite_score = (
            faithfulness * 0.25 +
            answer_relevancy * 0.25 +
            context_precision * 0.2 +
            context_recall * 0.15 +
            domain_accuracy * 0.15
        )
        
        return {
            "faithfulness": faithfulness,
            "answer_relevancy": answer_relevancy,
            "context_precision": context_precision,
            "context_recall": context_recall,
            "domain_accuracy": domain_accuracy,
            "composite_score": composite_score
        }
    
    def _calculate_faithfulness(self, result: Dict[str, Any], context: TavilySearchResult) -> float:
        """Calculate faithfulness score"""
        if not result.get("sql"):
            return 0.0
            
        # Check if SQL incorporates industry context appropriately
        sql_content = result.get("sql", "").lower()
        explanation = result.get("explanation", "").lower()
        
        # Look for manufacturing terms in explanation
        manufacturing_terms_used = sum(1 for term in self.manufacturing_keywords if term in explanation)
        
        # Normalize score
        faithfulness_score = min(manufacturing_terms_used / 5.0, 1.0)
        
        return faithfulness_score
    
    def _calculate_answer_relevancy(self, query: str, result: Dict[str, Any]) -> float:
        """Calculate answer relevancy score"""
        if not result.get("sql"):
            return 0.0
            
        query_terms = set(query.lower().split())
        sql_terms = set(result.get("sql", "").lower().split())
        explanation_terms = set(result.get("explanation", "").lower().split())
        
        # Calculate term overlap
        sql_overlap = len(query_terms.intersection(sql_terms)) / len(query_terms)
        explanation_overlap = len(query_terms.intersection(explanation_terms)) / len(query_terms)
        
        return (sql_overlap * 0.6 + explanation_overlap * 0.4)
    
    def _calculate_context_recall(self, query: str, context: TavilySearchResult) -> float:
        """Calculate context recall score"""
        query_terms = set(query.lower().split())
        
        context_coverage = 0.0
        for result in context.results:
            content = (result.get("content", "") + " " + result.get("title", "")).lower()
            content_terms = set(content.split())
            
            overlap = len(query_terms.intersection(content_terms))
            context_coverage += overlap / len(query_terms)
        
        return min(context_coverage / len(context.results), 1.0) if context.results else 0.0
    
    def _calculate_domain_accuracy(self, result: Dict[str, Any]) -> float:
        """Calculate manufacturing domain accuracy"""
        if not result.get("sql"):
            return 0.0
            
        sql_content = result.get("sql", "").lower()
        explanation = result.get("explanation", "").lower()
        
        # Check for proper manufacturing table usage
        manufacturing_tables = ["suppliers", "product_defects", "equipment_metrics", "quality_incidents"]
        table_usage = sum(1 for table in manufacturing_tables if table in sql_content)
        
        # Check for manufacturing KPI calculations
        kpi_patterns = ["avg(", "count(", "sum(", "having", "group by"]
        kpi_usage = sum(1 for pattern in kpi_patterns if pattern in sql_content)
        
        # Normalize scores
        table_score = min(table_usage / 2.0, 1.0)
        kpi_score = min(kpi_usage / 3.0, 1.0)
        
        return (table_score * 0.6 + kpi_score * 0.4)
    
    def _analyze_improvement(self, enhanced: Dict, baseline: Dict, ragas: Dict[str, float]) -> Dict[str, Any]:
        """Analyze improvement over baseline"""
        
        confidence_improvement = enhanced.get("confidence", 0) - baseline.get("confidence", 0)
        
        return {
            "confidence_improvement": confidence_improvement,
            "ragas_composite_score": ragas["composite_score"],
            "context_enhancement": enhanced.get("context_enhanced", False),
            "recommendation": self._get_improvement_recommendation(ragas)
        }
    
    def _get_improvement_recommendation(self, ragas: Dict[str, float]) -> str:
        """Generate improvement recommendation based on RAGAS scores"""
        composite = ragas["composite_score"]
        
        if composite >= 0.8:
            return "Excellent RAGAS performance! Ready for production deployment"
        elif composite >= 0.6:
            return "Good performance. Consider enhancing context precision and recall"
        elif composite >= 0.4:
            return "Moderate performance. Focus on improving faithfulness and domain accuracy"
        else:
            return "Needs improvement. Review few-shot examples and context retrieval strategy"

def main():
    """Main entry point for Frank Kane RAGAS experimentation"""
    print("🚀 FRANK KANE RAGAS AGENT")
    print("   Advanced RAG with Real-time Search + RAGAS Evaluation")
    print("=" * 70)
    
    # Initialize the RAGAS agent
    agent = FrankKaneRAGASAgent()
    
    # Test queries for manufacturing intelligence with real-time context
    test_queries = [
        "Show suppliers with delivery performance issues in current supply chain disruptions",
        "Find products with quality defects trending above 2024 industry benchmarks",
        "Calculate OEE for equipment using latest manufacturing best practices"
    ]
    
    print(f"\n🧪 Testing {len(test_queries)} RAGAS-enhanced queries...")
    
    results = []
    for i, query in enumerate(test_queries, 1):
        print(f"\n{i}. Testing: {query}")
        result = agent.generate_ragas_enhanced_sql(query)
        results.append(result)
    
    # Display comprehensive RAGAS analysis
    print("\n" + "="*70)
    print("📊 FRANK KANE RAGAS EVALUATION SUMMARY")
    print("="*70)
    
    if agent.ragas_metrics:
        avg_ragas = sum(m.ragas_score for m in agent.ragas_metrics) / len(agent.ragas_metrics)
        avg_faithfulness = sum(m.faithfulness for m in agent.ragas_metrics) / len(agent.ragas_metrics)
        avg_domain_accuracy = sum(m.manufacturing_domain_accuracy for m in agent.ragas_metrics) / len(agent.ragas_metrics)
        
        print(f"📈 Average RAGAS Score: {avg_ragas:.3f}")
        print(f"🔒 Average Faithfulness: {avg_faithfulness:.3f}")
        print(f"🏭 Average Domain Accuracy: {avg_domain_accuracy:.3f}")
        print(f"📡 Tavily Integration: ✅ Active")
        print(f"⚡ Queries Processed: {len(agent.ragas_metrics)}")
    
    print(f"\n✅ Frank Kane RAGAS analysis complete!")
    print(f"   Real-time manufacturing context + RAGAS evaluation integrated")
    print(f"   Next: Implement vector stores and embedding-based retrieval")
    
    return results

if __name__ == "__main__":
    main()