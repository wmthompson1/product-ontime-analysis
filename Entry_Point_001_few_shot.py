#!/usr/bin/env python3
"""
Entry Point 001: Few-Shot Learning Implementation
Educational entry point for studying Frank Kane's Advanced RAG techniques
Incrementally implement LangChain metrics and few-shot prompting
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

# Core LangChain imports for few-shot learning
from langchain.prompts import PromptTemplate, FewShotPromptTemplate
from langchain.schema import HumanMessage, SystemMessage
try:
    from langchain_community.callbacks.manager import get_openai_callback
except ImportError:
    from langchain.callbacks import get_openai_callback
import openai

# Import our semantic layer components
from semantic_layer import QueryRequest, QueryResult, QueryComplexity
from schema_context import get_schema_context, validate_sql_safety

@dataclass
class SQLExample:
    """Training example for few-shot prompting - Frank Kane style"""
    natural_language: str
    sql_query: str
    explanation: str
    complexity: str
    domain: str
    confidence: float = 1.0

@dataclass 
class RAGMetrics:
    """LangChain metrics for Advanced RAG evaluation"""
    query_id: str
    query_text: str
    response_time: float
    token_usage: Dict[str, int]
    confidence_score: float
    sql_complexity: str
    domain_relevance: float
    safety_score: float
    cost: float
    timestamp: str
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class AdvancedRAGMetrics:
    """
    Incremental LangChain metrics for Frank Kane's Advanced RAG study
    
    Key Metrics Areas:
    1. Performance Tracking (latency, tokens, cost)
    2. Quality Assessment (confidence, accuracy, domain relevance)  
    3. Safety Validation (SQL injection prevention, query safety)
    4. Few-Shot Learning Analysis (example effectiveness, improvement trends)
    """
    
    def __init__(self):
        self.metrics_log: List[RAGMetrics] = []
        self.session_start = datetime.now()
        self.total_queries = 0
        self.cumulative_cost = 0.0
        
    def record_query_metrics(
        self, 
        query: str, 
        result: Dict[str, Any], 
        response_time: float,
        token_usage: Dict[str, int] = None
    ) -> RAGMetrics:
        """Record comprehensive metrics for each query"""
        
        self.total_queries += 1
        query_id = f"Q{self.total_queries:03d}_{int(time.time())}"
        
        # Calculate domain relevance (manufacturing terms)
        domain_score = self._calculate_domain_relevance(query)
        
        # Safety assessment
        safety_check = result.get('safety_check', True)
        if isinstance(safety_check, tuple):
            safety_score = 1.0 if safety_check[0] else 0.0
        else:
            safety_score = 1.0 if safety_check else 0.0
        
        # Cost calculation
        cost = token_usage.get('total_cost', 0.0) if token_usage else 0.0
        self.cumulative_cost += cost
        
        metrics = RAGMetrics(
            query_id=query_id,
            query_text=query,
            response_time=response_time,
            token_usage=token_usage or {},
            confidence_score=result.get('confidence', 0.0),
            sql_complexity=result.get('complexity', 'unknown'),
            domain_relevance=domain_score,
            safety_score=safety_score,
            cost=cost,
            timestamp=datetime.now().isoformat()
        )
        
        self.metrics_log.append(metrics)
        return metrics
    
    def _calculate_domain_relevance(self, query: str) -> float:
        """Calculate how relevant query is to manufacturing domain"""
        manufacturing_terms = [
            'supplier', 'delivery', 'performance', 'ncm', 'defect', 'quality',
            'oee', 'equipment', 'downtime', 'production', 'capa', 'mtbf',
            'manufacturing', 'process', 'efficiency', 'yield', 'throughput'
        ]
        
        query_lower = query.lower()
        matches = sum(1 for term in manufacturing_terms if term in query_lower)
        return min(matches / 3.0, 1.0)  # Normalize to 0-1 scale
    
    def get_session_summary(self) -> Dict[str, Any]:
        """Generate comprehensive session metrics summary"""
        if not self.metrics_log:
            return {"status": "No queries recorded"}
            
        avg_confidence = sum(m.confidence_score for m in self.metrics_log) / len(self.metrics_log)
        avg_response_time = sum(m.response_time for m in self.metrics_log) / len(self.metrics_log)
        avg_domain_relevance = sum(m.domain_relevance for m in self.metrics_log) / len(self.metrics_log)
        
        complexity_dist = {}
        for m in self.metrics_log:
            complexity_dist[m.sql_complexity] = complexity_dist.get(m.sql_complexity, 0) + 1
            
        return {
            "session_duration": (datetime.now() - self.session_start).total_seconds(),
            "total_queries": self.total_queries,
            "avg_confidence": round(avg_confidence, 3),
            "avg_response_time": round(avg_response_time, 3),
            "avg_domain_relevance": round(avg_domain_relevance, 3),
            "total_cost": round(self.cumulative_cost, 4),
            "safety_success_rate": sum(1 for m in self.metrics_log if m.safety_score > 0.0) / len(self.metrics_log),
            "complexity_distribution": complexity_dist,
            "queries_per_minute": round(self.total_queries / ((datetime.now() - self.session_start).total_seconds() / 60), 2)
        }

class FewShotSQLGenerator:
    """
    Educational implementation of few-shot SQL generation
    Based on Frank Kane's Advanced RAG techniques
    
    Study Areas:
    1. Few-shot prompt engineering
    2. Domain-specific examples
    3. Manufacturing intelligence
    4. LangChain metrics (to be added incrementally)
    """
    
    def __init__(self):
        """Initialize with manufacturing examples for few-shot learning"""
        self.client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        # Initialize Advanced RAG metrics tracking
        self.metrics_tracker = AdvancedRAGMetrics()
        
        self.manufacturing_examples = self._load_core_examples()
        self.few_shot_template = self._setup_few_shot_template()
        print("🎯 Few-Shot SQL Generator initialized")
        print(f"   Loaded {len(self.manufacturing_examples)} manufacturing examples")
        print("📊 LangChain Advanced RAG metrics enabled")
    
    def _load_core_examples(self) -> List[SQLExample]:
        """
        Load core manufacturing examples for few-shot learning
        These are high-quality examples from your comprehensive database
        """
        return [
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
                explanation="Identifies underperforming suppliers with recent delivery data, prioritized by contract value",
                complexity="medium",
                domain="supply_chain"
            ),
            
            SQLExample(
                natural_language="Find products with NCM rates above industry standards",
                sql_query="""
                SELECT 
                    pd.product_line,
                    AVG(pd.defect_rate) as avg_ncm_rate,
                    COUNT(pd.production_date) as production_days,
                    SUM(pd.defect_count) as total_ncm_units,
                    ib.benchmark_value as industry_standard
                FROM product_defects pd
                JOIN industry_benchmarks ib ON ib.metric_name = 'defect_rate'
                WHERE pd.production_date >= CURRENT_DATE - INTERVAL '90 days'
                GROUP BY pd.product_line, ib.benchmark_value
                HAVING AVG(pd.defect_rate) > ib.benchmark_value
                ORDER BY avg_ncm_rate DESC
                """,
                explanation="Analyzes Non-Conformant Material rates against industry benchmarks for quality control",
                complexity="medium",
                domain="quality_control"
            ),
            
            SQLExample(
                natural_language="Calculate OEE for critical equipment showing downtime issues",
                sql_query="""
                SELECT 
                    pl.line_name,
                    pl.efficiency_rating as design_efficiency,
                    AVG(em.availability) as avg_availability,
                    AVG(em.performance_rate) as avg_performance,
                    AVG(em.quality_rate) as avg_quality,
                    (AVG(em.availability) * AVG(em.performance_rate) * AVG(em.quality_rate)) as calculated_oee,
                    COUNT(de.event_id) as downtime_events
                FROM production_lines pl
                JOIN equipment_metrics em ON pl.line_id = em.line_id
                LEFT JOIN downtime_events de ON pl.line_id = de.line_id
                    AND de.event_start_time >= CURRENT_DATE - INTERVAL '30 days'
                WHERE em.measurement_date >= CURRENT_DATE - INTERVAL '30 days'
                GROUP BY pl.line_id, pl.line_name, pl.efficiency_rating
                HAVING (AVG(em.availability) * AVG(em.performance_rate) * AVG(em.quality_rate)) < 0.75
                ORDER BY calculated_oee ASC, downtime_events DESC
                """,
                explanation="Calculates Overall Equipment Effectiveness (OEE = Availability × Performance × Quality) for lines below 75% target",
                complexity="complex",
                domain="production_efficiency"
            )
        ]
    
    def _setup_few_shot_template(self) -> FewShotPromptTemplate:
        """
        Setup few-shot prompt template using Frank Kane's methodology
        This is the core of few-shot learning implementation
        """
        
        # Template for each example in the few-shot prompt
        example_template = """
        Business Query: {natural_language}
        Domain: {domain}
        
        SQL Query:
        {sql_query}
        
        Explanation: {explanation}
        Complexity: {complexity}
        ---
        """
        
        example_prompt = PromptTemplate(
            input_variables=["natural_language", "sql_query", "explanation", "domain", "complexity"],
            template=example_template
        )
        
        # System prompt with manufacturing domain knowledge
        system_prompt = """You are an expert SQL assistant specializing in manufacturing and supply chain analytics.

CRITICAL RULES:
- Generate ONLY SELECT or WITH statements
- Use proper PostgreSQL syntax with explicit JOIN conditions
- Include appropriate aggregations and window functions for analytics
- Add business logic for manufacturing KPIs
- Use parameter placeholders (%s) for dynamic values
- Include meaningful column aliases and sorting

MANUFACTURING DOMAIN KNOWLEDGE:
- NCM = Non-Conformant Material (quality defects)
- OTD = On-Time Delivery (supply chain performance)  
- OEE = Overall Equipment Effectiveness (Availability × Performance × Quality)
- DPMO = Defects Per Million Opportunities
- MTBF = Mean Time Between Failures
- CAPA = Corrective and Preventive Actions

DATABASE SCHEMA CONTEXT:
{schema_context}

RESPONSE FORMAT:
SQL: [PostgreSQL query with proper business logic]
EXPLANATION: [Business context and query logic]
CONFIDENCE: [0.0-1.0 score]
COMPLEXITY: [simple|medium|complex]

Here are examples of high-quality manufacturing SQL queries:
"""
        
        # Create the few-shot prompt template
        few_shot_template = FewShotPromptTemplate(
            examples=[asdict(ex) for ex in self.manufacturing_examples],
            example_prompt=example_prompt,
            prefix=system_prompt,
            suffix="""Business Query: {user_query}

Generate SQL using EXACTLY this format:
SQL: [your PostgreSQL query here]
EXPLANATION: [business context and logic]
CONFIDENCE: [score between 0.0-1.0]
COMPLEXITY: [simple|medium|complex]

Response:""",
            input_variables=["user_query", "schema_context"]
        )
        
        return few_shot_template
    
    def generate_sql_with_few_shot(self, user_query: str, use_compact_schema: bool = True) -> Dict[str, Any]:
        """
        Generate SQL using few-shot learning approach with Advanced RAG metrics
        This is your main study method for Frank Kane techniques
        """
        print(f"🔍 Processing query: {user_query}")
        start_time = time.time()
        
        try:
            # Get database schema context (compact version for token efficiency)
            if use_compact_schema:
                schema_context = self._get_compact_schema_context()
            else:
                schema_context = get_schema_context()
            
            # Format the few-shot prompt
            formatted_prompt = self.few_shot_template.format(
                user_query=user_query,
                schema_context=schema_context
            )
            
            # Track token usage for cost analysis
            with get_openai_callback() as cb:
                response = self.client.chat.completions.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": formatted_prompt}],
                    temperature=0.1,
                    max_tokens=800  # Reduced for token efficiency
                )
                
                # Calculate response time
                response_time = time.time() - start_time
                
                # Extract response
                sql_response = response.choices[0].message.content
                
                # Parse the structured response
                result = self._parse_sql_response(sql_response)
                
                # Add token usage metrics for Frank Kane analysis
                token_usage = {
                    'total_tokens': cb.total_tokens,
                    'prompt_tokens': cb.prompt_tokens,
                    'completion_tokens': cb.completion_tokens,
                    'total_cost': cb.total_cost
                }
                result['token_usage'] = token_usage
                
                # Validate SQL safety
                if result.get('sql'):
                    safety_check = validate_sql_safety(result['sql'])
                    result['safety_check'] = safety_check
                
                # Record comprehensive metrics
                metrics = self.metrics_tracker.record_query_metrics(
                    query=user_query,
                    result=result,
                    response_time=response_time,
                    token_usage=token_usage
                )
                
                print(f"✅ Generated SQL with {result.get('confidence', 0):.3f} confidence")
                print(f"📊 Domain relevance: {metrics.domain_relevance:.2f} | Response time: {response_time:.3f}s")
                
                return result
                
        except Exception as e:
            response_time = time.time() - start_time
            print(f"❌ Few-shot generation failed: {e}")
            
            # Record failed query metrics
            error_result = {
                'error': str(e),
                'sql': None,
                'confidence': 0.0,
                'safety_check': False
            }
            
            self.metrics_tracker.record_query_metrics(
                query=user_query,
                result=error_result,
                response_time=response_time
            )
            
            return error_result
    
    def _parse_sql_response(self, response: str) -> Dict[str, Any]:
        """Parse structured response from the model with debug output"""
        
        # Debug: Show what we received from OpenAI (disabled for clean output)
        # print(f"🔍 DEBUG: Raw OpenAI response:\n{response[:500]}...")
        
        result = {
            'sql': None,
            'explanation': '',
            'confidence': 0.0,
            'complexity': 'unknown'
        }
        
        lines = response.strip().split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            if line.startswith('SQL:'):
                current_section = 'sql'
                result['sql'] = line[4:].strip()
            elif line.startswith('EXPLANATION:'):
                current_section = 'explanation'
                result['explanation'] = line[12:].strip()
            elif line.startswith('CONFIDENCE:'):
                confidence_str = line[11:].strip()
                # Debug output disabled for clean display
                # print(f"🔍 DEBUG: Found confidence string: '{confidence_str}'")
                try:
                    result['confidence'] = float(confidence_str)
                    # print(f"🔍 DEBUG: Parsed confidence: {result['confidence']}")
                except Exception as e:
                    # print(f"🔍 DEBUG: Failed to parse confidence '{confidence_str}': {e}")
                    result['confidence'] = 0.8  # Better default than 0.0
            elif line.startswith('COMPLEXITY:'):
                result['complexity'] = line[11:].strip().lower()
            elif current_section == 'sql' and line and not line.startswith(('EXPLANATION:', 'CONFIDENCE:', 'COMPLEXITY:')):
                result['sql'] += '\n' + line
            elif current_section == 'explanation' and line and not line.startswith(('CONFIDENCE:', 'COMPLEXITY:')):
                result['explanation'] += ' ' + line
        
        return result
    
    def _get_compact_schema_context(self) -> str:
        """
        Get a compact schema context for token efficiency
        Focus on key manufacturing tables for few-shot learning
        """
        compact_schema = """
CORE MANUFACTURING TABLES:

SUPPLIERS: supplier_id, supplier_name, contract_value, performance_rating
DAILY_DELIVERIES: delivery_id, supplier_id, delivery_date, ontime_rate, quantity_delivered

PRODUCT_DEFECTS: defect_id, product_line, production_date, defect_rate, defect_count, total_produced
INDUSTRY_BENCHMARKS: benchmark_id, metric_name, benchmark_value, industry_sector

PRODUCTION_LINES: line_id, line_name, efficiency_rating, theoretical_capacity, actual_capacity
EQUIPMENT_METRICS: metric_id, line_id, measurement_date, availability, performance_rate, quality_rate
DOWNTIME_EVENTS: event_id, line_id, event_start_time, downtime_duration_minutes, downtime_category

QUALITY_INCIDENTS: incident_id, product_line, incident_date, severity_level, cost_impact
FINANCIAL_IMPACT: impact_id, event_date, impact_type, gross_impact, net_impact

Key Manufacturing KPIs:
- OEE = Availability × Performance × Quality  
- NCM = Non-Conformant Material rates
- OTD = On-Time Delivery performance
- DPMO = Defects Per Million Opportunities
        """
        return compact_schema
    
    def analyze_few_shot_performance(self, test_queries: List[str]) -> Dict[str, Any]:
        """
        Analyze few-shot performance across multiple queries
        Educational method for studying Frank Kane metrics
        """
        print("📊 ANALYZING FEW-SHOT PERFORMANCE")
        print("=" * 50)
        
        results = []
        total_cost = 0.0
        successful_queries = 0
        
        for i, query in enumerate(test_queries, 1):
            print(f"\n{i}. Testing: {query}")
            result = self.generate_sql_with_few_shot(query)
            
            if not result.get('error'):
                successful_queries += 1
                total_cost += result.get('token_usage', {}).get('total_cost', 0)
                
            results.append({
                'query': query,
                'result': result,
                'success': not result.get('error')
            })
        
        # Calculate performance metrics
        success_rate = successful_queries / len(test_queries)
        avg_confidence = sum(r['result'].get('confidence', 0) for r in results) / len(results)
        
        performance_summary = {
            'success_rate': success_rate,
            'average_confidence': avg_confidence,
            'total_cost': total_cost,
            'queries_tested': len(test_queries),
            'successful_queries': successful_queries,
            'detailed_results': results
        }
        
        # Get comprehensive Advanced RAG metrics
        session_summary = self.metrics_tracker.get_session_summary()
        
        print(f"\n📈 PERFORMANCE SUMMARY:")
        print(f"   Success Rate: {success_rate:.1%}")
        print(f"   Average Confidence: {avg_confidence:.3f}")
        print(f"   Total Cost: ${total_cost:.4f}")
        print(f"   Queries Tested: {len(test_queries)}")
        
        # Display Advanced RAG metrics
        print(f"\n🧠 ADVANCED RAG METRICS:")
        print(f"   Domain Relevance: {session_summary.get('avg_domain_relevance', 0):.2f}")
        print(f"   Response Time: {session_summary.get('avg_response_time', 0):.3f}s") 
        print(f"   Safety Success: {session_summary.get('safety_success_rate', 0):.1%}")
        print(f"   Queries/Min: {session_summary.get('queries_per_minute', 0):.1f}")
        
        # Add advanced metrics to performance summary
        performance_summary.update({
            'advanced_rag_metrics': session_summary,
            'study_recommendations': self._generate_study_recommendations(session_summary)
        })
        
        return performance_summary
    
    def display_detailed_metrics_report(self):
        """Display comprehensive Frank Kane-style metrics for educational analysis"""
        report = self.get_detailed_metrics_report()
        
        print("\n" + "="*60)
        print("🧠 DETAILED ADVANCED RAG METRICS REPORT")
        print("   Frank Kane's Advanced RAG Analysis")
        print("="*60)
        
        # Session overview
        overview = report['session_overview']
        print(f"\n📊 SESSION OVERVIEW:")
        print(f"   Duration: {overview.get('session_duration', 0):.1f}s")
        print(f"   Total Queries: {overview.get('total_queries', 0)}")
        print(f"   Average Confidence: {overview.get('avg_confidence', 0):.3f}")
        print(f"   Average Domain Relevance: {overview.get('avg_domain_relevance', 0):.2f}")
        print(f"   Total Cost: ${overview.get('total_cost', 0):.4f}")
        
        # Performance trends
        trends = report['performance_trends']
        print(f"\n📈 PERFORMANCE TRENDS:")
        print(f"   Confidence Consistency: {trends.get('consistency_score', 0):.2f}")
        print(f"   Response Time Range: {min(trends.get('response_time_progression', [0])):.3f}s - {max(trends.get('response_time_progression', [0])):.3f}s")
        
        # Study recommendations
        recommendations = report['recommendations']
        print(f"\n🎯 STUDY RECOMMENDATIONS:")
        for i, rec in enumerate(recommendations, 1):
            print(f"   {i}. {rec}")
            
        print("\n✅ Detailed analysis complete!")
        print("   Use these insights for your Frank Kane Advanced RAG study")
    
    def get_detailed_metrics_report(self) -> Dict[str, Any]:
        """Generate detailed Frank Kane-style metrics report"""
        session_summary = self.metrics_tracker.get_session_summary()
        
        # Individual query metrics for detailed analysis
        query_details = []
        for metric in self.metrics_tracker.metrics_log:
            query_details.append({
                'query_id': metric.query_id,
                'query': metric.query_text[:50] + "..." if len(metric.query_text) > 50 else metric.query_text,
                'confidence': metric.confidence_score,
                'domain_relevance': metric.domain_relevance,
                'response_time': metric.response_time,
                'safety_score': metric.safety_score,
                'cost': metric.cost,
                'complexity': metric.sql_complexity
            })
        
        # Performance trends analysis
        confidence_trend = [m.confidence_score for m in self.metrics_tracker.metrics_log]
        response_time_trend = [m.response_time for m in self.metrics_tracker.metrics_log]
        
        return {
            'session_overview': session_summary,
            'query_details': query_details,
            'performance_trends': {
                'confidence_progression': confidence_trend,
                'response_time_progression': response_time_trend,
                'consistency_score': 1.0 - (max(confidence_trend) - min(confidence_trend)) if confidence_trend else 0.0
            },
            'recommendations': self._generate_study_recommendations(session_summary)
        }
    
    def _generate_study_recommendations(self, metrics: Dict[str, Any]) -> List[str]:
        """Generate study recommendations based on Advanced RAG metrics"""
        recommendations = []
        
        if metrics.get('avg_confidence', 0) < 0.8:
            recommendations.append("Focus on improving few-shot examples quality and domain specificity")
            
        if metrics.get('avg_response_time', 0) > 3.0:
            recommendations.append("Consider optimizing prompt length or using more efficient models")
            
        if metrics.get('avg_domain_relevance', 0) < 0.7:
            recommendations.append("Enhance manufacturing domain terminology in training examples")
            
        if metrics.get('total_cost', 0) > 0.05:
            recommendations.append("Implement token optimization strategies to reduce costs")
            
        if len(recommendations) == 0:
            recommendations.append("Excellent performance! Ready for advanced RAG techniques like vector retrieval")
            
        return recommendations

def main():
    """Main entry point for few-shot learning experimentation"""
    print("🚀 ENTRY POINT 001: FEW-SHOT LEARNING")
    print("   Frank Kane's Advanced RAG Techniques")
    print("=" * 60)
    
    # Initialize few-shot generator
    generator = FewShotSQLGenerator()
    
    # Test queries for manufacturing intelligence
    test_queries = [
        "Show suppliers with delivery performance below 95%",
        "Find products with NCM rates trending above industry standards",
        "Calculate OEE for critical equipment showing downtime issues",
        "Analyze CAPA effectiveness for recurring quality incidents",
        "Show equipment with MTBF below target requiring immediate attention"
    ]
    
    print(f"\n🧪 Testing {len(test_queries)} manufacturing intelligence queries...")
    
    # Analyze few-shot performance
    performance = generator.analyze_few_shot_performance(test_queries)
    
    # Display detailed Advanced RAG metrics report
    generator.display_detailed_metrics_report()
    
    print(f"\n✅ Few-shot analysis complete!")
    print(f"   Study this implementation to understand Frank Kane's techniques")
    print(f"   Next: Add vector stores and retrieval mechanisms for Advanced RAG")
    
    return performance

if __name__ == "__main__":
    main()