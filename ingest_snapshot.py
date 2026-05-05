# ingest_snapshot.py
"""
Lightweight ingestion that creates db/_raw_docs_snapshot.json without Chroma.
Reads .txt files (primary), and will include .pdf/.docx only if python libraries are available.
Splits each loaded document into chunks and writes a stable JSON snapshot for the query fallback.
"""

import os
import json
from datetime import datetime, timezone

DATA_PATH = "knowledge_base"
DB_DIR = "db"
SNAPSHOT_PATH = os.path.join(DB_DIR, "_raw_docs_snapshot.json")

# Chunking parameters
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

SUPPORTED_EXTS = [".txt", ".pdf", ".docx"]

def read_text_file(path):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read()
    except UnicodeDecodeError:
        try:
            with open(path, "r", encoding="latin-1") as fh:
                return fh.read()
        except Exception as e:
            print(f"[ingest_snapshot] Failed to read text file {path}: {e}")
            return ""
    except Exception as e:
        print(f"[ingest_snapshot] Failed to read text file {path}: {e}")
        return ""

def read_pdf(path):
    try:
        import PyPDF2
    except Exception:
        print(f"[ingest_snapshot] PyPDF2 not installed — skipping PDF text extraction for {path}")
        return ""
    try:
        text_parts = []
        with open(path, "rb") as fh:
            reader = PyPDF2.PdfReader(fh)
            for p in reader.pages:
                text_parts.append(p.extract_text() or "")
        return "\n".join(text_parts)
    except Exception as e:
        print(f"[ingest_snapshot] PDF read error for {path}: {e}")
        return ""

def read_docx(path):
    try:
        import docx
    except Exception:
        print(f"[ingest_snapshot] python-docx not installed — skipping .docx extraction for {path}")
        return ""
    try:
        doc = docx.Document(path)
        return "\n".join([p.text for p in doc.paragraphs])
    except Exception as e:
        print(f"[ingest_snapshot] docx read error for {path}: {e}")
        return ""

def safe_read_file(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".txt":
        return read_text_file(path)
    elif ext == ".pdf":
        return read_pdf(path)
    elif ext == ".docx":
        return read_docx(path)
    else:
        return ""

def chunk_text(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    """
    Return list of chunks. Ensure overlap < chunk_size to avoid infinite loops.
    """
    if not text:
        return []
    chunk_size = max(1, int(chunk_size))
    overlap = int(overlap)
    if overlap >= chunk_size:
        # Make overlap slightly smaller than chunk_size
        overlap = max(0, chunk_size - 1)

    chunks = []
    start = 0
    length = len(text)
    while start < length:
        end = start + chunk_size
        chunk = text[start:end]
        chunk = chunk.strip()
        if chunk:
            chunks.append(chunk)
        # Advance start; ensure progress
        start = end - overlap
        if start <= end and start < length and start > (end - chunk_size):
            # OK, continue
            pass
    return chunks

def _first_level_role(root_path, data_root):
    # Determine immediate subdirectory under data_root that contains file
    rel = os.path.relpath(root_path, data_root)
    if rel == "." or rel == "":
        return "general"
    parts = rel.split(os.sep)
    return parts[0] if parts else "general"

def discover_and_load(data_path=DATA_PATH):
    print(f"[ingest_snapshot] Scanning '{data_path}' for documents...")
    docs = []
    if not os.path.exists(data_path):
        print("[ingest_snapshot][ERROR] knowledge_base directory not found.")
        return docs

    count = 0
    for root, dirs, files in os.walk(data_path):
        # skip hidden directories
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for fname in files:
            if fname.startswith("."):
                continue  # skip hidden files
            file_path = os.path.join(root, fname)
            ext = os.path.splitext(fname)[1].lower()
            role = _first_level_role(root, data_path)

            count += 1
            print(f"[ingest_snapshot] Found file #{count}: {file_path} (role='{role}')")
            if ext not in SUPPORTED_EXTS:
                print(f"[ingest_snapshot]  -> Skipping unsupported extension: {ext}")
                continue

            text = safe_read_file(file_path)
            if not text or not text.strip():
                print(f"[ingest_snapshot]  -> No text extracted from {file_path}; skipping.")
                continue

            # chunk into manageable pieces
            chunks = chunk_text(text)
            for i, chunk in enumerate(chunks):
                docs.append({
                    "metadata": {"source": file_path, "role": role, "chunk_index": i},
                    "page_content": chunk
                })
            print(f"[ingest_snapshot]  -> Extracted {len(chunks)} chunk(s) from {fname}")
    print(f"[ingest_snapshot] Total chunks produced: {len(docs)}")
    return docs

def save_snapshot(docs, snapshot_path=SNAPSHOT_PATH):
    try:
        os.makedirs(os.path.dirname(snapshot_path), exist_ok=True)
        payload = {
            # timezone-aware UTC ISO timestamp
            "snapshot_time": datetime.now(timezone.utc).isoformat(),
            "docs": docs
        }
        with open(snapshot_path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=False)
        print(f"[ingest_snapshot] Snapshot saved to: {snapshot_path}")
    except Exception as e:
        print(f"[ingest_snapshot] Failed to save snapshot to {snapshot_path}: {e}")

def main():
    docs = discover_and_load(DATA_PATH)
    if not docs:
        print("[ingest_snapshot] No documents loaded — snapshot will contain zero docs.")
    save_snapshot(docs)

if __name__ == "__main__":
    main()
