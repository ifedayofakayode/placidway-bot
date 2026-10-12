import json

import numpy as np
from fastembed import TextEmbedding

import config

class Retriever:
    def __init__(self):
        with open(config.INDEX_PATH, encoding="utf-8") as f:
            data = json.load(f)
        self.built_at = data["built_at"]
        self.chunks = data["chunks"]
        m = np.array([c["embedding"] for c in self.chunks], dtype="float32")
        self.matrix = m / np.linalg.norm(m, axis=1, keepdims=True)   # normalise
        self.model = TextEmbedding(config.EMBED_MODEL)

    def search(self, query, k=config.TOP_K):
        q = np.array(list(self.model.query_embed(query))[0], dtype="float32")
        q = q / np.linalg.norm(q)
        scores = self.matrix @ q                      # cosine similarity
        top = np.argsort(scores)[::-1][:k]
        return [{**self.chunks[i], "score": float(scores[i])} for i in top]