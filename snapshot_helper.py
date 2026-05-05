# snapshot_helper.py  — safe snapshot loader + simple fallback retriever
import json
import os
from typing import List, Dict, Any, Tuple

# small vectorizer-based retriever (sklearn) — lightweight fallback
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import linear_kernel
    SKLEARN_AVAILABLE = True
except Exception:
    SKLEARN_AVAILABLE = False

SNAPSHOT_PATH = os.path.join("db", "_raw_docs_snapshot.json")

class SnapshotRetriever:
    def __init__(self, snapshot_path=SNAPSHOT_PATH):
        self.snapshot_path = snapshot_path
        self.docs = []
        self._loaded = False
        self._vectorizer = None
        self._matrix = None

    def load_snapshot(self) -> bool:
        if not os.path.exists(self.snapshot_path):
            print(f"[snapshot_helper][WARN] Snapshot not found at {self.snapshot_path}")
            self.docs = []
            self._loaded = True
            return False
        try:
            with open(self.snapshot_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            # Basic validation
            docs = data.get("docs") if isinstance(data, dict) else None
            if not isinstance(docs, list):
                print("[snapshot_helper][ERROR] Snapshot JSON does not contain a 'docs' list.")
                self.docs = []
                self._loaded = True
                return False
            # Normalize
            normalized = []
            for d in docs:
                meta = d.get("metadata", {}) if isinstance(d, dict) else {}
                content = d.get("page_content", "") if isinstance(d, dict) else ""
                normalized.append({"metadata": meta, "page_content": content})
            self.docs = normalized
            self._loaded = True
            print(f"[snapshot_helper] Loaded snapshot with {len(self.docs)} docs.")
            # build vector index if sklearn available
            if SKLEARN_AVAILABLE and self.docs:
                texts = [d["page_content"] for d in self.docs]
                self._vectorizer = TfidfVectorizer(stop_words="english", max_features=4096)
                self._matrix = self._vectorizer.fit_transform(texts)
                print("[snapshot_helper] Built TF-IDF matrix for snapshot retrieval.")
            return True
        except Exception as e:
            print(f"[snapshot_helper][ERROR] Failed to read snapshot: {e}")
            self.docs = []
            self._loaded = True
            return False

    def retrieve(self, query: str, k: int = 3, allowed_roles: List[str] = None) -> List[Dict[str,Any]]:
        """
        Returns a list of docs (dicts) filtered by allowed_roles (if provided)
        and ranked by simple TF-IDF cosine (if available) or by word-overlap fallback.
        """
        if not self._loaded:
            self.load_snapshot()
        if not self.docs:
            return []

        # Filter by role if requested
        def role_allowed(doc_meta):
            if not allowed_roles:
                return True
            role = doc_meta.get("role") or doc_meta.get("metadata", {}).get("role")
            return role in allowed_roles

        candidates = [d for d in self.docs if role_allowed(d["metadata"])]

        if not candidates:
            return []

        if SKLEARN_AVAILABLE and self._matrix is not None:
            try:
                q_vec = self._vectorizer.transform([query])
                scores = linear_kernel(q_vec, self._matrix).flatten()
                # pair scores with docs (only for candidates)
                # We must map back since _matrix was built on all docs
                # Build list of (score, doc) using indices of self.docs
                scored = []
                for idx, d in enumerate(self.docs):
                    if d in candidates:
                        scored.append((scores[idx], d))
                scored.sort(key=lambda x: x[0], reverse=True)
                top = [d for score, d in scored[:k]]
                return top
            except Exception as e:
                print(f"[snapshot_helper][WARN] sklearn scoring failed: {e}")

        # fallback: word-overlap ranking
        q_words = set(query.lower().split())
        def score_doc(d):
            words = set(d["page_content"].lower().split())
            return len(q_words & words)
        candidates.sort(key=score_doc, reverse=True)
        return candidates[:k]
