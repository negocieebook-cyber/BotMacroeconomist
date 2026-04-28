"""
Gerenciador de memoria com ChromaDB.
"""

from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import shutil
import sqlite3
from typing import Dict, List, Optional

import chromadb
from chromadb.config import Settings
import pandas as pd

from config import CHROMA_COLLECTION_NAME, CHROMA_DB_PATH, MAX_EMBEDDINGS_PER_BATCH

logger = logging.getLogger(__name__)


class ChromaDBManager:
    """Gerenciador de ChromaDB para memoria do agente."""

    def __init__(self, persist_directory: str = CHROMA_DB_PATH):
        self.persist_directory = self._select_persist_directory(persist_directory)
        os.makedirs(self.persist_directory, exist_ok=True)
        self.client = None
        self.collection = None
        try:
            self.client = self._build_client(persist_directory)
            self.collection = self._get_or_create_collection()
        except Exception as e:
            if self._should_reset_database(e):
                self._shutdown_client()
                self.persist_directory = self._reset_broken_database()
                logger.warning(
                    f"ChromaDB local estava inconsistente e foi reinicializado do zero: {e}"
                )
                self.client = self._build_client(self.persist_directory)
                self.collection = self._get_or_create_collection()
            else:
                raise

        logger.info(f"ChromaDB inicializado em {self.persist_directory}")

    def add_data(
        self,
        texts: List[str],
        metadatas: List[Dict],
        ids: Optional[List[str]] = None,
    ) -> None:
        """Adiciona documentos na colecao."""
        try:
            if ids is None:
                ids = [
                    f"{m.get('api', 'unknown')}_{m.get('serie', 'unknown')}_{i}_{int(datetime.now(timezone.utc).timestamp())}"
                    for i, m in enumerate(metadatas)
                ]

            for i in range(0, len(texts), MAX_EMBEDDINGS_PER_BATCH):
                batch_texts = texts[i : i + MAX_EMBEDDINGS_PER_BATCH]
                batch_metadatas = metadatas[i : i + MAX_EMBEDDINGS_PER_BATCH]
                batch_ids = ids[i : i + MAX_EMBEDDINGS_PER_BATCH]

                self.collection.add(
                    documents=batch_texts,
                    metadatas=batch_metadatas,
                    ids=batch_ids,
                )

                logger.info(f"{len(batch_texts)} documentos adicionados ao ChromaDB")

        except Exception as e:
            logger.error(f"Erro ao adicionar dados ao ChromaDB: {str(e)}")
            raise

    def search(
        self,
        query: str,
        n_results: int = 5,
        where: Optional[Dict] = None,
    ) -> Dict:
        """Busca semantica na colecao."""
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where,
            )

            documents = results.get("documents", [[]])[0]
            metadatas = results.get("metadatas", [[]])[0]
            distances = results.get("distances", [[]])[0]
            ids = results.get("ids", [[]])[0]

            formatted_results = {
                "query": query,
                "results": [
                    {
                        "id": doc_id,
                        "document": doc,
                        "metadata": meta,
                        "distance": dist,
                        "api": meta.get("api", "unknown") if meta else "unknown",
                    }
                    for doc_id, doc, meta, dist in zip(ids, documents, metadatas, distances)
                ],
            }

            logger.info(
                f"Busca realizada: '{query}' - {len(formatted_results['results'])} resultados"
            )
            return formatted_results

        except Exception as e:
            logger.error(f"Erro ao buscar no ChromaDB: {str(e)}")
            return {"query": query, "results": []}

    def add_data_from_dataframe(
        self,
        df: pd.DataFrame,
        api_source: str,
        serie_id: str = None,
    ) -> None:
        """Adiciona dados de um DataFrame."""
        try:
            if df.empty:
                logger.warning("DataFrame vazio, pulando")
                return

            texts = []
            metadatas = []

            for idx, row in df.iterrows():
                text = self._row_to_text(row)
                texts.append(text)

                metadata = {
                    "api": api_source,
                    "serie": serie_id or "unknown",
                    "timestamp": datetime.now().isoformat(),
                    "row_index": str(idx),
                }

                for col in df.columns:
                    if col not in ["value", "date", "datetime"]:
                        metadata[col] = str(row[col])

                metadatas.append(metadata)

            self.add_data(texts, metadatas)

        except Exception as e:
            logger.error(f"Erro ao adicionar DataFrame: {str(e)}")
            raise

    def add_indicator_data(self, indicator_name: str, data: Dict, api_source: str) -> None:
        """Adiciona dados de um indicador macroeconomico."""
        try:
            text = f"{indicator_name} ({api_source}): {json.dumps(data, indent=2, default=str)}"

            metadata = {
                "api": api_source,
                "indicator": indicator_name,
                "timestamp": datetime.now().isoformat(),
                "type": "indicator",
            }

            self.add_data([text], [metadata])
            logger.info(f"Indicador {indicator_name} adicionado")

        except Exception as e:
            logger.error(f"Erro ao adicionar indicador: {str(e)}")
            raise

    def get_collection_stats(self) -> Dict:
        """Retorna estatisticas da colecao."""
        try:
            count = self.collection.count()
            return {
                "total_documents": count,
                "collection_name": CHROMA_COLLECTION_NAME,
                "db_path": self.persist_directory,
            }
        except Exception as e:
            logger.error(f"Erro ao obter estatisticas: {str(e)}")
            return {}

    def get_recent_documents(self, limit: int = 5) -> List[Dict]:
        """Retorna documentos recentes da colecao com preview legivel."""
        try:
            result = self.collection.get(
                limit=limit,
                include=["documents", "metadatas"],
            )

            documents = result.get("documents", [])
            metadatas = result.get("metadatas", [])
            ids = result.get("ids", [])

            recent_docs = []
            for doc_id, document, metadata in zip(ids, documents, metadatas):
                preview = str(document).replace("\n", " ").strip()
                if len(preview) > 240:
                    preview = preview[:240] + "..."

                recent_docs.append(
                    {
                        "id": doc_id,
                        "metadata": metadata or {},
                        "document": document,
                        "preview": preview,
                    }
                )

            return recent_docs
        except Exception as e:
            logger.error(f"Erro ao obter documentos recentes: {str(e)}")
            return []

    def get_documents_for_date(self, date_prefix: str) -> List[Dict]:
        """Retorna documentos com timestamp iniciado pela data informada (YYYY-MM-DD)."""
        try:
            result = self.collection.get(
                include=["documents", "metadatas"],
            )

            documents = result.get("documents", [])
            metadatas = result.get("metadatas", [])
            ids = result.get("ids", [])
            matched_docs = []

            for doc_id, document, metadata in zip(ids, documents, metadatas):
                metadata = metadata or {}
                timestamp = str(metadata.get("timestamp", ""))
                if not timestamp.startswith(date_prefix):
                    continue

                preview = str(document).replace("\n", " ").strip()
                if len(preview) > 240:
                    preview = preview[:240] + "..."

                matched_docs.append(
                    {
                        "id": doc_id,
                        "metadata": metadata,
                        "document": document,
                        "preview": preview,
                    }
                )

            matched_docs.sort(
                key=lambda item: item.get("metadata", {}).get("timestamp", ""),
            )
            return matched_docs
        except Exception as e:
            logger.error(f"Erro ao obter documentos por data: {str(e)}")
            return []

    def has_document_for_date(
        self,
        date_prefix: str,
        metadata_type: str = None,
        focus_area: str = None,
    ) -> bool:
        """Verifica se ja existe documento para a data com filtros opcionais."""
        documents = self.get_documents_for_date(date_prefix)

        for item in documents:
            metadata = item.get("metadata", {})
            if metadata_type and metadata.get("type") != metadata_type:
                continue
            if focus_area and metadata.get("focus_area") != focus_area:
                continue
            return True

        return False

    def has_source_document(self, url: str = "", title: str = "") -> bool:
        """Verifica se uma fonte ja foi armazenada pela URL ou titulo."""
        try:
            result = self.collection.get(include=["metadatas"])
            metadatas = result.get("metadatas", [])

            normalized_url = (url or "").strip().lower()
            normalized_title = (title or "").strip().lower()

            for metadata in metadatas:
                metadata = metadata or {}
                if metadata.get("type") != "source_article":
                    continue

                existing_url = str(metadata.get("url", "")).strip().lower()
                existing_title = str(metadata.get("title", "")).strip().lower()

                if normalized_url and existing_url and normalized_url == existing_url:
                    return True
                if normalized_title and existing_title and normalized_title == existing_title:
                    return True

            return False
        except Exception as e:
            logger.error(f"Erro ao verificar fonte duplicada: {str(e)}")
            return False

    def clear_collection(self) -> None:
        """Limpa toda a colecao."""
        try:
            self.client.delete_collection(name=CHROMA_COLLECTION_NAME)
            self.collection = self._get_or_create_collection()
            logger.warning("Colecao completamente limpa")
        except Exception as e:
            logger.error(f"Erro ao limpar colecao: {str(e)}")

    def close(self) -> None:
        """Libera recursos internos do cliente persistente."""
        self._shutdown_client()

    def _build_client(self, persist_directory: str):
        return chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                is_persistent=True,
                persist_directory=persist_directory,
            ),
        )

    def _get_or_create_collection(self):
        return self.client.get_or_create_collection(
            name=CHROMA_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

    def _should_reset_database(self, error: Exception) -> bool:
        message = str(error).lower()
        reset_markers = [
            "no such column",
            "sqlite",
            "schema",
            "collections.topic",
            "migration",
        ]
        return any(marker in message for marker in reset_markers)

    def _shutdown_client(self) -> None:
        client = getattr(self, "client", None)
        if client is None:
            return

        stop = getattr(client, "stop", None)
        if callable(stop):
            try:
                stop()
            except Exception as exc:
                logger.warning(f"Nao foi possivel encerrar cliente antigo do ChromaDB: {exc}")

        self.client = None
        self.collection = None

    def _reset_broken_database(self) -> str:
        """Recria a persistencia local ou usa um diretorio novo se o antigo estiver bloqueado."""
        source_dir = Path(self.persist_directory)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")

        if source_dir.exists():
            try:
                shutil.rmtree(source_dir)
            except Exception as exc:
                backup_dir = source_dir.with_name(f"{source_dir.name}.broken-{timestamp}")
                try:
                    source_dir.rename(backup_dir)
                    logger.warning(f"Base ChromaDB antiga movida para {backup_dir}: {exc}")
                except Exception as rename_exc:
                    recovery_dir = source_dir.with_name(f"{source_dir.name}.recovered-{timestamp}")
                    recovery_dir.mkdir(parents=True, exist_ok=True)
                    logger.warning(
                        "Nao foi possivel limpar ou mover a base ChromaDB antiga. "
                        f"Usando {recovery_dir}: {rename_exc}"
                    )
                    return str(recovery_dir)

        source_dir.mkdir(parents=True, exist_ok=True)
        return str(source_dir)

    def _select_persist_directory(self, persist_directory: str) -> str:
        source_dir = Path(persist_directory)
        if not self._has_broken_chroma_schema(source_dir):
            return str(source_dir)

        recovered_dirs = sorted(
            source_dir.parent.glob(f"{source_dir.name}.recovered-*"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        for recovered_dir in recovered_dirs:
            if not self._has_broken_chroma_schema(recovered_dir):
                logger.warning(
                    f"Base ChromaDB principal esta inconsistente. Usando {recovered_dir}."
                )
                return str(recovered_dir)

        return str(source_dir)

    def _has_broken_chroma_schema(self, directory: Path) -> bool:
        db_path = directory / "chroma.sqlite3"
        if not db_path.exists():
            return False

        try:
            with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True) as conn:
                columns = {
                    row[1]
                    for row in conn.execute("PRAGMA table_info(collections)").fetchall()
                }
        except sqlite3.Error:
            return True

        return bool(columns) and "topic" not in columns

    def _row_to_text(self, row: pd.Series) -> str:
        """Converte uma linha de DataFrame em texto descritivo."""
        text_parts = []

        for col, val in row.items():
            if pd.notna(val) and col not in ["source", "timestamp"]:
                text_parts.append(f"{col}: {val}")

        return " | ".join(text_parts)


class MemoryAnalyzer:
    """Analisa e extrai insights da memoria."""

    def __init__(self, chromadb_manager: ChromaDBManager):
        self.db = chromadb_manager

    def search_by_indicator(self, indicator: str, n_results: int = 5) -> Dict:
        """Busca por significado, sem depender de metadata perfeita."""
        return self.db.search(
            query=f"dados historicos de {indicator}",
            n_results=n_results,
        )

    def search_by_api(self, api_source: str, n_results: int = 10) -> Dict:
        """Busca todos os dados de uma API especifica."""
        return self.db.search(
            query="dados economicos",
            n_results=n_results,
            where={"api": api_source},
        )

    def get_latest_data(self) -> Dict:
        """Retorna estatisticas da memoria."""
        return self.db.get_collection_stats()
