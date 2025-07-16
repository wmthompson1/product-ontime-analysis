"""
python semantic_layer_ver3.py 
/home/runner/workspace/.pythonlibs/lib/python3.11/site-packages/langchain/indexes/vectorstore.py:171: UserWarning: Using InMemoryVectorStore as the default vectorstore.This memory store won't persist data. You should explicitlyspecify a vectorstore when using VectorstoreIndexCreator
  warnings.warn(

"""

import os
import re
import random
import openai

from langchain.indexes import VectorstoreIndexCreator
from langchain_openai import ChatOpenAI
from langchain_openai import OpenAIEmbeddings
from langchain_experimental.text_splitter import SemanticChunker

# Import OpenAI client and initialize with your API key.
from openai import OpenAI

api_key = os.getenv("OPENAI_API_KEY")

dialogues = []


def strip_parentheses(s):
    return re.sub(r'', '', s)


def is_single_word_all_caps(s):
    # First, we split the string into words
    words = s.split()

    # Check if the string contains only a single word
    if len(words) != 1:
        return False

    # Make sure it isn't a line number
    if bool(re.search(r'\d', words[0])):
        return False

    # Check if the single word is in all caps
    return words[0].isupper()


def extract_character_lines(file_path, character_name):
    lines = []
    with open(file_path, 'r') as script_file:
        try:
            lines = script_file.readlines()
        except UnicodeDecodeError:
            pass

    is_character_line = False
    current_line = ''
    current_character = ''
    for line in lines:
        strippedLine = line.strip()
        if (is_single_word_all_caps(strippedLine)):
            is_character_line = True
            current_character = strippedLine
        elif (line.strip() == '') and is_character_line:
            is_character_line = False
            dialog_line = strip_parentheses(current_line).strip()
            dialog_line = dialog_line.replace('"', "'")
            if (current_character == 'DATA' and len(dialog_line) > 0):
                dialogues.append(dialog_line)
            current_line = ''
        elif is_character_line:
            current_line += line.strip() + ' '


def process_directory(directory_path, character_name):
    for filename in os.listdir(directory_path):
        file_path = os.path.join(directory_path, filename)
        if os.path.isfile(file_path):  # Ignore directories
            extract_character_lines(file_path, character_name)


process_directory("./sample_data/tng", 'DATA')

# Access the API key from the environment variable
#from google.colab import userdata
# api_key = userdata.get('OPENAI_API_KEY')
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Initialize the OpenAI API client
# openai.api_key = api_key

# Write our extracted lines for Data into a single file, to make
# life easier for langchain.

with open("./sample_data/data_lines.txt", "w+") as f:
    for line in dialogues:
        f.write(line + "\n")

text_splitter = SemanticChunker(OpenAIEmbeddings(openai_api_key=api_key),
                                breakpoint_threshold_type="percentile")
with open("./sample_data/data_lines.txt") as f:
    data_lines = f.read()
docs = text_splitter.create_documents([data_lines])

embeddings = OpenAIEmbeddings(openai_api_key=api_key)
index = VectorstoreIndexCreator(embedding=embeddings).from_documents(docs)
