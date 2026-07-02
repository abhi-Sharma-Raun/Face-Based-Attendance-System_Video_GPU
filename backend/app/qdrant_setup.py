from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, HnswConfigDiff
from .config import settings

# connect to Qdrant Cloud
client = QdrantClient(
    url=settings.qdrant_url,
    api_key=settings.qdrant_api_key,
    cloud_inference=True
)

collection_name = "Face_Embeddings-All"
if client.collection_exists(collection_name=collection_name):
    print("Collection exists")
else:
    client.create_collection(
    collection_name=collection_name,
    vectors_config=VectorParams(
        size=512,
        distance=Distance.COSINE
    ),
    hnsw_config=HnswConfigDiff(
        m=0,  
    ))
    print("Collection created successfully")
    
