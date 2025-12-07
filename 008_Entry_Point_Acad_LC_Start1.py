from langsmith import Client
from openai import OpenAI
import os
import json
from typing import Dict, Any, List

# Custom LLM-as-Judge implementation (replaces openevals)
class CustomLLMJudge:
    """Custom LLM-as-Judge evaluator for LangChain Academy patterns"""
    
    def __init__(self, model_name: str = "gpt-4"):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = model_name
        
        # Correctness evaluation prompt (similar to openevals CORRECTNESS_PROMPT)
        self.correctness_prompt = """
        You are an expert evaluator assessing the correctness of AI responses.
        
        Given:
        - Question: {question}
        - Reference Answer: {reference}
        - Actual Answer: {answer}
        
        Evaluate how correct the actual answer is compared to the reference answer.
        Consider:
        - Factual accuracy
        - Completeness
        - Relevance to the question
        
        Provide your evaluation as:
        1. Score (0.0 to 1.0): Numerical correctness score
        2. Reasoning: Brief explanation of your evaluation
        
        Response format:
        {{
            "score": 0.85,
            "reasoning": "The answer is factually correct and addresses the question directly..."
        }}
        """
    
    def evaluate_correctness(self, question: str, reference: str, answer: str) -> Dict[str, Any]:
        """Evaluate answer correctness using LLM-as-judge"""
        
        prompt = self.correctness_prompt.format(
            question=question,
            reference=reference,
            answer=answer
        )
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            
            # Parse JSON response
            result = json.loads(response.choices[0].message.content)
            return {
                "score": result.get("score", 0.0),
                "reasoning": result.get("reasoning", "No reasoning provided"),
                "evaluation_model": self.model
            }
            
        except Exception as e:
            return {
                "score": 0.0,
                "reasoning": f"Evaluation failed: {str(e)}",
                "evaluation_model": self.model
            }

# Initialize LangSmith client and custom evaluator
client = Client()
llm_judge = CustomLLMJudge()

# Create or get existing dataset
import uuid
dataset_name = f"Manufacturing_QA_Dataset_{str(uuid.uuid4())[:8]}"

try:
    # Try to create a new dataset with unique name
    dataset = client.create_dataset(
        dataset_name=dataset_name, 
        description="Manufacturing Q&A dataset for LangChain Academy evaluation."
    )
    print(f"📊 Created new dataset: {dataset_name}")
    
    # Create examples in the dataset
    examples = [
        {
            "inputs": {"question": "Which country is Mount Kilimanjaro located in?"},
            "outputs": {"answer": "Mount Kilimanjaro is located in Tanzania."},
        },
        {
            "inputs": {"question": "What is Earth's lowest point?"},
            "outputs": {"answer": "Earth's lowest point is The Dead Sea."},
        },
        {
            "inputs": {"question": "What is OEE in manufacturing?"},
            "outputs": {"answer": "Overall Equipment Effectiveness (OEE) is calculated as Availability × Performance × Quality."},
        },
        {
            "inputs": {"question": "What is the typical manufacturing defect rate threshold?"},
            "outputs": {"answer": "Typical manufacturing defect rates should be below 2% for quality standards."},
        },
    ]
    
    # Add the examples to the dataset
    client.create_examples(dataset_id=dataset.id, examples=examples)
    print(f"✅ Added {len(examples)} examples to dataset")
    
except Exception as e:
    print(f"⚠️ Dataset creation issue: {e}")
    print("📊 Continuing with evaluation demo without LangSmith dataset...")
    dataset = None

# Define evaluation function using custom LLM judge
def evaluate_correctness(run, example):
    """Custom evaluation function for LangSmith"""
    
    # Extract data from run and example
    question = example.inputs["question"]
    reference_answer = example.outputs["answer"]
    actual_answer = run.outputs.get("answer", "No answer provided")
    
    # Use custom LLM judge for evaluation
    evaluation = llm_judge.evaluate_correctness(question, reference_answer, actual_answer)
    
    return {
        "key": "correctness",
        "score": evaluation["score"],
        "comment": evaluation["reasoning"]
    }

# Simple function to simulate your app (replace with your actual app logic)
def simple_qa_app(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """Simple Q&A app for demonstration"""
    question = inputs.get("question", "")
    
    # Simulate some simple responses for testing
    if "kilimanjaro" in question.lower():
        return {"answer": "Mount Kilimanjaro is located in Tanzania."}
    elif "lowest point" in question.lower():
        return {"answer": "The lowest point on Earth is the Dead Sea."}
    else:
        return {"answer": "I don't know the answer to that question."}

# Manufacturing-focused evaluation example
def manufacturing_qa_app(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """Manufacturing intelligence Q&A app"""
    question = inputs.get("question", "")
    
    # Simple manufacturing responses for testing
    if "oee" in question.lower():
        return {"answer": "Overall Equipment Effectiveness (OEE) is calculated as Availability × Performance × Quality."}
    elif "defect" in question.lower():
        return {"answer": "Typical manufacturing defect rates should be below 2% for quality standards."}
    elif "supply chain" in question.lower():
        return {"answer": "Supply chain optimization focuses on reducing lead times and improving delivery reliability."}
    else:
        return {"answer": "Please provide a manufacturing-related question for better assistance."}

def main():
    """Main function to demonstrate LangChain Academy evaluation patterns"""
    print("🧪 LangChain Academy Evaluation Demo")
    print("   Custom LLM-as-Judge Implementation")
    print("=" * 50)
    
    # Check if dataset was created successfully
    if dataset:
        print(f"📊 LangSmith dataset ready: {dataset.name}")
    else:
        print("📊 Running in standalone evaluation mode")
    
    # Test the evaluation system
    print("\n📊 Testing Custom LLM Judge...")
    
    # Test evaluation
    test_question = "Which country is Mount Kilimanjaro located in?"
    test_reference = "Mount Kilimanjaro is located in Tanzania."
    test_answer = "Tanzania is the country where Mount Kilimanjaro is located."
    
    evaluation = llm_judge.evaluate_correctness(test_question, test_reference, test_answer)
    
    print(f"Question: {test_question}")
    print(f"Reference: {test_reference}")
    print(f"Answer: {test_answer}")
    print(f"Score: {evaluation['score']}")
    print(f"Reasoning: {evaluation['reasoning']}")
    
    # Test simple app
    print(f"\n🔧 Testing Simple Q&A App...")
    test_inputs = {"question": "Which country is Mount Kilimanjaro located in?"}
    app_output = simple_qa_app(test_inputs)
    print(f"App Output: {app_output}")
    
    # Test manufacturing app
    print(f"\n🏭 Testing Manufacturing Q&A App...")
    mfg_inputs = {"question": "What is OEE in manufacturing?"}
    mfg_output = manufacturing_qa_app(mfg_inputs)
    print(f"Manufacturing App Output: {mfg_output}")
    
    print(f"\n✅ LangChain Academy evaluation patterns successfully implemented!")
    print(f"   Ready for integration with your Frank Kane Advanced RAG system")

if __name__ == "__main__":
    main()