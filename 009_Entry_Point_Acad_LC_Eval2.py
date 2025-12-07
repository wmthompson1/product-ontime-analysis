"""
009_Entry_Point_Acad_LC_Eval2.py
LangChain Academy Evaluation - Working Implementation
Fixed openevals import issues with custom LLM-as-Judge
"""
from langsmith import Client, wrappers
from openai import OpenAI
import os
import json
import uuid
from typing import Dict, Any, List

# Initialize LangSmith client
client = Client()

# Create dataset with unique name to avoid conflicts
dataset_name = f"LangChain_Academy_Eval_{str(uuid.uuid4())[:8]}"

try:
    dataset = client.create_dataset(
        dataset_name=dataset_name, 
        description="LangChain Academy evaluation dataset with working LLM-as-Judge."
    )
    print(f"Created dataset: {dataset_name}")
except Exception as e:
    print(f"Dataset creation issue: {e}")
    # For demonstration, continue without dataset
    dataset = None

# Create examples in the dataset. Examples consist of inputs and reference outputs 
examples = [
    {
        "inputs": {"question": "Which country is Mount Kilimanjaro located in?"},
        "outputs": {"answer": "Mount Kilimanjaro is located in Tanzania."},
    },
    {
        "inputs": {"question": "What is Earth's lowest point?"},
        "outputs": {"answer": "Earth's lowest point is The Dead Sea."},
    },
]

# Add examples to dataset if successfully created
if dataset:
    client.create_examples(dataset_id=dataset.id, examples=examples)
    print(f"Added {len(examples)} examples to dataset")

# Wrap the OpenAI client for LangSmith tracing
openai_client = wrappers.wrap_openai(OpenAI())

# Custom LLM-as-Judge implementation (replaces openevals)
def create_custom_correctness_evaluator():
    """Create custom correctness evaluator to replace openevals"""
    
    def evaluator(inputs: dict, outputs: dict, reference_outputs: dict):
        # Extract data
        question = inputs.get("question", "")
        actual_answer = outputs.get("answer", "")
        reference_answer = reference_outputs.get("answer", "")
        
        # Create evaluation prompt
        eval_prompt = f"""
        You are an expert evaluator. Assess the correctness of the actual answer compared to the reference answer.
        
        Question: {question}
        Reference Answer: {reference_answer}
        Actual Answer: {actual_answer}
        
        Evaluate based on:
        - Factual accuracy
        - Completeness
        - Relevance
        
        Respond with JSON:
        {{"score": 0.95, "reasoning": "Brief explanation"}}
        """
        
        try:
            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": eval_prompt}],
                temperature=0.1
            )
            
            result = json.loads(response.choices[0].message.content)
            return {
                "feedback_key": "correctness",
                "score": result.get("score", 0.0),
                "comment": result.get("reasoning", "No reasoning provided")
            }
            
        except Exception as e:
            return {
                "feedback_key": "correctness", 
                "score": 0.0,
                "comment": f"Evaluation failed: {str(e)}"
            }
    
    return evaluator

# Define the application logic you want to evaluate inside a target function. For example, this may be one LLM call that includes the new prompt you are testing, a part of your application or your end to end application
# The SDK will automatically send the inputs from the dataset to your target function
def target(inputs: dict) -> dict:
    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Answer the following question accurately"},
            {"role": "user", "content": inputs["question"]},
        ],
    )
    return { "answer": response.choices[0].message.content.strip() }

# Create the custom correctness evaluator
correctness_evaluator = create_custom_correctness_evaluator()

def main():
    """Main function to run LangChain Academy evaluation"""
    print("🧪 LangChain Academy Evaluation - Entry Point 009")
    print("   Working LLM-as-Judge Implementation")
    print("=" * 55)
    
    if dataset:
        print(f"Dataset: {dataset.name}")
        print(f"Running evaluation with LangSmith integration...")
        
        # Run the evaluation
        try:
            experiment_results = client.evaluate(
                target,
                data=dataset_name,
                evaluators=[
                    correctness_evaluator,
                    # you can add multiple evaluators here
                ],
                experiment_prefix="langchain-academy-eval",
                max_concurrency=2,
            )
            
            print(f"Evaluation completed successfully!")
            print(f"Check LangSmith for detailed results")
            return experiment_results
            
        except Exception as e:
            print(f"Evaluation error: {e}")
            
    else:
        print("Dataset creation failed - running basic demo instead")
        
        # Basic demo without full evaluation
        test_inputs = {"question": "Which country is Mount Kilimanjaro located in?"}
        result = target(test_inputs)
        print(f"Test result: {result}")

if __name__ == "__main__":
    main()

""" 
https://smith.langchain.com/onboarding?organizationId=95f320f8-5610-4227-a649-65ec124f0497&step=4
"""