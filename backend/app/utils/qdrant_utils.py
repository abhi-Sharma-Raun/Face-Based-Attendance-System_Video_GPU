from qdrant_client.models import HasIdCondition, QueryRequest, SearchParams, Filter, FieldCondition, MatchAny, Prefetch, Fusion, FusionQuery
from ..qdrant_setup import client, collection_name
from ..config import settings
from typing import List, Any, Literal, Optional


def build_query(embedding, shared_filter=None):
    
    params = SearchParams(exact=True)
    embed_list = embedding.tolist()
    
    prefetch_ = [
        Prefetch(query=embed_list, using="front", filter=shared_filter, params=params),
        Prefetch(query=embed_list, using="left", filter=shared_filter, params=params),
        Prefetch(query=embed_list, using="right", filter=shared_filter, params=params),
    ]
    query_req = QueryRequest(
        prefetch=prefetch_, query=FusionQuery(fusion=Fusion.RRF), limit=1, score_threshold=settings.face_similarity_threshold,
        with_payload=True, with_vector=False,
    )
    return query_req

def qdrant_cosine_search(embeddings: List[Any], purpose: Literal["Face_registration", "attendance"], studs_ids: Optional[List[Any]]=None):
    
    
    if purpose == "Face_registration":
        assert len(embeddings) == 3
        search_queries = [build_query(v) for v in embeddings]
        qd_response = client.query_batch_points(
            collection_name = collection_name,
            requests = search_queries
        )
    
    else:
        assert studs_ids is not None
        assert len(studs_ids)>0
        CHUNK_SIZE=80
        qd_response = []
        shared_filter = Filter(
            must=[HasIdCondition(has_id=studs_ids)]
        )
        all_queries = [build_query(v, shared_filter) for v in embeddings]
        qd_response = []
        for i in range(0, len(all_queries), CHUNK_SIZE):
            batch = all_queries[i:i + CHUNK_SIZE]
            batch_response = client.query_batch_points(
                collection_name = collection_name,
                requests = batch
            )
            qd_response.extend(batch_response)
        
    return qd_response

