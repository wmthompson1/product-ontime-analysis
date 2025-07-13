# Pinecone API key
# pcsk_5R2pu4_LeqndKKt5QyTiNmgH7KDajjBEr4vMsXYFX5SuoDi58ywPzAPj3UK6sg2BSXZAbD

from pinecone import Pinecone, ServerlessSpec

pc = Pinecone(
    api_key=
    "pcsk_5R2pu4_LeqndKKt5QyTiNmgH7KDajjBEr4vMsXYFX5SuoDi58ywPzAPj3UK6sg2BSXZAbD"
)

index_name = "developer-quickstart-py"

if not pc.has_index(index_name):
  pc.create_index_for_model(name=index_name,
                            cloud="aws",
                            region="us-east-1",
                            embed={
                                "model": "llama-text-embed-v2",
                                "field_map": {
                                    "text": "chunk_text"
                                }
                            })

index = pc.Index(index_name)

records = [{
    "_id": "rec1",
    "chunk_text":
    "The Eiffel Tower was completed in 1889 and stands in Paris, France.",
    "category": "history"
}, {
    "_id": "rec2",
    "chunk_text":
    "Photosynthesis allows plants to convert sunlight into energy.",
    "category": "science"
}, {
    "_id": "rec3",
    "chunk_text": "Albert Einstein developed the theory of relativity.",
    "category": "science"
}, {
    "_id": "rec4",
    "chunk_text":
    "The mitochondrion is often called the powerhouse of the cell.",
    "category": "biology"
}, {
    "_id": "rec5",
    "chunk_text":
    "Shakespeare wrote many famous plays, including Hamlet and Macbeth.",
    "category": "literature"
}, {
    "_id": "rec6",
    "chunk_text": "Water boils at 100°C under standard atmospheric pressure.",
    "category": "physics"
}, {
    "_id": "rec7",
    "chunk_text":
    "The Great Wall of China was built to protect against invasions.",
    "category": "history"
}, {
    "_id": "rec8",
    "chunk_text":
    "Honey never spoils due to its low moisture content and acidity.",
    "category": "food science"
}, {
    "_id": "rec9",
    "chunk_text":
    "The speed of light in a vacuum is approximately 299,792 km/s.",
    "category": "physics"
}, {
    "_id": "rec10",
    "chunk_text": "Newton's laws describe the motion of objects.",
    "category": "physics"
}]

index.upsert_records("ns1", records)

query = "Famous historical structures and monuments"

results = index.search(namespace="ns1",
                       query={
                           "top_k": 5,
                           "inputs": {
                               'text': query
                           }
                       })

print(results)

reranked_results = index.search(namespace="ns1",
                                query={
                                    "top_k": 5,
                                    "inputs": {
                                        'text': query
                                    }
                                },
                                rerank={
                                    "model": "bge-reranker-v2-m3",
                                    "top_n": 5,
                                    "rank_fields": ["chunk_text"]
                                },
                                fields=["category", "chunk_text"])

print(reranked_results)
