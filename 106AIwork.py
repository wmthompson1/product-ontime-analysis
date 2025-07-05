import os
from datasets import load_dataset
from huggingface_hub import login

# Login programmatically
login(token=os.getenv("HUGGINGFACE_TOKEN"))

# Load dataset
ds = load_dataset("dataset-name")
