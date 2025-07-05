#%pip install datasets tqdm pandas pinecone openai --quiet

import os
import time
from tqdm.auto import tqdm
from pandas import DataFrame
from datasets import load_dataset
import random
import string

# Import OpenAI client and initialize with your API key.
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Import Pinecone client and related specifications.
from pinecone import Pinecone
from pinecone import ServerlessSpec
