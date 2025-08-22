#!/usr/bin/env python3
"""
Semantic Layer Research Demo
Advanced SQL generation evaluation and improvement demonstration
"""

import sys
import os
import json
from datetime import datetime
from typing import Dict, List, Any

# Add app directory to path
sys.path.append('app')

from semantic_layer import SemanticLayer, QueryRequest, QueryComplexity
from contextual_hints import get_contextual_hints

class SemanticLayerComparison:
    """Compare different approaches to SQL generation"""
    
    def __init__(self):
        self.standard_layer = SemanticLayer()
        self.test_results = []
    
    def create_manufacturing_test_set(self) -> List[Dict]:
        """Create test queries for manufacturing domain evaluation"""
        return [
            {
                "id": "supply_chain_001",
                "query": "Show suppliers with delivery performance below 95% affecting production schedule",
                "domain": "supply_chain",
                "expected_concepts": ["supplier", "delivery", "performance", "threshold"],
                "complexity": "medium"
            },
            {
                "id": "quality_001", 
                "query": "Find products with NCM rates trending above industry standards",
                "domain": "quality_control",
                "expected_concepts": ["NCM", "defect", "trend", "benchmark"],
                "complexity": "complex"
            },
            {
                "id": "production_001",
                "query": "Calculate OEE for critical equipment showing downtime patterns",
                "domain": "production_efficiency",
                "expected_concepts": ["OEE", "equipment", "availability", "performance"],
                "complexity": "complex"
            },
            {
                "id": "maintenance_001",
                "query": "Show equipment with MTBF below target requiring immediate attention",
                "domain": "maintenance",
                "expected_concepts": ["MTBF", "reliability", "target", "maintenance"],
                "complexity": "medium"
            },
            {
                "id": "compliance_001",
                "query": "Analyze CAPA effectiveness for recurring quality issues",
                "domain": "compliance", 
                "expected_concepts": ["CAPA", "effectiveness", "recurrence", "quality"],
                "complexity": "complex"
            }
        ]
    
    def evaluate_query_generation(self, test_case: Dict) -> Dict[str, Any]:
        """Evaluate SQL generation for a single test case"""
        
        # Create request
        request = QueryRequest(
            natural_language=test_case["query"],
            user_id="research_test"
        )
        
        # Test standard semantic layer
        try:
            result = self.standard_layer.process_query(request)
            
            # Get contextual hints for comparison
            hints = get_contextual_hints(test_case["query"], [])
            
            # Analyze result quality
            quality_score = self._analyze_sql_quality(result.sql_query, test_case)
            concept_coverage = self._analyze_concept_coverage(result.sql_query, result.explanation, test_case)
            
            evaluation = {
                "test_id": test_case["id"],
                "domain": test_case["domain"],
                "query": test_case["query"],
                "generated_sql": result.sql_query,
                "confidence": result.confidence_score,
                "complexity": str(result.complexity),
                "explanation": result.explanation,
                "safety_check": result.safety_check,
                "quality_score": quality_score,
                "concept_coverage": concept_coverage,
                "contextual_hints_count": len(hints),
                "acronyms_detected": self._count_acronyms_in_hints(hints),
                "timestamp": datetime.now().isoformat()
            }
            
            return evaluation
            
        except Exception as e:
            return {
                "test_id": test_case["id"],
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def _analyze_sql_quality(self, sql: str, test_case: Dict) -> float:
        """Analyze the quality of generated SQL"""
        score = 0.0
        sql_upper = sql.upper()
        
        # Basic syntax check (30% of score)
        if sql_upper.startswith("SELECT") or sql_upper.startswith("WITH"):
            score += 0.3
        
        # Manufacturing domain relevance (40% of score)
        domain_keywords = {
            "supply_chain": ["SUPPLIER", "DELIVERY", "ONTIME", "SHIPMENT"],
            "quality_control": ["DEFECT", "QUALITY", "NCM", "CONFORMANT"],
            "production_efficiency": ["PRODUCTION", "OEE", "EQUIPMENT", "EFFICIENCY"],
            "maintenance": ["MTBF", "FAILURE", "MAINTENANCE", "RELIABILITY"],
            "compliance": ["CAPA", "CORRECTIVE", "ACTION", "COMPLIANCE"]
        }
        
        domain = test_case.get("domain", "")
        if domain in domain_keywords:
            keywords_found = sum(1 for keyword in domain_keywords[domain] if keyword in sql_upper)
            score += 0.4 * min(keywords_found / len(domain_keywords[domain]), 1.0)
        
        # SQL best practices (30% of score)
        best_practices_score = 0.0
        
        # Proper JOIN usage
        if "JOIN" in sql_upper and "ON" in sql_upper:
            best_practices_score += 0.1
        
        # Aggregation functions for analytics
        if any(agg in sql_upper for agg in ["AVG(", "SUM(", "COUNT(", "GROUP BY"]):
            best_practices_score += 0.1
        
        # Filtering with WHERE
        if "WHERE" in sql_upper:
            best_practices_score += 0.05
        
        # Proper ordering
        if "ORDER BY" in sql_upper:
            best_practices_score += 0.05
        
        score += best_practices_score
        
        return min(score, 1.0)
    
    def _analyze_concept_coverage(self, sql: str, explanation: str, test_case: Dict) -> float:
        """Analyze how well the SQL covers expected business concepts"""
        expected_concepts = test_case.get("expected_concepts", [])
        if not expected_concepts:
            return 0.5
        
        combined_text = (sql + " " + explanation).upper()
        concepts_found = 0
        
        for concept in expected_concepts:
            concept_upper = concept.upper()
            if concept_upper in combined_text:
                concepts_found += 1
            # Check for common variations
            elif concept_upper == "NCM" and ("NON" in combined_text and "CONFORM" in combined_text):
                concepts_found += 1
            elif concept_upper == "OEE" and ("EQUIPMENT" in combined_text and "EFFECTIVENESS" in combined_text):
                concepts_found += 1
            elif concept_upper == "MTBF" and ("MEAN" in combined_text and "FAILURE" in combined_text):
                concepts_found += 1
        
        return concepts_found / len(expected_concepts)
    
    def _count_acronyms_in_hints(self, hints: List[Dict]) -> int:
        """Count manufacturing acronyms detected in contextual hints"""
        acronym_count = 0
        for hint in hints:
            if hint.get("type") == "acronym":
                acronym_count += 1
        return acronym_count
    
    def run_comprehensive_evaluation(self) -> Dict[str, Any]:
        """Run evaluation on all test cases"""
        print("🔬 SEMANTIC LAYER RESEARCH EVALUATION")
        print("   Advanced SQL Generation for Manufacturing Intelligence")
        print("=" * 60)
        print()
        
        test_cases = self.create_manufacturing_test_set()
        results = []
        
        print(f"📊 Testing {len(test_cases)} manufacturing domain queries...")
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"   {i}. {test_case['domain']}: {test_case['query'][:50]}...")
            
            evaluation = self.evaluate_query_generation(test_case)
            results.append(evaluation)
            
            if 'error' not in evaluation:
                print(f"      ✅ Success - Quality: {evaluation['quality_score']:.2f}, Confidence: {evaluation['confidence']:.2f}")
            else:
                print(f"      ❌ Error: {evaluation['error']}")
        
        # Calculate summary statistics
        successful_results = [r for r in results if 'error' not in r]
        
        summary = {
            "total_tests": len(test_cases),
            "successful_tests": len(successful_results),
            "success_rate": len(successful_results) / len(test_cases) if test_cases else 0,
            "average_quality": sum(r['quality_score'] for r in successful_results) / len(successful_results) if successful_results else 0,
            "average_confidence": sum(r['confidence'] for r in successful_results) / len(successful_results) if successful_results else 0,
            "average_concept_coverage": sum(r['concept_coverage'] for r in successful_results) / len(successful_results) if successful_results else 0,
            "total_acronyms_detected": sum(r['acronyms_detected'] for r in successful_results),
            "safety_compliance": sum(1 for r in successful_results if r['safety_check']) / len(successful_results) if successful_results else 0
        }
        
        # Domain-specific analysis
        domain_analysis = {}
        for result in successful_results:
            domain = result['domain']
            if domain not in domain_analysis:
                domain_analysis[domain] = {
                    'count': 0,
                    'quality_scores': [],
                    'confidence_scores': [],
                    'concept_coverage': []
                }
            
            domain_analysis[domain]['count'] += 1
            domain_analysis[domain]['quality_scores'].append(result['quality_score'])
            domain_analysis[domain]['confidence_scores'].append(result['confidence'])
            domain_analysis[domain]['concept_coverage'].append(result['concept_coverage'])
        
        # Calculate domain averages
        for domain, data in domain_analysis.items():
            data['avg_quality'] = sum(data['quality_scores']) / len(data['quality_scores'])
            data['avg_confidence'] = sum(data['confidence_scores']) / len(data['confidence_scores'])
            data['avg_concept_coverage'] = sum(data['concept_coverage']) / len(data['concept_coverage'])
        
        return {
            "timestamp": datetime.now().isoformat(),
            "test_results": results,
            "summary_statistics": summary,
            "domain_analysis": domain_analysis,
            "research_insights": self._generate_research_insights(summary, domain_analysis)
        }
    
    def _generate_research_insights(self, summary: Dict, domain_analysis: Dict) -> List[str]:
        """Generate research insights from evaluation results"""
        insights = []
        
        # Overall performance insights
        if summary['success_rate'] >= 0.8:
            insights.append("High success rate indicates robust SQL generation capabilities")
        elif summary['success_rate'] >= 0.6:
            insights.append("Moderate success rate - room for improvement in error handling")
        else:
            insights.append("Low success rate indicates need for significant enhancement")
        
        # Quality insights
        if summary['average_quality'] >= 0.7:
            insights.append("Generated SQL demonstrates good structural quality and domain relevance")
        else:
            insights.append("SQL quality could be improved through better domain knowledge integration")
        
        # Concept coverage insights
        if summary['average_concept_coverage'] >= 0.6:
            insights.append("Strong business concept coverage in generated queries")
        else:
            insights.append("Business concept recognition needs enhancement for better domain alignment")
        
        # Domain-specific insights
        best_domain = max(domain_analysis.items(), key=lambda x: x[1]['avg_quality']) if domain_analysis else None
        if best_domain:
            insights.append(f"Strongest performance in {best_domain[0]} domain (quality: {best_domain[1]['avg_quality']:.2f})")
        
        # Acronym detection insights
        if summary['total_acronyms_detected'] > 0:
            insights.append(f"Contextual hints successfully detected {summary['total_acronyms_detected']} manufacturing acronyms")
        
        return insights
    
    def print_research_report(self, evaluation_results: Dict):
        """Print comprehensive research report"""
        print("\n" + "="*60)
        print("📊 SEMANTIC LAYER RESEARCH REPORT")
        print("="*60)
        
        summary = evaluation_results['summary_statistics']
        
        print(f"\n🎯 PERFORMANCE METRICS:")
        print(f"   Success Rate: {summary['success_rate']:.1%}")
        print(f"   Average SQL Quality: {summary['average_quality']:.3f}")
        print(f"   Average Confidence: {summary['average_confidence']:.3f}")
        print(f"   Concept Coverage: {summary['average_concept_coverage']:.1%}")
        print(f"   Safety Compliance: {summary['safety_compliance']:.1%}")
        print(f"   Acronyms Detected: {summary['total_acronyms_detected']}")
        
        print(f"\n📋 DOMAIN ANALYSIS:")
        domain_analysis = evaluation_results['domain_analysis']
        for domain, data in domain_analysis.items():
            print(f"   {domain.replace('_', ' ').title()}:")
            print(f"     Quality: {data['avg_quality']:.3f}")
            print(f"     Confidence: {data['avg_confidence']:.3f}")
            print(f"     Concept Coverage: {data['avg_concept_coverage']:.1%}")
        
        print(f"\n🔬 RESEARCH INSIGHTS:")
        for insight in evaluation_results['research_insights']:
            print(f"   • {insight}")
        
        print(f"\n📈 RECOMMENDATIONS:")
        if summary['average_quality'] < 0.7:
            print("   • Enhance domain-specific training examples")
        if summary['average_concept_coverage'] < 0.6:
            print("   • Improve business concept recognition")
        if summary['total_acronyms_detected'] < 3:
            print("   • Expand manufacturing acronym knowledge base")
        if summary['safety_compliance'] < 1.0:
            print("   • Strengthen SQL safety validation")
        
        print("\n" + "="*60)

def main():
    """Run semantic layer research evaluation"""
    researcher = SemanticLayerComparison()
    
    try:
        # Run comprehensive evaluation
        results = researcher.run_comprehensive_evaluation()
        
        # Print detailed report
        researcher.print_research_report(results)
        
        # Save results
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"semantic_research_results_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\n💾 Results saved to: {filename}")
        
        return results
        
    except Exception as e:
        print(f"❌ Research evaluation failed: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    main()