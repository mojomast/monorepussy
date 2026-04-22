"""Search and indexing utilities."""

import re
from typing import List, Dict, Any


class SimpleSearch:
    """Simple full-text search implementation."""

    def __init__(self):
        self.documents: Dict[str, str] = {}
        self.index: Dict[str, set] = {}

    def add_document(self, doc_id: str, content: str):
        """Add a document to the index."""
        self.documents[doc_id] = content

        # Tokenize and index
        words = re.findall(r"\b\w+\b", content.lower())
        for word in words:
            if word not in self.index:
                self.index[word] = set()
            self.index[word].add(doc_id)

    def search(self, query: str) -> List[str]:
        """Search for documents matching the query."""
        words = re.findall(r"\b\w+\b", query.lower())

        if not words:
            return []

        results = self.index.get(words[0], set()).copy()

        for word in words[1:]:
            results &= self.index.get(word, set())

        return list(results)

    def get_document(self, doc_id: str) -> str:
        """Get a document by ID."""
        return self.documents.get(doc_id, "")


class FilterEngine:
    """Filter and sort results."""

    @staticmethod
    def apply_filters(items: List[Any], filters: Dict[str, Any]) -> List[Any]:
        """Apply filters to a list of items."""
        result = items

        for key, value in filters.items():
            if value is not None:
                result = [item for item in result if getattr(item, key, None) == value]

        return result

    @staticmethod
    def sort_by(items: List[Any], field: str, reverse: bool = False) -> List[Any]:
        """Sort items by a field."""
        return sorted(
            items, key=lambda x: getattr(x, field, None) or "", reverse=reverse
        )
