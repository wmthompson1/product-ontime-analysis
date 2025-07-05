import os
from datasets import load_dataset
from huggingface_hub import login
import pandas as pd
# Load the dataset (ensure you're logged in with huggingface-cli if needed)
ds = load_dataset("FreedomIntelligence/medical-o1-reasoning-SFT", "en", split='train[:100]', trust_remote_code=True)
ds_dataframe = DataFrame(ds)

# Merge the Question and Response columns into a single string.
ds_dataframe['merged'] = ds_dataframe.apply(
    lambda row: f"Question: {row['Question']} Answer: {row['Response']}", axis=1
)
print("Example merged text:", ds_dataframe['merged'].iloc[0])