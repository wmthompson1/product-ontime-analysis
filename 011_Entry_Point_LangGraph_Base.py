#!/usr/bin/env python3
"""
011_Entry_Point_LangGraph_Base.py
LangGraph 101 Base Class Implementation for Manufacturing Intelligence
Following the exact pattern from langchain-ai/agents-from-scratch/langgraph_101.ipynb
"""

import os
from typing import TypedDict, Literal, Dict, Any, List
from dataclasses import dataclass
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain.chat_models import init_chat_model
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.types import Command
import json
import uuid

# Manufacturing Intelligence Tools - Following LangGraph 101 @tool pattern
@tool
def analyze_defect_rate(production_line: str, time_period: str, target_rate: float = 2.0) -> str:
    """Analyze manufacturing defect rates for quality control."""
    # Simulate defect rate analysis
    current_rate = 3.2
    analysis = {
        "production_line": production_line,
        "time_period": time_period,
        "current_defect_rate": f"{current_rate}%",
        "target_defect_rate": f"{target_rate}%",
        "status": "Above Target" if current_rate > target_rate else "Within Target",
        "trend": "increasing",
        "recommendations": [
            "Implement statistical process control",
            "Enhanced material inspection protocols",
            "Equipment calibration review"
        ]
    }
    return json.dumps(analysis, indent=2)

@tool
def calculate_oee(equipment_id: str, availability: float = 0.85, performance: float = 0.92, quality: float = 0.97) -> str:
    """Calculate Overall Equipment Effectiveness (OEE) metrics."""
    # Calculate OEE
    oee = availability * performance * quality
    world_class = 0.85
    
    analysis = {
        "equipment_id": equipment_id,
        "availability": availability,
        "performance": performance,
        "quality": quality,
        "overall_oee": round(oee, 3),
        "world_class_benchmark": world_class,
        "performance_gap": round(world_class - oee, 3),
        "status": "World Class" if oee >= world_class else "Improvement Needed",
        "improvement_areas": []
    }
    
    if availability < 0.90:
        analysis["improvement_areas"].append("Reduce unplanned downtime")
    if performance < 0.95:
        analysis["improvement_areas"].append("Optimize cycle times")
    if quality < 0.99:
        analysis["improvement_areas"].append("Enhance quality controls")
    
    return json.dumps(analysis, indent=2)

@tool  
def assess_supply_chain_risk(supplier_id: str, risk_factors: List[str] = None) -> str:
    """Assess supply chain risks and dependencies."""
    if risk_factors is None:
        risk_factors = ["geographic_concentration", "single_source", "financial_stability"]
    
    risk_assessment = {
        "supplier_id": supplier_id,
        "overall_risk_level": "Medium",
        "risk_factors": risk_factors,
        "critical_components": ["hydraulic_seals", "precision_bearings"],
        "geographic_risks": [
            "Single source suppliers in high-risk regions",
            "Transportation route vulnerabilities"
        ],
        "mitigation_strategies": [
            "Diversify supplier base",
            "Implement supplier monitoring dashboard",
            "Develop contingency sourcing plans"
        ],
        "next_review_date": "2024-03-15"
    }
    
    return json.dumps(risk_assessment, indent=2)

@tool
def monitor_equipment_health(equipment_list: List[str] = None) -> str:
    """Monitor equipment health status and predict maintenance needs."""
    if equipment_list is None:
        equipment_list = ["CNC-001", "PRESS-002", "ROBOT-003"]
    
    health_status = {
        "monitoring_timestamp": "2024-01-15T10:30:00Z",
        "overall_health": "Good",
        "equipment_status": []
    }
    
    # Simulate health data for each equipment
    health_scores = [0.85, 0.60, 0.92]
    risk_levels = ["Low", "Medium", "Low"]
    
    for i, equipment in enumerate(equipment_list):
        status = {
            "equipment_id": equipment,
            "health_score": health_scores[i % len(health_scores)],
            "predicted_failure_risk": risk_levels[i % len(risk_levels)],
            "next_maintenance": f"2024-{2 + i:02d}-15",
            "alert_status": "ATTENTION" if health_scores[i % len(health_scores)] < 0.70 else "NORMAL"
        }
        health_status["equipment_status"].append(status)
    
    return json.dumps(health_status, indent=2)

@tool
def schedule_maintenance(equipment_id: str, maintenance_type: str = "preventive", priority: str = "medium") -> str:
    """Schedule and optimize maintenance activities."""
    schedule = {
        "schedule_id": str(uuid.uuid4())[:8],
        "equipment_id": equipment_id,
        "maintenance_type": maintenance_type,
        "priority": priority,
        "scheduled_date": "2024-02-15",
        "estimated_duration": "4 hours" if maintenance_type == "preventive" else "8 hours",
        "resource_requirements": {
            "technicians_needed": 1 if priority == "low" else 2,
            "spare_parts": ["hydraulic_seals", "bearings"] if maintenance_type == "corrective" else ["filters"],
            "downtime_impact": "Minimal with proper scheduling"
        },
        "pre_maintenance_checklist": [
            "Ensure spare parts availability",
            "Schedule technician assignments",
            "Notify production planning"
        ]
    }
    
    return json.dumps(schedule, indent=2)

# Manufacturing State Schema - Following LangGraph 101 TypedDict pattern
class ManufacturingStateSchema(TypedDict):
    """State schema for manufacturing intelligence workflows"""
    query: str
    analysis_type: str
    tool_results: Dict[str, Any]
    recommendations: List[str]
    final_report: str

# Manufacturing Messages State - Following LangGraph 101 MessagesState pattern  
class ManufacturingMessagesState(MessagesState):
    """Extended MessagesState for manufacturing intelligence"""
    equipment_context: Dict[str, Any]
    production_metrics: Dict[str, Any]

class ManufacturingIntelligenceGraph:
    """LangGraph 101 based Manufacturing Intelligence System"""
    
    def __init__(self, openai_api_key: str = None):
        self.api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        
        # Initialize LLM following LangGraph 101 pattern
        self.llm = init_chat_model("openai:gpt-4", temperature=0)
        
        # Manufacturing tools list
        self.manufacturing_tools = [
            analyze_defect_rate,
            calculate_oee, 
            assess_supply_chain_risk,
            monitor_equipment_health,
            schedule_maintenance
        ]
        
        # Bind tools to model - Following LangGraph 101 pattern
        self.model_with_tools = self.llm.bind_tools(
            self.manufacturing_tools,
            tool_choice="auto",
            parallel_tool_calls=False
        )
        
        # Build workflows
        self.simple_workflow = self._build_simple_workflow()
        self.agent_workflow = self._build_agent_workflow()
    
    def _build_simple_workflow(self) -> StateGraph:
        """Build simple workflow following LangGraph 101 StateGraph pattern"""
        
        def analyze_manufacturing_query(state: ManufacturingStateSchema) -> ManufacturingStateSchema:
            """Analyze manufacturing query and execute appropriate tools"""
            print(f"🔧 Processing: {state['query']}")
            
            # Determine analysis type based on query
            query_lower = state['query'].lower()
            if 'defect' in query_lower or 'quality' in query_lower:
                analysis_type = "quality_control"
                # Execute defect analysis
                result = analyze_defect_rate.invoke({
                    "production_line": "Line-A", 
                    "time_period": "last_week"
                })
            elif 'oee' in query_lower or 'efficiency' in query_lower:
                analysis_type = "production_analytics"
                result = calculate_oee.invoke({"equipment_id": "MAIN-LINE-001"})
            elif 'supply' in query_lower or 'supplier' in query_lower:
                analysis_type = "supply_chain"
                result = assess_supply_chain_risk.invoke({"supplier_id": "SUP-001"})
            elif 'equipment' in query_lower or 'health' in query_lower:
                analysis_type = "equipment_monitoring"
                result = monitor_equipment_health.invoke({})
            elif 'maintenance' in query_lower or 'schedule' in query_lower:
                analysis_type = "maintenance"
                result = schedule_maintenance.invoke({"equipment_id": "MAIN-LINE-001"})
            else:
                analysis_type = "general"
                result = calculate_oee.invoke({"equipment_id": "MAIN-LINE-001"})
            
            return {
                "analysis_type": analysis_type,
                "tool_results": {"primary_analysis": result},
                "recommendations": ["Analysis completed successfully"]
            }
        
        def generate_report(state: ManufacturingStateSchema) -> ManufacturingStateSchema:
            """Generate final manufacturing intelligence report"""
            report = f"""
🏭 Manufacturing Intelligence Report
Analysis Type: {state['analysis_type']}
Query: {state['query']}

Primary Analysis Results:
{state['tool_results']['primary_analysis']}

Recommendations:
{chr(10).join(f"• {rec}" for rec in state['recommendations'])}
            """.strip()
            
            return {"final_report": report}
        
        # Build workflow following LangGraph 101 pattern
        workflow = StateGraph(ManufacturingStateSchema)
        workflow.add_node("analyze_query", analyze_manufacturing_query)
        workflow.add_node("generate_report", generate_report)
        workflow.add_edge(START, "analyze_query")
        workflow.add_edge("analyze_query", "generate_report")
        workflow.add_edge("generate_report", END)
        
        return workflow.compile()
    
    def _build_agent_workflow(self) -> StateGraph:
        """Build agent workflow following LangGraph 101 tool calling loop pattern"""
        
        def call_llm(state: ManufacturingMessagesState) -> ManufacturingMessagesState:
            """Run LLM with manufacturing context"""
            # Add manufacturing context to messages
            system_msg = SystemMessage(content="""
            You are a manufacturing intelligence assistant. You have access to tools for:
            - Quality control analysis (defect rates)
            - Production analytics (OEE calculation)
            - Supply chain risk assessment
            - Equipment health monitoring
            - Maintenance scheduling
            
            Use the appropriate tools to provide comprehensive manufacturing insights.
            """)
            
            messages = [system_msg] + state["messages"]
            output = self.model_with_tools.invoke(messages)
            return {"messages": [output]}
        
        def run_tools(state: ManufacturingMessagesState):
            """Execute manufacturing tools"""
            result_messages = []
            
            for tool_call in state["messages"][-1].tool_calls:
                # Find and execute the tool
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                
                # Execute the appropriate tool
                for tool in self.manufacturing_tools:
                    if tool.name == tool_name:
                        try:
                            observation = tool.invoke(tool_args)
                            result_messages.append(
                                ToolMessage(
                                    content=observation,
                                    tool_call_id=tool_call["id"]
                                )
                            )
                            print(f"✅ Executed {tool_name}")
                        except Exception as e:
                            result_messages.append(
                                ToolMessage(
                                    content=f"Error executing {tool_name}: {str(e)}",
                                    tool_call_id=tool_call["id"]
                                )
                            )
                            print(f"❌ Error in {tool_name}: {str(e)}")
                        break
            
            return {"messages": result_messages}
        
        def should_continue(state: ManufacturingMessagesState) -> Literal["run_tools", "__end__"]:
            """Route to tool handler or end"""
            messages = state["messages"]
            last_message = messages[-1]
            
            if last_message.tool_calls:
                return "run_tools"
            return END
        
        # Build agent workflow following LangGraph 101 pattern
        workflow = StateGraph(ManufacturingMessagesState)
        workflow.add_node("call_llm", call_llm)
        workflow.add_node("run_tools", run_tools)
        workflow.add_edge(START, "call_llm")
        workflow.add_conditional_edges(
            "call_llm",
            should_continue,
            {"run_tools": "run_tools", END: END}
        )
        workflow.add_edge("run_tools", "call_llm")
        
        return workflow.compile()

def demo_langgraph_101_manufacturing():
    """Demonstrate LangGraph 101 patterns with manufacturing intelligence"""
    print("🧪 LangGraph 101 Manufacturing Intelligence Demo")
    print("Following exact patterns from langchain-ai/agents-from-scratch")
    print("=" * 70)
    
    # Initialize the graph system
    mfg_graph = ManufacturingIntelligenceGraph()
    
    print("\n📊 Part 1: Simple Workflow (StateGraph)")
    print("-" * 40)
    
    # Test simple workflow
    simple_queries = [
        "What is our current defect rate?",
        "Calculate OEE for our main production line",
        "Assess supply chain risks"
    ]
    
    for query in simple_queries:
        print(f"\nQuery: {query}")
        result = mfg_graph.simple_workflow.invoke({
            "query": query,
            "analysis_type": "",
            "tool_results": {},
            "recommendations": [],
            "final_report": ""
        })
        
        print("Report:")
        print(result["final_report"])
        print("-" * 30)
    
    print("\n🤖 Part 2: Agent Workflow (Tool Calling Loop)")
    print("-" * 40)
    
    # Test agent workflow
    agent_queries = [
        "I need a comprehensive analysis of our manufacturing performance including OEE and defect rates",
        "Monitor equipment health and schedule maintenance for any issues found",
        "Assess our supply chain risks and provide mitigation strategies"
    ]
    
    for query in agent_queries:
        print(f"\nAgent Query: {query}")
        print("-" * 30)
        
        result = mfg_graph.agent_workflow.invoke({
            "messages": [HumanMessage(content=query)],
            "equipment_context": {},
            "production_metrics": {}
        })
        
        # Print conversation
        for message in result["messages"]:
            if hasattr(message, 'content') and message.content:
                print(f"Assistant: {message.content[:200]}...")
                break
        
        print("-" * 30)
    
    print(f"\n" + "=" * 70)
    print("🎯 LangGraph 101 patterns successfully implemented!")
    print("📚 Ready for advanced manufacturing intelligence workflows")
    
    return True

if __name__ == "__main__":
    # Run the LangGraph 101 demo
    demo_langgraph_101_manufacturing()