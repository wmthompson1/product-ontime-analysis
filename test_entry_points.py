#!/usr/bin/env python3
"""
test_entry_points.py
LangChain Academy-style pytest framework for Entry Points testing
Based on official LangChain Academy testing patterns
"""

import sys
from pathlib import Path

# Add project root to Python path (LangChain Academy pattern)
project_root = Path(__file__).parent
sys.path.append(str(project_root))

import pytest
import os
import json
import tempfile
from unittest.mock import patch, MagicMock
from typing import Dict, Any, List

# Import your Entry Point modules
import importlib.util

def import_entry_point_module(filename, class_name):
    """Safely import modules with numeric prefixes"""
    try:
        spec = importlib.util.spec_from_file_location("module", filename)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return getattr(module, class_name)
    except Exception:
        return None

# Import Entry Point classes safely
FewShotSQLGenerator = import_entry_point_module("Entry_Point_001_few_shot.py", "FewShotSQLGenerator")
FrankKaneRAGASDemoAgent = import_entry_point_module("001_Entry_Point_Kane_Ragas_Demo.py", "FrankKaneRAGASDemoAgent")
ManufacturingAmbientAgent = import_entry_point_module("007_Entry_Point_Ambient_Agents.py", "ManufacturingAmbientAgent")
CustomLLMJudge = import_entry_point_module("008_Entry_Point_Acad_LC_Start1.py", "CustomLLMJudge")

class TestFrankKaneRAGSystems:
    """Test suite for Frank Kane Advanced RAG implementations"""
    
    def test_few_shot_sql_generator_initialization(self):
        """Test FewShotSQLGenerator initializes correctly"""
        if FewShotSQLGenerator is None:
            print("⚠️ FewShotSQLGenerator not available - skipping test")
            return
            
        generator = FewShotSQLGenerator()
        assert hasattr(generator, 'manufacturing_examples')
        assert len(generator.manufacturing_examples) > 0
        print("✅ FewShotSQLGenerator initialization test passed")
    
    def test_manufacturing_example_structure(self):
        """Test manufacturing examples have required structure"""
        generator = FewShotSQLGenerator()
        
        for example in generator.manufacturing_examples:
            assert 'query' in example
            assert 'sql' in example
            assert 'explanation' in example
            assert 'complexity' in example
        
        print("✅ Manufacturing example structure test passed")
    
    def test_ragas_demo_agent_initialization(self):
        """Test RAGAS demo agent initializes without API dependencies"""
        agent = FrankKaneRAGASDemoAgent()
        assert hasattr(agent, 'manufacturing_keywords')
        assert hasattr(agent, 'ragas_metrics')
        assert len(agent.ragas_metrics) == 0  # Should start empty
        print("✅ RAGAS demo agent initialization test passed")
    
    def test_ragas_demo_evaluation_structure(self):
        """Test RAGAS evaluation returns proper structure"""
        agent = FrankKaneRAGASDemoAgent()
        
        # Mock evaluation
        mock_query = "Test manufacturing query"
        mock_result = {"sql": "SELECT * FROM test", "explanation": "Test explanation"}
        mock_context = {"results": [{"title": "Test", "content": "Test content"}], "relevance_score": 0.8}
        
        evaluation = agent.evaluate_with_ragas_demo(mock_query, mock_result, mock_context)
        
        # Check required RAGAS metrics
        required_metrics = ['faithfulness', 'answer_relevancy', 'context_precision', 'context_recall', 'domain_accuracy', 'composite_score']
        for metric in required_metrics:
            assert metric in evaluation
            assert 0.0 <= evaluation[metric] <= 1.0
        
        print("✅ RAGAS evaluation structure test passed")

class TestAmbientAgents:
    """Test suite for ambient agent implementations"""
    
    def test_manufacturing_ambient_agent_initialization(self):
        """Test manufacturing ambient agent initializes correctly"""
        agent = ManufacturingAmbientAgent()
        assert hasattr(agent, 'thresholds')
        assert hasattr(agent, 'memories')
        assert hasattr(agent, 'pending_reviews')
        assert agent.is_monitoring == False  # Should start inactive
        print("✅ Manufacturing ambient agent initialization test passed")
    
    def test_manufacturing_event_processing(self):
        """Test manufacturing event processing logic"""
        from 007_Entry_Point_Ambient_Agents import ManufacturingEvent, AlertSeverity
        
        agent = ManufacturingAmbientAgent()
        
        # Create test event
        test_event = ManufacturingEvent(
            event_id="TEST_001",
            event_type="quality_alert",
            severity=AlertSeverity.HIGH,
            description="Test quality alert",
            data={"defect_rate": 0.03},
            timestamp="2025-09-01T00:00:00",
            requires_human=True
        )
        
        # Test event processing
        initial_memory_count = len(agent.memories)
        agent._process_manufacturing_event(test_event)
        
        # Should have learned from this event
        assert len(agent.memories) > initial_memory_count
        print("✅ Manufacturing event processing test passed")

class TestLangChainAcademyIntegration:
    """Test suite for LangChain Academy evaluation patterns"""
    
    @patch('openai.OpenAI')
    def test_custom_llm_judge_initialization(self, mock_openai):
        """Test custom LLM judge initializes correctly"""
        judge = CustomLLMJudge()
        assert hasattr(judge, 'client')
        assert hasattr(judge, 'model')
        assert hasattr(judge, 'correctness_prompt')
        print("✅ Custom LLM judge initialization test passed")
    
    @patch('openai.OpenAI')
    def test_llm_judge_evaluation_structure(self, mock_openai):
        """Test LLM judge returns proper evaluation structure"""
        # Mock OpenAI response
        mock_response = MagicMock()
        mock_response.choices[0].message.content = '{"score": 0.95, "reasoning": "Test reasoning"}'
        mock_openai.return_value.chat.completions.create.return_value = mock_response
        
        judge = CustomLLMJudge()
        
        evaluation = judge.evaluate_correctness(
            question="Test question",
            reference="Test reference",
            answer="Test answer"
        )
        
        # Check required structure
        assert 'score' in evaluation
        assert 'reasoning' in evaluation
        assert 'evaluation_model' in evaluation
        assert 0.0 <= evaluation['score'] <= 1.0
        print("✅ LLM judge evaluation structure test passed")

class TestIntegrationScenarios:
    """Test integration between different Entry Point systems"""
    
    def test_entry_point_progression_compatibility(self):
        """Test that Entry Points work together without conflicts"""
        # Test that multiple systems can be initialized together
        sql_generator = FewShotSQLGenerator()
        ragas_agent = FrankKaneRAGASDemoAgent()
        ambient_agent = ManufacturingAmbientAgent()
        
        # Should not conflict
        assert sql_generator is not None
        assert ragas_agent is not None
        assert ambient_agent is not None
        print("✅ Entry Point progression compatibility test passed")
    
    def test_manufacturing_domain_consistency(self):
        """Test manufacturing domain knowledge consistency across systems"""
        sql_generator = FewShotSQLGenerator()
        ragas_agent = FrankKaneRAGASDemoAgent()
        ambient_agent = ManufacturingAmbientAgent()
        
        # Check for common manufacturing terms
        common_terms = ['oee', 'defect', 'quality', 'manufacturing']
        
        # Check SQL generator examples contain manufacturing terms
        sql_examples_text = ' '.join([ex['explanation'].lower() for ex in sql_generator.manufacturing_examples])
        assert any(term in sql_examples_text for term in common_terms)
        
        # Check RAGAS agent has manufacturing keywords
        ragas_keywords = [kw.lower() for kw in ragas_agent.manufacturing_keywords]
        assert any(term in ragas_keywords for term in common_terms)
        
        # Check ambient agent has manufacturing thresholds
        assert 'defect_rate' in ambient_agent.thresholds
        assert 'oee_minimum' in ambient_agent.thresholds
        
        print("✅ Manufacturing domain consistency test passed")

class TestErrorHandling:
    """Test error handling and resilience"""
    
    def test_missing_api_keys_graceful_handling(self):
        """Test systems handle missing API keys gracefully"""
        # Temporarily remove API keys
        original_openai_key = os.environ.get('OPENAI_API_KEY')
        if 'OPENAI_API_KEY' in os.environ:
            del os.environ['OPENAI_API_KEY']
        
        try:
            # RAGAS demo should work without API keys
            agent = FrankKaneRAGASDemoAgent()
            assert agent is not None
            
            # LLM judge should handle missing key gracefully
            judge = CustomLLMJudge()
            evaluation = judge.evaluate_correctness("test", "test", "test")
            assert 'score' in evaluation  # Should return error structure
            
        finally:
            # Restore API key if it existed
            if original_openai_key:
                os.environ['OPENAI_API_KEY'] = original_openai_key
        
        print("✅ Missing API keys graceful handling test passed")
    
    def test_invalid_input_handling(self):
        """Test systems handle invalid inputs gracefully"""
        sql_generator = FewShotSQLGenerator()
        
        # Test with empty/invalid inputs
        metrics = sql_generator.calculate_advanced_rag_metrics("", {})
        assert isinstance(metrics, dict)  # Should return some structure
        
        print("✅ Invalid input handling test passed")

def run_comprehensive_tests():
    """Run all tests with detailed reporting"""
    print("🧪 Running LangChain Academy-style Entry Point Tests")
    print("=" * 60)
    
    test_classes = [
        TestFrankKaneRAGSystems,
        TestAmbientAgents,
        TestLangChainAcademyIntegration,
        TestIntegrationScenarios,
        TestErrorHandling
    ]
    
    total_tests = 0
    passed_tests = 0
    
    for test_class in test_classes:
        print(f"\n📋 Running {test_class.__name__}")
        print("-" * 40)
        
        test_instance = test_class()
        test_methods = [method for method in dir(test_instance) if method.startswith('test_')]
        
        for test_method in test_methods:
            total_tests += 1
            try:
                getattr(test_instance, test_method)()
                passed_tests += 1
            except Exception as e:
                print(f"❌ {test_method} failed: {e}")
    
    print(f"\n" + "=" * 60)
    print(f"📊 Test Results: {passed_tests}/{total_tests} passed")
    
    if passed_tests == total_tests:
        print("🎉 All tests passed! Your Entry Point implementations are solid.")
    else:
        print(f"⚠️  {total_tests - passed_tests} tests failed. Review implementation.")
    
    return passed_tests == total_tests

if __name__ == "__main__":
    # Run tests when executed directly
    run_comprehensive_tests()