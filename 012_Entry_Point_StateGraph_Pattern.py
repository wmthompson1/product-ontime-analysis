#!/usr/bin/env python3
"""
012_Entry_Point_StateGraph_Pattern.py
LangGraph 101 StateGraph Pattern Implementation for Manufacturing Intelligence
Demonstrates core StateGraph concepts without requiring full LangGraph package
Following the exact pattern from langchain-ai/agents-from-scratch/langgraph_101.ipynb
"""

import os
from typing import TypedDict, Literal, Dict, Any, List, Callable
from dataclasses import dataclass
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage, BaseMessage
from langchain_openai import ChatOpenAI
import json
import uuid

# LangGraph 101 Pattern: @tool decorator for manufacturing tools
@tool
def analyze_defect_rate(production_line: str = "Line-A", time_period: str = "last_week", target_rate: float = 2.0) -> str:
    """Analyze manufacturing defect rates for quality control."""
    current_rate = 3.2
    analysis = {
        "production_line": production_line,
        "time_period": time_period,
        "current_defect_rate": f"{current_rate}%",
        "target_defect_rate": f"{target_rate}%",
        "status": "Above Target" if current_rate > target_rate else "Within Target",
        "recommendations": ["Implement SPC", "Enhanced inspection", "Equipment calibration"]
    }
    return json.dumps(analysis, indent=2)

@tool
def calculate_oee(equipment_id: str = "MAIN-LINE-001", availability: float = 0.85, performance: float = 0.92, quality: float = 0.97) -> str:
    """Calculate Overall Equipment Effectiveness (OEE) metrics."""
    oee = availability * performance * quality
    analysis = {
        "equipment_id": equipment_id,
        "availability": availability,
        "performance": performance, 
        "quality": quality,
        "overall_oee": round(oee, 3),
        "world_class_benchmark": 0.85,
        "status": "World Class" if oee >= 0.85 else "Improvement Needed"
    }
    return json.dumps(analysis, indent=2)

@tool
def assess_supply_chain_risk(supplier_id: str = "SUP-001") -> str:
    """Assess supply chain risks and dependencies."""
    risk_assessment = {
        "supplier_id": supplier_id,
        "overall_risk_level": "Medium",
        "critical_components": ["hydraulic_seals", "precision_bearings"],
        "mitigation_strategies": ["Diversify supplier base", "Implement monitoring", "Develop contingency plans"]
    }
    return json.dumps(risk_assessment, indent=2)

# LangGraph 101 Pattern: State Schema using TypedDict
class ManufacturingState(TypedDict):
    """State schema following LangGraph 101 pattern"""
    request: str
    analysis_type: str
    tool_results: Dict[str, Any]
    final_report: str

class MessagesState(TypedDict):
    """Messages state for agent pattern"""
    messages: List[BaseMessage]

# Simplified StateGraph Implementation following LangGraph 101 concepts
class SimpleStateGraph:
    """Simplified StateGraph implementation demonstrating LangGraph 101 concepts"""
    
    def __init__(self, state_schema: type):
        self.state_schema = state_schema
        self.nodes = {}
        self.edges = {}
        self.conditional_edges = {}
        self.start_node = None
        self.end_nodes = set()
    
    def add_node(self, name: str, func: Callable):
        """Add a node (function) to the graph"""
        self.nodes[name] = func
    
    def add_edge(self, from_node: str, to_node: str):
        """Add a direct edge between nodes"""
        if from_node == "START":
            self.start_node = to_node
        elif to_node == "END":
            self.end_nodes.add(from_node)
        else:
            self.edges[from_node] = to_node
    
    def add_conditional_edge(self, from_node: str, condition_func: Callable, mapping: Dict[str, str]):
        """Add a conditional edge"""
        self.conditional_edges[from_node] = {
            "condition": condition_func,
            "mapping": mapping
        }
    
    def compile(self):
        """Compile the graph into an executable workflow"""
        return CompiledGraph(self)

class CompiledGraph:
    """Compiled graph that can be invoked"""
    
    def __init__(self, graph: SimpleStateGraph):
        self.graph = graph
    
    def invoke(self, initial_state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the graph with initial state"""
        state = initial_state.copy()
        current_node = self.graph.start_node
        
        print(f"🚀 Starting workflow at: {current_node}")
        
        while current_node and current_node not in self.graph.end_nodes:
            print(f"🔧 Executing node: {current_node}")
            
            # Execute current node
            if current_node in self.graph.nodes:
                node_func = self.graph.nodes[current_node]
                result = node_func(state)
                
                # Update state with node result
                if isinstance(result, dict):
                    state.update(result)
            
            # Determine next node
            if current_node in self.graph.conditional_edges:
                # Use conditional edge
                condition_info = self.graph.conditional_edges[current_node]
                condition_result = condition_info["condition"](state)
                current_node = condition_info["mapping"].get(condition_result, "END")
            elif current_node in self.graph.edges:
                # Use direct edge
                current_node = self.graph.edges[current_node]
            else:
                # No more edges, end execution
                break
        
        print(f"✅ Workflow completed")
        return state

class ManufacturingIntelligenceWorkflow:
    """Manufacturing Intelligence using LangGraph 101 patterns"""
    
    def __init__(self, openai_api_key: str = None):
        self.api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        
        # Initialize LLM following LangGraph 101 pattern
        self.llm = ChatOpenAI(
            model="gpt-4",
            api_key=self.api_key,
            temperature=0
        )
        
        # Manufacturing tools
        self.tools = [analyze_defect_rate, calculate_oee, assess_supply_chain_risk]
        
        # Bind tools to model
        self.model_with_tools = self.llm.bind_tools(
            self.tools,
            tool_choice="auto", 
            parallel_tool_calls=False
        )
        
        # Build workflows
        self.simple_workflow = self._build_simple_workflow()
        self.agent_workflow = self._build_agent_workflow()
    
    def _build_simple_workflow(self) -> CompiledGraph:
        """Build simple workflow using StateGraph pattern"""
        
        def analyze_manufacturing_request(state: ManufacturingState) -> ManufacturingState:
            """Node: Analyze manufacturing request and determine tools needed"""
            request = state["request"]
            print(f"📋 Analyzing request: {request}")
            
            # Categorize request
            request_lower = request.lower()
            if any(term in request_lower for term in ["defect", "quality"]):
                analysis_type = "quality_control"
                result = analyze_defect_rate.invoke({})
            elif any(term in request_lower for term in ["oee", "efficiency"]):
                analysis_type = "production_analytics"
                result = calculate_oee.invoke({})
            elif any(term in request_lower for term in ["supply", "supplier", "risk"]):
                analysis_type = "supply_chain"
                result = assess_supply_chain_risk.invoke({})
            else:
                analysis_type = "general"
                result = calculate_oee.invoke({})
            
            return {
                "analysis_type": analysis_type,
                "tool_results": {"primary": result}
            }
        
        def generate_manufacturing_report(state: ManufacturingState) -> ManufacturingState:
            """Node: Generate final manufacturing intelligence report"""
            report = f"""
🏭 Manufacturing Intelligence Report
==================================
Request: {state['request']}
Analysis Type: {state['analysis_type']}

Primary Analysis:
{state['tool_results']['primary']}

Status: Analysis completed successfully
            """.strip()
            
            return {"final_report": report}
        
        # Build workflow following LangGraph 101 StateGraph pattern
        workflow = SimpleStateGraph(ManufacturingState)
        workflow.add_node("analyze_request", analyze_manufacturing_request)
        workflow.add_node("generate_report", generate_manufacturing_report)
        workflow.add_edge("START", "analyze_request")
        workflow.add_edge("analyze_request", "generate_report")
        workflow.add_edge("generate_report", "END")
        
        return workflow.compile()
    
    def _build_agent_workflow(self) -> CompiledGraph:
        """Build agent workflow using tool calling loop pattern"""
        
        def call_manufacturing_llm(state: MessagesState) -> MessagesState:
            """Node: Call LLM with manufacturing tools"""
            print(f"🤖 Calling LLM with {len(self.tools)} manufacturing tools")
            
            # Add system message for manufacturing context
            system_msg = SystemMessage(content="""
            You are a manufacturing intelligence assistant with access to:
            - Defect rate analysis for quality control
            - OEE calculation for production analytics  
            - Supply chain risk assessment
            
            Use these tools to provide comprehensive manufacturing insights.
            """)
            
            messages = [system_msg] + state["messages"]
            output = self.model_with_tools.invoke(messages)
            
            return {"messages": state["messages"] + [output]}
        
        def execute_manufacturing_tools(state: MessagesState) -> MessagesState:
            """Node: Execute manufacturing tools"""
            last_message = state["messages"][-1]
            result_messages = []
            
            for tool_call in last_message.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                
                print(f"🔧 Executing tool: {tool_name}")
                
                # Find and execute the tool
                for tool in self.tools:
                    if tool.name == tool_name:
                        try:
                            observation = tool.invoke(tool_args)
                            result_messages.append(
                                ToolMessage(
                                    content=observation,
                                    tool_call_id=tool_call["id"]
                                )
                            )
                            print(f"✅ Tool {tool_name} executed successfully")
                        except Exception as e:
                            result_messages.append(
                                ToolMessage(
                                    content=f"Error: {str(e)}",
                                    tool_call_id=tool_call["id"]
                                )
                            )
                            print(f"❌ Tool {tool_name} failed: {str(e)}")
                        break
            
            return {"messages": state["messages"] + result_messages}
        
        def should_continue_manufacturing(state: MessagesState) -> str:
            """Conditional edge: Determine if we should continue or end"""
            last_message = state["messages"][-1]
            
            if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
                return "continue"
            return "end"
        
        # Build agent workflow
        workflow = SimpleStateGraph(MessagesState)
        workflow.add_node("call_llm", call_manufacturing_llm)
        workflow.add_node("execute_tools", execute_manufacturing_tools)
        workflow.add_edge("START", "call_llm")
        workflow.add_conditional_edge(
            "call_llm",
            should_continue_manufacturing,
            {"continue": "execute_tools", "end": "END"}
        )
        workflow.add_edge("execute_tools", "call_llm")
        
        return workflow.compile()

def demo_langgraph_101_patterns():
    """Demonstrate LangGraph 101 patterns for manufacturing intelligence"""
    print("🧪 LangGraph 101 Manufacturing Intelligence Demo")
    print("Demonstrating core StateGraph patterns from langchain-ai/agents-from-scratch")
    print("=" * 75)
    
    # Initialize manufacturing workflow system
    mfg_workflow = ManufacturingIntelligenceWorkflow()
    
    print("\n📊 Part 1: Simple StateGraph Workflow")
    print("-" * 45)
    
    # Test simple workflow with different manufacturing requests
    simple_requests = [
        "Analyze our current defect rates for quality improvement",
        "Calculate OEE for our main production equipment",
        "Assess supply chain risks for critical suppliers"
    ]
    
    for request in simple_requests:
        print(f"\nRequest: {request}")
        print("-" * 30)
        
        result = mfg_workflow.simple_workflow.invoke({
            "request": request,
            "analysis_type": "",
            "tool_results": {},
            "final_report": ""
        })
        
        print("Result:")
        print(result["final_report"])
        print("-" * 30)
    
    print(f"\n🤖 Part 2: Agent Workflow (Tool Calling Loop)")
    print("-" * 45)
    
    # Test agent workflow
    agent_requests = [
        "I need a comprehensive OEE analysis for equipment optimization",
        "Provide defect rate analysis with improvement recommendations",
        "Assess our supply chain vulnerabilities and mitigation strategies"
    ]
    
    for request in agent_requests:
        print(f"\nAgent Request: {request}")
        print("-" * 30)
        
        try:
            result = mfg_workflow.agent_workflow.invoke({
                "messages": [HumanMessage(content=request)]
            })
            
            # Show final assistant response
            for message in reversed(result["messages"]):
                if hasattr(message, 'content') and message.content and not hasattr(message, 'tool_calls'):
                    print(f"Assistant Response: {message.content[:200]}...")
                    break
            
        except Exception as e:
            print(f"Note: Agent workflow requires OpenAI API key - {str(e)}")
        
        print("-" * 30)
    
    print(f"\n" + "=" * 75)
    print("🎯 LangGraph 101 patterns successfully demonstrated!")
    print("📚 Core concepts: StateGraph, nodes, edges, conditional routing")
    print("🏭 Manufacturing tools: defect analysis, OEE calculation, risk assessment")
    print("🔧 Ready for integration with your Berkeley Haas capstone project")
    
    return True

if __name__ == "__main__":
    # Run the LangGraph 101 demonstration
    demo_langgraph_101_patterns()