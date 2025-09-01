#!/usr/bin/env python3
"""
010_Entry_Point_Custom_Tools.py
Deconstructed LangChain Academy Email Tools for Manufacturing Intelligence
Creating custom tools following LangChain Academy patterns
"""

import os
from typing import Literal, Dict, Any, List, Optional
from dataclasses import dataclass
from langchain_core.tools import Tool
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langsmith import Client as LangSmithClient
import json
import uuid

# Manufacturing Intelligence Tool Categories
class ManufacturingToolCategory:
    QUALITY_CONTROL = "quality_control"
    SUPPLY_CHAIN = "supply_chain" 
    EQUIPMENT_MONITORING = "equipment_monitoring"
    PRODUCTION_ANALYTICS = "production_analytics"
    MAINTENANCE = "maintenance"

@dataclass
class ManufacturingState:
    """State management for manufacturing intelligence tools"""
    current_query: str = ""
    tool_category: str = ""
    manufacturing_context: Dict[str, Any] = None
    analysis_results: Dict[str, Any] = None
    recommendations: List[str] = None
    
    def __post_init__(self):
        if self.manufacturing_context is None:
            self.manufacturing_context = {}
        if self.analysis_results is None:
            self.analysis_results = {}
        if self.recommendations is None:
            self.recommendations = []

class ManufacturingToolsRegistry:
    """Registry for manufacturing intelligence tools following LangChain Academy pattern"""
    
    def __init__(self):
        self.tools = {}
        self.tool_prompts = {}
        self._register_default_tools()
    
    def _register_default_tools(self):
        """Register default manufacturing tools"""
        
        # Quality Control Tools
        self.register_tool(
            "defect_rate_analyzer",
            self._defect_rate_analyzer,
            ManufacturingToolCategory.QUALITY_CONTROL,
            "Analyze manufacturing defect rates and quality trends"
        )
        
        self.register_tool(
            "oee_calculator", 
            self._oee_calculator,
            ManufacturingToolCategory.PRODUCTION_ANALYTICS,
            "Calculate Overall Equipment Effectiveness (OEE) metrics"
        )
        
        # Supply Chain Tools
        self.register_tool(
            "supply_chain_risk_assessor",
            self._supply_chain_risk_assessor,
            ManufacturingToolCategory.SUPPLY_CHAIN,
            "Assess supply chain risks and dependencies"
        )
        
        # Equipment Monitoring Tools
        self.register_tool(
            "equipment_health_monitor",
            self._equipment_health_monitor,
            ManufacturingToolCategory.EQUIPMENT_MONITORING,
            "Monitor equipment health and predict maintenance needs"
        )
        
        # Maintenance Tools
        self.register_tool(
            "maintenance_scheduler",
            self._maintenance_scheduler,
            ManufacturingToolCategory.MAINTENANCE,
            "Schedule and optimize maintenance activities"
        )
    
    def register_tool(self, name: str, func, category: str, description: str):
        """Register a new manufacturing tool"""
        self.tools[name] = {
            "function": func,
            "category": category,
            "description": description,
            "tool": Tool(
                name=name,
                description=description,
                func=func
            )
        }
    
    def get_tools_by_category(self, category: str) -> List[Tool]:
        """Get tools by manufacturing category"""
        return [
            tool_info["tool"] 
            for tool_info in self.tools.values() 
            if tool_info["category"] == category
        ]
    
    def get_all_tools(self) -> List[Tool]:
        """Get all registered tools"""
        return [tool_info["tool"] for tool_info in self.tools.values()]
    
    def get_tools_by_name(self, tool_names: List[str]) -> List[Tool]:
        """Get specific tools by name"""
        return [
            self.tools[name]["tool"] 
            for name in tool_names 
            if name in self.tools
        ]
    
    # Tool Implementation Methods
    def _defect_rate_analyzer(self, input_data: str) -> str:
        """Analyze defect rates in manufacturing processes"""
        try:
            # Handle input data properly
            query = input_data if isinstance(input_data, str) else str(input_data)
            
            # Simulate defect rate analysis based on query
            analysis = {
                "current_defect_rate": "2.3%",
                "target_defect_rate": "1.5%", 
                "trend": "decreasing",
                "main_causes": [
                    "Material inconsistency",
                    "Equipment calibration drift",
                    "Process variation"
                ],
                "recommendations": [
                    "Implement statistical process control",
                    "Enhanced material inspection",
                    "Equipment calibration schedule review"
                ]
            }
            
            return json.dumps(analysis, indent=2)
            
        except Exception as e:
            return f"Error analyzing defect rates: {str(e)}"
    
    def _oee_calculator(self, input_data: str) -> str:
        """Calculate Overall Equipment Effectiveness"""
        try:
            # Handle input data properly
            query = input_data if isinstance(input_data, str) else str(input_data)
            
            # Simulate OEE calculation
            oee_metrics = {
                "availability": 0.85,
                "performance": 0.92,
                "quality": 0.97,
                "overall_oee": 0.76,
                "world_class_benchmark": 0.85,
                "improvement_opportunities": [
                    "Reduce unplanned downtime (availability)",
                    "Optimize cycle times (performance)",
                    "Implement quality controls (quality)"
                ]
            }
            
            return json.dumps(oee_metrics, indent=2)
            
        except Exception as e:
            return f"Error calculating OEE: {str(e)}"
    
    def _supply_chain_risk_assessor(self, input_data: str) -> str:
        """Assess supply chain risks"""
        try:
            # Handle input data properly
            query = input_data if isinstance(input_data, str) else str(input_data)
            
            risk_assessment = {
                "overall_risk_level": "Medium",
                "critical_suppliers": 3,
                "geographic_risks": [
                    "Single source suppliers in high-risk regions",
                    "Transportation route vulnerabilities"
                ],
                "mitigation_strategies": [
                    "Diversify supplier base",
                    "Implement supplier monitoring",
                    "Develop contingency plans"
                ]
            }
            
            return json.dumps(risk_assessment, indent=2)
            
        except Exception as e:
            return f"Error assessing supply chain risk: {str(e)}"
    
    def _equipment_health_monitor(self, input_data: str) -> str:
        """Monitor equipment health status"""
        try:
            # Handle input data properly
            query = input_data if isinstance(input_data, str) else str(input_data)
            
            health_status = {
                "overall_health": "Good",
                "critical_equipment": [
                    {
                        "equipment_id": "CNC-001",
                        "health_score": 0.75,
                        "predicted_failure_risk": "Low",
                        "next_maintenance": "2024-02-15"
                    },
                    {
                        "equipment_id": "PRESS-002", 
                        "health_score": 0.60,
                        "predicted_failure_risk": "Medium",
                        "next_maintenance": "2024-01-20"
                    }
                ],
                "maintenance_alerts": [
                    "PRESS-002 requires attention within 2 weeks"
                ]
            }
            
            return json.dumps(health_status, indent=2)
            
        except Exception as e:
            return f"Error monitoring equipment health: {str(e)}"
    
    def _maintenance_scheduler(self, input_data: str) -> str:
        """Schedule maintenance activities"""
        try:
            # Handle input data properly
            query = input_data if isinstance(input_data, str) else str(input_data)
            
            schedule = {
                "optimized_schedule": [
                    {
                        "equipment": "CNC-001",
                        "maintenance_type": "Preventive",
                        "scheduled_date": "2024-02-15",
                        "estimated_duration": "4 hours",
                        "priority": "Medium"
                    },
                    {
                        "equipment": "PRESS-002",
                        "maintenance_type": "Corrective", 
                        "scheduled_date": "2024-01-20",
                        "estimated_duration": "8 hours",
                        "priority": "High"
                    }
                ],
                "resource_requirements": {
                    "technicians_needed": 2,
                    "spare_parts": ["Hydraulic seals", "Bearings"],
                    "downtime_impact": "Minimal with proper scheduling"
                }
            }
            
            return json.dumps(schedule, indent=2)
            
        except Exception as e:
            return f"Error scheduling maintenance: {str(e)}"

class ManufacturingPromptTemplates:
    """Prompt templates for manufacturing intelligence tools"""
    
    TOOL_SELECTION_PROMPT = """
    You are a manufacturing intelligence assistant. Based on the user's query, select the most appropriate tools.
    
    Available tool categories:
    - Quality Control: defect analysis, quality metrics
    - Supply Chain: risk assessment, supplier management  
    - Equipment Monitoring: health status, predictive maintenance
    - Production Analytics: OEE calculation, performance metrics
    - Maintenance: scheduling, optimization
    
    User Query: {query}
    
    Recommend the best tools to address this query.
    """
    
    MANUFACTURING_ANALYSIS_PROMPT = """
    You are an expert manufacturing engineer analyzing production data.
    
    Context: {manufacturing_context}
    Tool Results: {tool_results}
    
    Provide actionable insights and recommendations for:
    1. Immediate actions needed
    2. Long-term improvements
    3. Risk mitigation strategies
    4. Performance optimization opportunities
    
    Focus on practical, implementable solutions.
    """

class ManufacturingIntelligenceAgent:
    """Main agent orchestrating manufacturing intelligence tools"""
    
    def __init__(self, openai_api_key: str = None, langsmith_project: str = None):
        self.api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.langsmith_project = langsmith_project or "Manufacturing_Intelligence"
        
        # Initialize components
        self.llm = ChatOpenAI(
            model="gpt-4",
            api_key=self.api_key,
            temperature=0.1
        )
        
        self.tools_registry = ManufacturingToolsRegistry()
        self.prompts = ManufacturingPromptTemplates()
        
        # LangSmith integration
        self.langsmith_client = LangSmithClient() if os.getenv("LANGSMITH_API_KEY") else None
    
    def analyze_manufacturing_query(self, query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Main method to analyze manufacturing queries using appropriate tools"""
        
        print(f"🏭 Manufacturing Intelligence Analysis")
        print(f"Query: {query}")
        print("-" * 50)
        
        # Initialize state
        state = ManufacturingState(
            current_query=query,
            manufacturing_context=context or {}
        )
        
        # Step 1: Determine tool category
        category = self._categorize_query(query)
        state.tool_category = category
        
        print(f"📊 Detected Category: {category}")
        
        # Step 2: Get relevant tools
        relevant_tools = self.tools_registry.get_tools_by_category(category)
        
        # Step 3: Execute tools
        tool_results = {}
        for tool in relevant_tools:
            try:
                result = tool.func(query)
                tool_results[tool.name] = result
                print(f"✅ {tool.name}: Completed")
            except Exception as e:
                tool_results[tool.name] = f"Error: {str(e)}"
                print(f"❌ {tool.name}: Failed - {str(e)}")
        
        state.analysis_results = tool_results
        
        # Step 4: Generate comprehensive analysis
        analysis = self._generate_comprehensive_analysis(state)
        
        return {
            "query": query,
            "category": category,
            "tool_results": tool_results,
            "comprehensive_analysis": analysis,
            "recommendations": state.recommendations
        }
    
    def _categorize_query(self, query: str) -> str:
        """Categorize the manufacturing query"""
        query_lower = query.lower()
        
        if any(term in query_lower for term in ["defect", "quality", "reject", "scrap"]):
            return ManufacturingToolCategory.QUALITY_CONTROL
        elif any(term in query_lower for term in ["oee", "efficiency", "performance", "productivity"]):
            return ManufacturingToolCategory.PRODUCTION_ANALYTICS
        elif any(term in query_lower for term in ["supply", "supplier", "vendor", "procurement"]):
            return ManufacturingToolCategory.SUPPLY_CHAIN
        elif any(term in query_lower for term in ["equipment", "machine", "breakdown", "failure"]):
            return ManufacturingToolCategory.EQUIPMENT_MONITORING
        elif any(term in query_lower for term in ["maintenance", "repair", "service", "schedule"]):
            return ManufacturingToolCategory.MAINTENANCE
        else:
            return ManufacturingToolCategory.PRODUCTION_ANALYTICS  # Default
    
    def _generate_comprehensive_analysis(self, state: ManufacturingState) -> str:
        """Generate comprehensive analysis using LLM"""
        try:
            prompt = ChatPromptTemplate.from_template(self.prompts.MANUFACTURING_ANALYSIS_PROMPT)
            
            response = self.llm.invoke([
                SystemMessage(content="You are an expert manufacturing intelligence analyst."),
                HumanMessage(content=prompt.format(
                    manufacturing_context=json.dumps(state.manufacturing_context),
                    tool_results=json.dumps(state.analysis_results, indent=2)
                ))
            ])
            
            return response.content
            
        except Exception as e:
            return f"Error generating analysis: {str(e)}"

def demo_custom_manufacturing_tools():
    """Demonstrate the custom manufacturing tools system"""
    print("🔧 LangChain Academy Custom Tools Demo")
    print("Manufacturing Intelligence Tool Deconstruction")
    print("=" * 60)
    
    # Initialize agent
    agent = ManufacturingIntelligenceAgent()
    
    # Test queries for different categories
    test_queries = [
        "What is our current defect rate and how can we improve quality?",
        "Calculate the OEE for our main production line",
        "Assess supply chain risks for our key suppliers",
        "Monitor the health status of our critical equipment",
        "Schedule maintenance for our manufacturing equipment"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n🧪 Test {i}: {query}")
        print("-" * 40)
        
        try:
            result = agent.analyze_manufacturing_query(query)
            
            print(f"Category: {result['category']}")
            print(f"Tools Used: {list(result['tool_results'].keys())}")
            print(f"Analysis: {result['comprehensive_analysis'][:200]}...")
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
    
    print(f"\n" + "=" * 60)
    print("🎯 Custom manufacturing tools successfully deconstructed!")
    print("📚 Ready for LangChain Academy integration patterns")
    
    return True

if __name__ == "__main__":
    # Run the demo
    demo_custom_manufacturing_tools()