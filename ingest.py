import os
import json
import shutil
import time
import gc
from datetime import datetime, timezone

from langchain_community.document_loaders import TextLoader, PyPDFLoader, Docx2txtLoader
from langchain_text_splitters.character import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

# --- CONFIG ---
DATA_PATH = "knowledge_base"
DB_PATH = "db"
SNAPSHOT_PATH = os.path.join(DB_PATH, "_raw_docs_snapshot.json")
# --- Use the BGE model to fix the "Finder" bug ---
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

LOADER_MAP = {
    ".txt": (TextLoader, {"encoding": "utf8"}),
    ".pdf": (PyPDFLoader, {}),
    ".docx": (Docx2txtLoader, {}),
    ".md": (TextLoader, {"encoding": "utf8"}), 
}


def safe_remove_db(db_path: str, max_retries: int = 5):
    """
    Safely remove database with retry logic for Windows file locks.
    If database is locked by the app, creates a backup instead.
    """
    if not os.path.exists(db_path):
        print(f"[ingest] No existing database found at '{db_path}'")
        return True
    
    for attempt in range(max_retries):
        try:
            print(f"[ingest] Attempting to remove old database (attempt {attempt + 1}/{max_retries})...")
            
            # Try to close any open connections first
            gc.collect()
            time.sleep(0.5)
            
            # Try to remove
            shutil.rmtree(db_path)
            print("[ingest] [SUCCESS] Old database removed successfully")
            return True
            
        except PermissionError as e:
            print(f"[ingest] [WARNING] Database locked (attempt {attempt + 1}): File is in use")
            
            if attempt < max_retries - 1:
                print(f"[ingest] Waiting 2 seconds before retry...")
                time.sleep(2)
            else:
                print("[ingest] [WARNING] Database is still in use by the app")
                print("[ingest] Creating backup instead of deleting...")
                
                # Create backup instead of deleting
                backup_path = f"{db_path}_backup_{int(time.time())}"
                try:
                    shutil.move(db_path, backup_path)
                    print(f"[ingest] [SUCCESS] Moved old database to: {backup_path}")
                    print(f"[ingest] You can delete '{backup_path}' manually later")
                    return True
                except Exception as backup_err:
                    print(f"[ingest] [WARNING] Backup also failed: {backup_err}")
                    print("[ingest] Will attempt to create new database anyway...")
                    return False
        
        except Exception as e:
            print(f"[ingest] [ERROR] Unexpected error removing database: {e}")
            if attempt < max_retries - 1:
                print(f"[ingest] Retrying in 2 seconds...")
                time.sleep(2)
            else:
                return False
    
    return False


def load_documents(path):
    """Load all documents from the knowledge base directory"""
    print(f"[ingest] Loading documents from '{path}'...")
    all_docs = []
    
    if not os.path.exists(path):
        print(f"[ingest] [ERROR] Directory not found: {path}")
        return all_docs
    
    file_count = 0
    for root, dirs, files in os.walk(path):
        # Skip hidden directories
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        
        for file in files:
            # Skip hidden files
            if file.startswith('.'):
                continue
            
            file_count += 1
            file_ext = os.path.splitext(file)[1].lower()
            file_path = os.path.join(root, file)
            
            # Determine role from directory structure
            relative_path = os.path.relpath(root, path)
            if relative_path == ".":
                role = "general"
            else:
                role = relative_path.split(os.sep)[0]
            
            print(f"[ingest] Found file #{file_count}: '{file_path}' (role: '{role}')")
            
            # Check if file extension is supported
            if file_ext not in LOADER_MAP:
                print(f"[ingest]  -> Skipping unsupported extension: {file_ext}")
                continue
            
            # Load the document
            loader_class, loader_args = LOADER_MAP[file_ext]
            try:
                loader = loader_class(file_path, **loader_args)
                loaded_docs = loader.load()
                
                # Add metadata to each document
                for doc in loaded_docs:
                    # Handle edge case where doc might be a string
                    if isinstance(doc, str):
                        doc = type("D", (), {"page_content": doc, "metadata": {}})()
                    
                    if not hasattr(doc, "metadata"):
                        doc.metadata = {}
                    
                    doc.metadata["role"] = role
                    doc.metadata["source"] = file_path
                
                all_docs.extend(loaded_docs)
                print(f"[ingest]  -> [SUCCESS] Loaded {len(loaded_docs)} chunk(s) from {file}")
                
            except Exception as e:
                print(f"[ingest] [ERROR] Loading '{file_path}': {e}")
                print("[ingest]  -> Skipping file due to loader error.")
    
    print(f"[ingest] Total loaded document objects: {len(all_docs)}")
    return all_docs


def split_text_into_chunks(documents):
    """Split documents into smaller chunks for embedding"""
    print("[ingest] Splitting documents into chunks...")
    
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )
    
    chunks = splitter.split_documents(documents)
    print(f"[ingest] [SUCCESS] Split into {len(chunks)} chunks")
    
    return chunks


def save_snapshot(chunks, snapshot_path=SNAPSHOT_PATH):
    """Save a JSON snapshot of all chunks for backup/debugging"""
    print(f"[ingest] Saving JSON snapshot to '{snapshot_path}'...")
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(snapshot_path), exist_ok=True)
    
    # Convert chunks to JSON-serializable format
    docs_out = []
    for d in chunks:
        meta = getattr(d, "metadata", {}) or {}
        content = getattr(d, "page_content", "") or ""
        docs_out.append({
            "metadata": meta,
            "page_content": content
        })
    
    # Create snapshot (FIXED: Use timezone.utc instead of UTC)
    snapshot = {
        "snapshot_time": datetime.now(timezone.utc).isoformat(),
        "total_chunks": len(docs_out),
        "docs": docs_out
    }
    
    # Save to file
    with open(snapshot_path, "w", encoding="utf-8") as fh:
        json.dump(snapshot, fh, indent=2, ensure_ascii=False)
    
    print(f"[ingest] [SUCCESS] Snapshot saved ({len(docs_out)} chunks)")


def create_and_store_embeddings(chunks):
    """Create embeddings and store in ChromaDB"""
    print(f"[ingest] Initializing embedding model: {EMBEDDING_MODEL}...")
    
    embeddings = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"}
    )
    
    print(f"[ingest] Creating vector store at '{DB_PATH}'...")
    
    try:
        # Create ChromaDB vector store
        vector_store = Chroma.from_documents(
            documents=chunks,
            embedding=embeddings,
            persist_directory=DB_PATH
        )
        
        # Try to persist if method exists
        if hasattr(vector_store, "client") and hasattr(vector_store.client, "persist"):
            vector_store.client.persist()
            print("[ingest] [SUCCESS] Chroma persisted via vector_store.client.persist()")
        else:
            print("[ingest] [WARNING] No persist() method available (newer Chroma version auto-persists)")
        
        print("[ingest] [SUCCESS] Embeddings created and stored successfully")
        return vector_store
        
    except Exception as e:
        print(f"[ingest] [ERROR] Could not create/persist Chroma DB: {e}")
        print("[ingest] [WARNING] Falling back to saving JSON snapshot only")
        return None


def main():
    """Main ingestion pipeline"""
    print("\n" + "=" * 70)
    print("*** STARTING KNOWLEDGE BASE INGESTION ***")
    print("=" * 70 + "\n")
    
    # Step 1: Safely remove old database (with retry logic and backup)
    print(f"[ingest] Step 1: Cleaning old database at '{DB_PATH}'...")
    safe_remove_db(DB_PATH)
    print()
    
    # Step 2: Load documents
    print("[ingest] Step 2: Loading documents...")
    documents = load_documents(DATA_PATH)
    
    if not documents:
        print("[ingest] [ERROR] No documents loaded. Exiting.")
        print("\nTIP: Make sure you have files in the 'knowledge_base/' directory")
        return
    print()
    
    # Step 3: Split into chunks
    print("[ingest] Step 3: Splitting documents...")
    chunks = split_text_into_chunks(documents)
    
    if not chunks:
        print("[ingest] [ERROR] No chunks created. Exiting.")
        return
    print()
    
    # Step 4: Create embeddings and store in ChromaDB
    print("[ingest] Step 4: Creating embeddings and vector store...")
    vs = create_and_store_embeddings(chunks)
    print()
    
    # Step 5: Save JSON snapshot as backup
    print("[ingest] Step 5: Saving JSON snapshot backup...")
    save_snapshot(chunks, snapshot_path=SNAPSHOT_PATH)
    print()
    
    # Final status
    print("=" * 70)
    if vs is None:
        print("*** INGESTION COMPLETED WITH WARNINGS ***")
        print("=" * 70)
        print("[ERROR] Chroma DB creation failed")
        print("[SUCCESS] JSON snapshot saved for fallback")
        print("\nTIP: The system will use JSON fallback until ChromaDB is fixed")
    else:
        print("*** INGESTION COMPLETED SUCCESSFULLY! ***")
        print("=" * 70)
        print(f"Total documents: {len(documents)}")
        print(f"Total chunks: {len(chunks)}")
        print(f"Database location: {DB_PATH}")
        print(f"Snapshot backup: {SNAPSHOT_PATH}")
        print("\nSUCCESS: Knowledge base is ready! You can now query it in the app.")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[ingest] [WARNING] Ingestion interrupted by user")
    except Exception as e:
        print(f"\n[ingest] [ERROR] Fatal error: {e}")
        import traceback
        traceback.print_exc()