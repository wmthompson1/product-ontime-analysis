
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

def generate_sql_from_nl(nl_query: str) -> str:
    prompt = f"""
You are a SQL assistant. Based on the schema below, generate a parameterized SQL query.

Schema:
{SQL_SCHEMA_DESCRIPTION}

Rules:
- Only SELECT statements.
- Use %s as placeholders for values.
- Do NOT include any LIMITs or ORDER BY unless explicitly asked.
- Never reference tables that are not in the schema.

Question: {nl_query}

SQL:
"""
    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You convert questions to SQL."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content.strip()
