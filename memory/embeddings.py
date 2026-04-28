"""
Gerenciador de embeddings com foco em simplicidade.
Por padrao usa sentence-transformers local.
"""

import logging
from typing import List

import numpy as np

from config import OPENAI_API_KEY

logger = logging.getLogger(__name__)

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
    SENTENCE_TRANSFORMERS_IMPORT_ERROR = ""
except Exception as e:
    SentenceTransformer = None
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    SENTENCE_TRANSFORMERS_IMPORT_ERROR = str(e)


class EmbeddingManager:
    """Gerenciador de embeddings com fallback automatico."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.use_openai = False
        self.model = None
        self.client = None

        if OPENAI_AVAILABLE and OPENAI_API_KEY:
            try:
                self.client = OpenAI(api_key=OPENAI_API_KEY)
                self.use_openai = True
                logger.info("Usando OpenAI Embeddings API")
            except Exception as e:
                logger.warning(f"OpenAI indisponivel, usando modelo local: {str(e)}")
                self.use_openai = False

        if not self.use_openai:
            if not SENTENCE_TRANSFORMERS_AVAILABLE:
                detail = f": {SENTENCE_TRANSFORMERS_IMPORT_ERROR}" if SENTENCE_TRANSFORMERS_IMPORT_ERROR else ""
                raise ImportError(f"sentence-transformers indisponivel{detail}")

            self.model = SentenceTransformer(model_name)
            logger.info(f"Modelo local carregado: {model_name}")

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        try:
            if self.use_openai:
                response = self.client.embeddings.create(
                    input=texts,
                    model="text-embedding-3-small",
                )
                return [item.embedding for item in response.data]

            embeddings = self.model.encode(texts, show_progress_bar=False)
            return embeddings.tolist()

        except Exception as e:
            logger.error(f"Erro ao gerar embeddings: {str(e)}")
            raise

    def embed_single(self, text: str) -> List[float]:
        return self.embed_texts([text])[0]

    def similarity(self, text1: str, text2: str) -> float:
        try:
            emb1 = self.embed_single(text1)
            emb2 = self.embed_single(text2)

            dot_product = np.dot(emb1, emb2)
            norm1 = np.linalg.norm(emb1)
            norm2 = np.linalg.norm(emb2)

            if norm1 == 0 or norm2 == 0:
                return 0.0

            return float(dot_product / (norm1 * norm2))
        except Exception as e:
            logger.error(f"Erro ao calcular similaridade: {str(e)}")
            return 0.0

    def batch_similarity(self, reference_text: str, comparison_texts: List[str]) -> List[float]:
        try:
            ref_emb = self.embed_single(reference_text)
            comp_embs = self.embed_texts(comparison_texts)

            similarities = []
            norm_ref = np.linalg.norm(ref_emb)

            for comp_emb in comp_embs:
                norm_comp = np.linalg.norm(comp_emb)
                if norm_ref == 0 or norm_comp == 0:
                    similarities.append(0.0)
                    continue

                dot_product = np.dot(ref_emb, comp_emb)
                similarities.append(float(dot_product / (norm_ref * norm_comp)))

            return similarities
        except Exception as e:
            logger.error(f"Erro ao calcular batch similarity: {str(e)}")
            return []

    def get_model_info(self) -> dict:
        return {
            "using_openai": self.use_openai,
            "model_name": self.model_name,
            "embedding_dimension": (
                1536 if self.use_openai else self.model.get_sentence_embedding_dimension()
            ),
        }
