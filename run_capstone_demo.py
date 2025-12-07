#!/usr/bin/env python3
"""
Berkeley Haas AI Strategy Capstone Demo Runner
Easy launcher for your capstone presentation
"""

import subprocess
import sys

def main():
    print("🎓 Berkeley Haas AI Strategy Capstone")
    print("   LangChain Semantic Layer for Business Intelligence")
    print("=" * 60)
    print()
    print("Choose your demo version:")
    print("1. Reliable Demo (recommended for presentation)")
    print("2. Full LangChain Integration (with OpenAI)")
    print("3. ROI Analysis Only")
    print()
    
    choice = input("Select option (1-3): ").strip()
    
    if choice == '1':
        print("\n🚀 Starting reliable capstone demo...")
        subprocess.run([sys.executable, "capstone_demo_simple.py"])
    elif choice == '2':
        print("\n🤖 Starting full LangChain demo...")
        subprocess.run([sys.executable, "capstone_demo.py"])
    elif choice == '3':
        print("\n📊 Showing ROI analysis...")
        subprocess.run([sys.executable, "capstone_demo_simple.py", "--roi"])
    else:
        print("Invalid choice. Please run again and select 1-3.")

if __name__ == "__main__":
    main()