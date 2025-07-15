rag_app/
│
├── app/
│   ├── main.py               # FastAPI app
│   ├── semantic_layer.py     # NL → SQL logic (OpenAI + templates)
│   ├── db.py                 # Safe SQL execution
│   ├── schema_context.py     # Info about SQL schema for prompting
│   ├── config.py
│
├── .env
└── README.md
