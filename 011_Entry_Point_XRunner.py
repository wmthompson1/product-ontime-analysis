#!/usr/bin/env python3
"""
011_Entry_Point_XRunner.py
Runner for LangGraph Base Demo - Development vs Test Management
"""

import subprocess
import sys
import os

def run_langgraph_base_demo():
    """Execute the LangGraph Base demo"""
    print("🚀 Starting LangGraph Base Demo via Runner")
    print("=" * 60)
    
    try:
        # Run the base LangGraph implementation
        result = subprocess.run([
            sys.executable, 
            "011_Entry_Point_LangGraph_Base.py"
        ], capture_output=False, text=True)
        
        if result.returncode == 0:
            print("\n" + "=" * 60)
            print("✅ LangGraph Base Demo completed successfully!")
        else:
            print(f"\n❌ Demo failed with return code: {result.returncode}")
            
    except Exception as e:
        print(f"❌ Error running demo: {str(e)}")

if __name__ == "__main__":
    run_langgraph_base_demo()