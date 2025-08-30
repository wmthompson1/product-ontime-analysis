#!/usr/bin/env python3
"""
Entry Point 001: Few-Shot Learning Implementation
Educational entry point for studying Frank Kane's Advanced RAG techniques
Incrementally implement LangChain metrics and few-shot prompting
"""

import os
import sys
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

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
        self.manufacturing_examples = self._load_core_examples()
        self.few_shot_template = self._setup_few_shot_template()
        print("🎯 Few-Shot SQL Generator initialized")
        print(f"   Loaded {len(self.manufacturing_examples)} manufacturing examples")
    
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
            suffix="Business Query: {user_query}\n\nGenerate SQL:",
            input_variables=["user_query", "schema_context"]
        )
        
        return few_shot_template
    
    def generate_sql_with_few_shot(self, user_query: str, use_compact_schema: bool = True) -> Dict[str, Any]:
        """
        Generate SQL using few-shot learning approach
        This is your main study method for Frank Kane techniques
        """
        print(f"🔍 Processing query: {user_query}")
        
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
                
                # Extract response
                sql_response = response.choices[0].message.content
                
                # Parse the structured response
                result = self._parse_sql_response(sql_response)
                
                # Add token usage metrics for Frank Kane analysis
                result['token_usage'] = {
                    'total_tokens': cb.total_tokens,
                    'prompt_tokens': cb.prompt_tokens,
                    'completion_tokens': cb.completion_tokens,
                    'total_cost': cb.total_cost
                }
                
                # Validate SQL safety
                if result.get('sql'):
                    safety_check = validate_sql_safety(result['sql'])
                    result['safety_check'] = safety_check
                
                print(f"✅ Generated SQL with {result.get('confidence', 0):.3f} confidence")
                return result
                
        except Exception as e:
            print(f"❌ Few-shot generation failed: {e}")
            return {
                'error': str(e),
                'sql': None,
                'confidence': 0.0,
                'safety_check': False
            }
    
    def _parse_sql_response(self, response: str) -> Dict[str, Any]:
        """Parse structured response from the model"""
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
                try:
                    result['confidence'] = float(line[11:].strip())
                except:
                    result['confidence'] = 0.5
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
        
        print(f"\n📈 PERFORMANCE SUMMARY:")
        print(f"   Success Rate: {success_rate:.1%}")
        print(f"   Average Confidence: {avg_confidence:.3f}")
        print(f"   Total Cost: ${total_cost:.4f}")
        print(f"   Queries Tested: {len(test_queries)}")
        
        return performance_summary

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
    
    print(f"\n✅ Few-shot analysis complete!")
    print(f"   Study this implementation to understand Frank Kane's techniques")
    print(f"   Next: Add incremental LangChain metrics as you progress")
    
    return performance

if __name__ == "__main__":
    main()