"""
Coletor simples de fontes RSS/Atom para pesquisa macro.
"""

import logging
import xml.etree.ElementTree as ET
from typing import Dict, List

import requests

from config import REQUEST_TIMEOUT

logger = logging.getLogger(__name__)


class ResearchMonitor:
    """Busca artigos e notas em feeds RSS/Atom."""

    def __init__(self):
        self.session = requests.Session()

    def fetch_feed(self, feed_url: str, limit: int = 10) -> List[Dict]:
        """Retorna entradas padronizadas de um feed RSS ou Atom."""
        response = self.session.get(feed_url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()

        root = ET.fromstring(response.content)
        entries = self._parse_rss(root) or self._parse_atom(root)
        return entries[:limit]

    def _parse_rss(self, root: ET.Element) -> List[Dict]:
        items = root.findall(".//channel/item")
        if not items:
            return []

        entries = []
        for item in items:
            entries.append(
                {
                    "title": self._safe_text(item.find("title")),
                    "url": self._safe_text(item.find("link")),
                    "published_at": self._safe_text(item.find("pubDate")),
                    "summary": self._safe_text(item.find("description")),
                }
            )
        return entries

    def _parse_atom(self, root: ET.Element) -> List[Dict]:
        namespace = {"atom": "http://www.w3.org/2005/Atom"}
        items = root.findall(".//atom:entry", namespace)
        if not items:
            return []

        entries = []
        for item in items:
            link = item.find("atom:link", namespace)
            entries.append(
                {
                    "title": self._safe_text(item.find("atom:title", namespace)),
                    "url": link.attrib.get("href", "") if link is not None else "",
                    "published_at": self._safe_text(item.find("atom:updated", namespace)),
                    "summary": self._safe_text(item.find("atom:summary", namespace)),
                }
            )
        return entries

    def _safe_text(self, element: ET.Element) -> str:
        if element is None or element.text is None:
            return ""
        return element.text.strip()
