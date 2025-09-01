from langsmith import Client
from openai import OpenAI
import os
import json
from typing import Dict, Any, List

# Define the input and reference output pairs that you'll use to evaluate your app
client = Client()

# Create the dataset
dataset = client.create_dataset(
    dataset_name="Sample dataset", description="A sample dataset in LangSmith."
)

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

# Add the examples to the dataset
client.create_examples(dataset_id=dataset.id, examples=examples)

# Wrap the OpenAI client for LangSmith tracing
openai_client = wrappers.wrap_openai(OpenAI())

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

# Define an LLM as a judge evaluator to evaluate correctness of the output
# Import a prebuilt evaluator prompt from openevals (https://github.com/langchain-ai/openevals) and create an evaluator.

def correctness_evaluator(inputs: dict, outputs: dict, reference_outputs: dict):
    evaluator = create_llm_as_judge(
        prompt=CORRECTNESS_PROMPT,
        model="openai:o3-mini",
        feedback_key="correctness",
    )
    eval_result = evaluator(
        inputs=inputs,
        outputs=outputs,
        reference_outputs=reference_outputs
    )
    return eval_result
    # After running the evaluation, a link will be provided to view the results in langsmith
    experiment_results = client.evaluate(
        target,
        data="Sample dataset",
        evaluators=[
            correctness_evaluator,
            # you can add multiple evaluators here
        ],
        experiment_prefix="first-eval-in-langsmith",
        max_concurrency=2,
    )

""" 
https://smith.langchain.com/onboarding?organizationId=95f320f8-5610-4227-a649-65ec124f0497&step=4
"""