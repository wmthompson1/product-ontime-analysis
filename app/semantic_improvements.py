"""
Semantic Layer Improvements Based on Frank Kane's Advanced RAG Techniques
Implements enhanced SQL generation with few-shot learning and domain knowledge
"""

import os
import json
from typing import Dict, List, Any, Optional
from datetime import datetime

from semantic_layer import SemanticLayer, QueryRequest, QueryResult, QueryComplexity
from schema_context import get_schema_context, validate_sql_safety

class ImprovedSemanticLayer(SemanticLayer):
    """Enhanced semantic layer with advanced RAG-inspired techniques"""
    
    def __init__(self):
        super().__init__()
        self.manufacturing_examples = self._load_manufacturing_examples()
        self.domain_knowledge = self._build_domain_knowledge()
        self._enhance_templates()
    
    def _load_manufacturing_examples(self) -> List[Dict]:
        """Load high-quality manufacturing SQL examples for few-shot learning"""
        return [
            {
                "domain": "supply_chain",
                "query": "Show suppliers with delivery performance issues",
                "sql": """
                SELECT 
                    s.supplier_name,
                    s.contract_value,
                    AVG(d.ontime_rate) as avg_delivery_performance,
                    COUNT(d.delivery_id) as total_deliveries,
                    CASE 
                        WHEN AVG(d.ontime_rate) < 0.85 THEN 'Critical'
                        WHEN AVG(d.ontime_rate) < 0.95 THEN 'Needs Improvement'
                        ELSE 'Acceptable'
                    END as performance_status
                FROM suppliers s
                JOIN daily_deliveries d ON s.supplier_id = d.supplier_id
                WHERE d.date >= CURRENT_DATE - INTERVAL '90 days'
                GROUP BY s.supplier_id, s.supplier_name, s.contract_value
                HAVING AVG(d.ontime_rate) < 0.95
                ORDER BY s.contract_value DESC, avg_delivery_performance ASC
                """,
                "explanation": "Identifies underperforming suppliers with business impact prioritization",
                "concepts": ["OTD", "supplier performance", "business impact"]
            },
            {
                "domain": "quality_control",
                "query": "Find products with Non-Conformant Material rates above threshold",
                "sql": """
                SELECT 
                    product_line,
                    AVG(defect_rate) as avg_ncm_rate,
                    COUNT(production_date) as production_days,
                    SUM(total_produced) as total_units,
                    SUM(defect_count) as total_ncm_units,
                    (SUM(defect_count) * 1000000.0 / SUM(total_produced)) as dpmo_rate
                FROM product_defects
                WHERE production_date >= CURRENT_DATE - INTERVAL '90 days'
                GROUP BY product_line
                HAVING AVG(defect_rate) > 0.025
                ORDER BY avg_ncm_rate DESC, total_units DESC
                """,
                "explanation": "Analyzes NCM rates with DPMO calculation for Six Sigma compliance",
                "concepts": ["NCM", "defect rate", "DPMO", "quality standards"]
            },
            {
                "domain": "production_efficiency",
                "query": "Calculate Overall Equipment Effectiveness for manufacturing lines",
                "sql": """
                SELECT 
                    pl.line_name,
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
                GROUP BY pl.line_id, pl.line_name
                ORDER BY oee_score DESC
                """,
                "explanation": "Calculates OEE using standard formula with performance classification",
                "concepts": ["OEE", "availability", "performance", "quality", "world class"]
            }
        ]
    
    def _build_domain_knowledge(self) -> Dict[str, Dict]:
        """Build comprehensive domain knowledge for manufacturing"""
        return {
            "acronyms": {
                "NCM": "Non-Conformant Material - Quality defects requiring corrective action",
                "OTD": "On-Time Delivery - Supply chain performance metric",
                "OEE": "Overall Equipment Effectiveness - Production efficiency (Availability × Performance × Quality)",
                "DPMO": "Defects Per Million Opportunities - Six Sigma quality metric",
                "MTBF": "Mean Time Between Failures - Reliability metric",
                "CAPA": "Corrective and Preventive Action - Quality management process"
            },
            "business_rules": {
                "oee_thresholds": {"world_class": 0.85, "acceptable": 0.60},
                "delivery_targets": {"excellent": 0.98, "acceptable": 0.95, "poor": 0.90},
                "quality_standards": {"six_sigma": 0.00034, "industry_standard": 0.025}
            },
            "sql_patterns": {
                "trend_analysis": "Use window functions with LAG/LEAD for time series analysis",
                "performance_classification": "Use CASE statements for business rule implementation",
                "aggregation_best_practices": "Group by relevant dimensions, use appropriate aggregation functions"
            }
        }
    
    def _enhance_templates(self):
        """Enhance prompt templates with manufacturing domain knowledge"""
        
        manufacturing_context = f"""
MANUFACTURING DOMAIN KNOWLEDGE:
{json.dumps(self.domain_knowledge['acronyms'], indent=2)}

BUSINESS RULES:
- OEE World Class: ≥85%, Acceptable: ≥60%
- Delivery Performance: Excellent ≥98%, Acceptable ≥95%
- Quality Standards: Six Sigma ≤0.034%, Industry Standard ≤2.5%

SQL BEST PRACTICES FOR MANUFACTURING:
- Use proper business logic in CASE statements
- Include relevant time windows for trend analysis
- Apply appropriate aggregation for KPI calculations
- Add performance classifications based on industry standards
"""
        
        # Enhanced complex template
        self.templates["manufacturing"] = f"""
{manufacturing_context}

EXAMPLES OF HIGH-QUALITY MANUFACTURING QUERIES:

{self._format_examples_for_prompt()}

Generate a PostgreSQL query following these patterns for: "{{user_query}}"

Schema Context:
{{schema_context}}

Response format:
SQL: [optimized PostgreSQL query with business logic]
PARAMS: [parameter list]
EXPLANATION: [business context and query logic]
CONFIDENCE: [0.0-1.0 based on domain alignment]
"""
    
    def _format_examples_for_prompt(self) -> str:
        """Format examples for few-shot prompting"""
        formatted_examples = []
        
        for example in self.manufacturing_examples[:2]:  # Use top 2 examples
            formatted = f"""
Query: "{example['query']}"
SQL: {example['sql'].strip()}
Explanation: {example['explanation']}
Key Concepts: {', '.join(example['concepts'])}
"""
            formatted_examples.append(formatted)
        
        return "\n".join(formatted_examples)
    
    def _select_relevant_examples(self, query: str, domain: str = None) -> List[Dict]:
        """Select most relevant examples based on query content"""
        relevant_examples = []
        query_lower = query.lower()
        
        # Score examples based on relevance
        for example in self.manufacturing_examples:
            score = 0
            
            # Domain match
            if domain and example['domain'] == domain:
                score += 0.5
            
            # Concept match
            for concept in example['concepts']:
                if concept.lower() in query_lower:
                    score += 0.3
            
            # Keyword match
            example_keywords = example['query'].lower().split()
            query_keywords = query_lower.split()
            common_keywords = set(example_keywords) & set(query_keywords)
            score += len(common_keywords) * 0.1
            
            if score > 0.3:  # Threshold for relevance
                relevant_examples.append((example, score))
        
        # Sort by score and return top examples
        relevant_examples.sort(key=lambda x: x[1], reverse=True)
        return [ex[0] for ex in relevant_examples[:3]]
    
    def _detect_domain(self, query: str) -> str:
        """Detect manufacturing domain from query"""
        query_lower = query.lower()
        
        domain_keywords = {
            "supply_chain": ["supplier", "delivery", "shipment", "vendor", "otd"],
            "quality_control": ["quality", "defect", "ncm", "conformant", "dpmo"],
            "production_efficiency": ["production", "oee", "equipment", "efficiency", "throughput"],
            "maintenance": ["maintenance", "mtbf", "failure", "reliability", "downtime"],
            "compliance": ["capa", "corrective", "audit", "compliance", "regulatory"]
        }
        
        for domain, keywords in domain_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                return domain
        
        return "general"
    
    def generate_improved_sql(self, request: QueryRequest) -> QueryResult:
        """Generate SQL using improved RAG-inspired techniques"""
        
        # 1. Detect domain and select relevant examples
        domain = self._detect_domain(request.natural_language)
        relevant_examples = self._select_relevant_examples(request.natural_language, domain)
        
        # 2. Build enhanced context
        schema_context = get_schema_context(request.tables_hint)
        
        # 3. Use manufacturing-specific template
        template = self.templates.get("manufacturing", self.templates["complex"])
        
        try:
            prompt = template.format(
                user_query=request.natural_language,
                schema_context=schema_context
            )
            
            # 4. Generate SQL
            response = self._generate_sql_with_openai(prompt)
            parsed = self._parse_response(response["content"])
            
            # 5. Enhanced validation with domain knowledge
            is_safe, safety_message = validate_sql_safety(parsed["sql"])
            
            if not is_safe:
                return self._create_safe_fallback(request, safety_message)
            
            # 6. Domain-specific confidence adjustment
            confidence = self._adjust_confidence_for_domain(
                parsed["confidence"], 
                domain, 
                request.natural_language, 
                parsed["sql"]
            )
            
            # 7. Enhanced explanation with business context
            enhanced_explanation = self._enhance_explanation(
                parsed["explanation"], 
                domain, 
                relevant_examples
            )
            
            return QueryResult(
                sql_query=parsed["sql"],
                parameters=parsed["params"],
                confidence_score=confidence,
                complexity=parsed.get("complexity", QueryComplexity.MEDIUM),
                explanation=enhanced_explanation,
                safety_check=is_safe,
                estimated_cost=response.get("cost")
            )
            
        except Exception as e:
            return self._create_safe_fallback(request, str(e))
    
    def _adjust_confidence_for_domain(self, base_confidence: float, domain: str, query: str, sql: str) -> float:
        """Adjust confidence based on domain knowledge alignment"""
        
        # Start with base confidence
        confidence = base_confidence
        
        # Boost confidence for domain-specific acronym usage
        acronyms_in_query = [acronym for acronym in self.domain_knowledge["acronyms"] if acronym.lower() in query.lower()]
        if acronyms_in_query:
            confidence += 0.1 * len(acronyms_in_query)
        
        # Boost confidence for business rule implementation
        sql_upper = sql.upper()
        if "CASE" in sql_upper and domain in ["quality_control", "production_efficiency"]:
            confidence += 0.1
        
        # Boost confidence for appropriate aggregation
        if any(agg in sql_upper for agg in ["AVG(", "SUM(", "COUNT("]) and "GROUP BY" in sql_upper:
            confidence += 0.05
        
        return min(confidence, 1.0)
    
    def _enhance_explanation(self, base_explanation: str, domain: str, relevant_examples: List[Dict]) -> str:
        """Enhance explanation with business context"""
        
        enhanced = base_explanation
        
        # Add domain context
        if domain != "general":
            enhanced += f" This query focuses on {domain.replace('_', ' ')} analytics."
        
        # Add business rule context
        if domain in ["quality_control", "production_efficiency"]:
            enhanced += " Results include industry-standard performance classifications."
        
        # Add example reference if relevant
        if relevant_examples:
            enhanced += f" Similar to standard {domain.replace('_', ' ')} reporting patterns."
        
        return enhanced
    
    def _create_safe_fallback(self, request: QueryRequest, error_msg: str) -> QueryResult:
        """Create safe fallback result with domain context"""
        return QueryResult(
            sql_query="SELECT 'Query generation failed' as status, %s as error_message, %s as domain_hint",
            parameters=[error_msg, self._detect_domain(request.natural_language)],
            confidence_score=0.0,
            complexity=QueryComplexity.SIMPLE,
            explanation=f"Could not generate SQL: {error_msg}. Detected domain: {self._detect_domain(request.natural_language)}",
            safety_check=False
        )
    
    def get_domain_insights(self) -> Dict[str, Any]:
        """Get insights about domain knowledge and performance"""
        return {
            "supported_domains": list(set(ex["domain"] for ex in self.manufacturing_examples)),
            "acronyms_supported": list(self.domain_knowledge["acronyms"].keys()),
            "business_rules": self.domain_knowledge["business_rules"],
            "example_count": len(self.manufacturing_examples),
            "sql_patterns": list(self.domain_knowledge["sql_patterns"].keys())
        }

# Global improved instance
improved_semantic_layer = ImprovedSemanticLayer()