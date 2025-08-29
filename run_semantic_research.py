#!/usr/bin/env python3
"""
Semantic Layer Research Runner
Execute comprehensive evaluation and research on SQL generation improvements
"""

import asyncio
import json
import os
from datetime import datetime

# Ensure the app directory is in the Python path
import sys
sys.path.append('app')

from semantic_layer_research import researcher

async def main():
    """Run comprehensive semantic layer research"""
    print("🔬 SEMANTIC LAYER RESEARCH FRAMEWORK")
    print("   Advanced RAG & RAGAS Evaluation for SQL Generation")
    print("=" * 60)
    print()
    
    print("🚀 Starting comparative evaluation...")
    print("   - Testing standard vs advanced semantic layers")
    print("   - Manufacturing domain focus")
    print("   - 6 comprehensive test scenarios")
    print()
    
    try:
        # Run comparative evaluation
        results = await researcher.run_comparative_evaluation()
        
        print("📊 EVALUATION RESULTS")
        print("=" * 40)
        
        # Display success rates
        perf = results.get('performance_comparison', {})
        success_rates = perf.get('success_rates', {})
        confidence = perf.get('average_confidence', {})
        safety = perf.get('safety_compliance', {})
        
        print(f"Success Rates:")
        print(f"  Standard Layer: {success_rates.get('standard', 0):.1%}")
        print(f"  Advanced Layer: {success_rates.get('advanced', 0):.1%}")
        print()
        
        print(f"Average Confidence:")
        print(f"  Standard Layer: {confidence.get('standard', 0):.3f}")
        print(f"  Advanced Layer: {confidence.get('advanced', 0):.3f}")
        print()
        
        print(f"Safety Compliance:")
        print(f"  Standard Layer: {safety.get('standard', 0):.1%}")
        print(f"  Advanced Layer: {safety.get('advanced', 0):.1%}")
        print()
        
        # Show improvements
        improvements = perf.get('improvement_metrics', {})
        if improvements:
            print("🎯 IMPROVEMENTS ACHIEVED:")
            print(f"  Success Rate: {improvements.get('success_rate_improvement', 0):+.1%}")
            print(f"  Confidence: {improvements.get('confidence_improvement', 0):+.1%}")
            print()
        
        # Display sample results
        print("📝 SAMPLE GENERATED QUERIES:")
        print("-" * 40)
        
        advanced_results = results.get('advanced_layer_results', [])
        for i, result in enumerate(advanced_results[:3]):
            if 'error' not in result:
                print(f"\n{i+1}. Query: {result['query'][:60]}...")
                print(f"   SQL: {result['generated_sql'][:100]}...")
                print(f"   Confidence: {result['confidence']:.3f}")
                print(f"   Safety: {'✅' if result['safety_check'] else '❌'}")
        
        # Generate and save report
        print("\n📄 Generating research report...")
        report = researcher.generate_research_report(results)
        
        # Save results
        filename = researcher.save_research_results(results)
        
        report_filename = f"semantic_research_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(report_filename, 'w') as f:
            f.write(report)
        
        print(f"✅ Research completed successfully!")
        print(f"   Results saved: {filename}")
        print(f"   Report saved: {report_filename}")
        print()
        
        # Show next steps
        print("🔬 NEXT RESEARCH DIRECTIONS:")
        print("  1. Fine-tune RAG retrieval parameters")
        print("  2. Expand manufacturing domain examples")
        print("  3. Implement RAGAS evaluation metrics")
        print("  4. Test with real production data")
        print("  5. Develop domain-specific evaluation criteria")
        
        return results
        
    except Exception as e:
        print(f"❌ Research failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def run_quick_test():
    """Run a quick test of semantic layer capabilities"""
    print("🧪 QUICK SEMANTIC LAYER TEST")
    print("=" * 30)
    
    from app.semantic_layer import SemanticLayer, QueryRequest
    from app.advanced_semantic_layer import AdvancedSemanticLayer
    
    # Test queries
    test_queries = [
        "Show suppliers with poor delivery performance",
        "Find products with NCM rates above 2.5%",
        "Calculate OEE for critical equipment"
    ]
    
    standard_layer = SemanticLayer()
    advanced_layer = AdvancedSemanticLayer()
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{i}. Testing: {query}")
        
        request = QueryRequest(natural_language=query)
        
        try:
            # Standard layer
            std_result = standard_layer.process_query(request)
            print(f"   Standard: {std_result.confidence_score:.3f} confidence, Safety: {'✅' if std_result.safety_check else '❌'}")
            
            # Advanced layer
            adv_result = advanced_layer.generate_advanced_sql(request)
            print(f"   Advanced: {adv_result.confidence_score:.3f} confidence, Safety: {'✅' if adv_result.safety_check else '❌'}")
            
        except Exception as e:
            print(f"   Error: {e}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Semantic Layer Research Framework")
    parser.add_argument("--quick", action="store_true", help="Run quick test instead of full evaluation")
    args = parser.parse_args()
    
    if args.quick:
        run_quick_test()
    else:
        asyncio.run(main())