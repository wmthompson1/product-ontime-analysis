
import openai
from app.schema_context import SQL_SCHEMA_DESCRIPTION


import os
import re
import random
import openai

from langchain.indexes import VectorstoreIndexCreator
from langchain_openai import ChatOpenAI
from langchain_openai import OpenAIEmbeddings
from langchain_experimental.text_splitter import SemanticChunker    

from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate


openai.api_key = os.getenv("OPENAI_API_KEY")
print("test ok")