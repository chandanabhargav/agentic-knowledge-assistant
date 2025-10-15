import hashlib
from typing import List, Dict
from core.settings import settings
from openai import OpenAI

_client = OpenAI(api_key=settings.OPENAI_API_KEY)
_CACHE: Dict[str, List[float]] = {}

def _h(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def embed_texts(texts: List[str]) -> List[List[float]]:
    to_query, order = [], []
    for t in texts:
        h = _h(t)
        if h not in _CACHE:
            to_query.append(t)
            order.append(h)
    if to_query:
        resp = _client.embeddings.create(model=settings.EMBED_MODEL, input=to_query)
        for h, d in zip(order, resp.data):
            _CACHE[h] = d.embedding
    return [_CACHE[_h(t)] for t in texts]
