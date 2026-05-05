import os
import json
import traceback
from typing import List, Callable, Optional
import re

# Langchain / local LLM imports
from langchain_community.llms import CTransformers
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

try:
    from langchain_chroma import Chroma
    CHROMA_AVAILABLE = True
except Exception:
    CHROMA_AVAILABLE = False

# --- Global reference to API manager (will be set by app.py) ---
api_manager_instance = None

def set_api_manager(api_mgr):
    """Called from app.py to set the shared API manager"""
    global api_manager_instance
    api_manager_instance = api_mgr
    print("[API] API Manager set successfully in query.py")

def get_pto_balance(username: str) -> str:
    """
    Get PTO balance from shared API manager (live data).
    Falls back to fake data if API not initialized.
    """
    print(f"[get_pto_balance] username={username}")
    
    # Try to get from API manager first
    if api_manager_instance is not None:
        try:
            emp_result = api_manager_instance.fetch_employee_data(username)
            if emp_result["status"] == "success":
                pto = emp_result["data"]["pto_balance"]
                print(f"[get_pto_balance] Got live PTO balance from API: {pto}")
                return f"User '{username}' has {pto} days of PTO remaining."
        except Exception as e:
            print(f"[get_pto_balance] API call failed: {e}")
    
    # Fallback to fake data if API not available
    print("[get_pto_balance] Using fallback fake balances (API not initialized)")
    fake_balances = {"admin": 14, "finance": 10, "hr": 12, "it_support": 14, "engineering": 16, "general": 20}
    balance = fake_balances.get(username, 0)
    return f"User '{username}' has {balance} days of PTO remaining (from fallback data)."

def is_balance_query(text: str) -> bool:
    """
    Return True only when the user is asking for a *personal* PTO balance.
    This is strict to avoid false positives.
    """
    t = (text or "").strip().lower()
    
    # Must contain "pto" or related terms
    pto_terms = ["pto", "paid time off", "vacation days", "time off"]
    if not any(term in t for term in pto_terms):
        return False
        
    # Must contain a "balance" word
    balance_words = ["balance", "left", "remaining", "how much", "how many", "have"]
    if not any(k in t for k in balance_words):
        return False
        
    # Must not be a "policy" question
    policy_words = ["policy", "explain", "rule", "guideline", "sop", "what is"]
    if any(k in t for k in policy_words):
        return False
        
    return True

# Local helper imports
SNAPSHOT_PATH = os.path.join("db", "_raw_docs_snapshot.json")

# --- Configuration ---
DB_PATH = "db"
FALLBACK_PHRASE = "I do not have that information in the knowledge base."

# --- EMBEDDING MODEL ---
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


# --- LLM MODEL CONFIGURATION (ZEPHYR-7B) ---
MODEL_REPO_ID = "TheBloke/Mistral-7B-Instruct-v0.2-GGUF"
MODEL_FILE = "mistral-7b-instruct-v0.2.Q4_K_M.gguf"
MODEL_TYPE = "mistral"

# --- LLM loader / safe caller ---
def load_llm():
    """Create and return a CTransformers LLM instance."""
    print(f"[LLM] Loading model: {MODEL_REPO_ID}/{MODEL_FILE}...")
    try:
        llm = CTransformers(
            model=MODEL_REPO_ID,
            model_file=MODEL_FILE,
            model_type=MODEL_TYPE,
            config={
                "max_new_tokens": 128,
                "temperature": 0.01,
                "top_p": 0.9,
                "top_k": 40,
                "repetition_penalty": 1.15,
                "context_length": 2048,
                "threads": 2
            },
            local_files_only=True
        )
        print("[LLM] Model loaded successfully.")
        return llm
    except Exception as e:
        print("[LLM] Error loading model:", e)
        traceback.print_exc()
        raise

def call_llm(prompt: str, llm) -> str:
    """Safely call the CTransformers LLM and return the generated text."""
    try:
        print("[LLM] Calling model...")
        
        # Method 1: Try direct invocation
        try:
            result = llm.invoke(prompt)
            if isinstance(result, str) and result.strip():
                print("[LLM] Response received (invoke method)")
                return result.strip()
        except (AttributeError, TypeError):
            pass
        
        # Method 2: Try __call__ method
        try:
            result = llm(prompt)
            if isinstance(result, str) and result.strip():
                print("[LLM] Response received (__call__ method)")
                return result.strip()
        except (AttributeError, TypeError):
            pass
        
        # Method 3: Use generate method
        try:
            result = llm.generate([prompt])
        except TypeError:
            try:
                result = llm.generate(prompts=[prompt])
            except Exception:
                result = llm.generate(prompt)

        # Parse the result
        if hasattr(result, "generations"):
            gens = result.generations
            if gens and len(gens) > 0:
                if len(gens[0]) > 0 and hasattr(gens[0][0], "text"):
                    text = gens[0][0].text
                    if text and text.strip():
                        print("[LLM] Response received (generations structure)")
                        return text.strip()
        
        if isinstance(result, list) and len(result) > 0:
            first_result = result[0]
            if hasattr(first_result, "generations"):
                gens = first_result.generations
                if gens and len(gens) > 0:
                    if hasattr(gens[0], "text"):
                        text = gens[0].text
                        if text and text.strip():
                            print("[LLM] Response received (list structure)")
                            return text.strip()
            if isinstance(first_result, str) and first_result.strip():
                print("[LLM] Response received (list of strings)")
                return first_result.strip()
        
        if isinstance(result, str) and result.strip():
            print("[LLM] Response received (direct string)")
            return result.strip()
        
        print(f"[LLM] Warning: Model returned unexpected structure: {type(result)}")
        return FALLBACK_PHRASE

    except Exception as e:
        print(f"[LLM] Error calling model: {e}")
        traceback.print_exc()
        return "Error: The AI model failed to generate a response."

# --- Embeddings loader ---
_embeddings_cache = None

def load_embeddings():
    global _embeddings_cache
    if _embeddings_cache is None:
        print(f"[Embeddings] Loading embeddings model: {EMBEDDING_MODEL}...")
        _embeddings_cache = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL, 
            model_kwargs={"device": "cpu"}
        )
    else:
        print("[Embeddings] Using cached embeddings model.")
    return _embeddings_cache

# --- Snapshot fallback utilities ---
def load_snapshot(snapshot_path=SNAPSHOT_PATH):
    if not os.path.exists(snapshot_path):
        return None
    with open(snapshot_path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    docs = data.get("docs", [])
    return docs

def snapshot_retriever(query: str, docs: List[dict], top_k: int = 3, role_filter: Optional[List[str]] = None):
    """Simple word-overlap fallback retriever."""
    q_tokens = set(query.lower().split())
    scored = []
    for d in docs:
        md = d.get("metadata", {})
        role = md.get("role", "general")
        if role_filter and role not in role_filter:
            continue
        text = d.get("page_content", "")
        text_tokens = set(text.lower().split())
        score = len(q_tokens.intersection(text_tokens))
        scored.append((score, text, role))
    scored.sort(key=lambda x: x[0], reverse=True)
    selected = [t for s, t, r in scored[:top_k] if s > 0]
    return selected

# --- Main search function ---
def search_knowledge_base(query: str, user_role: str, llm) -> str:
    """Search the knowledge base with role-aware filtering."""
    print(f"[search_knowledge_base] role={user_role} query={query!r}")
    
    search_kwargs = {"k": 3}
    
    if user_role == "admin":
        print("[search_knowledge_base] Admin user: Accessing ALL roles (no filter).")
        allowed_roles_for_fallback = None
    else:
        allowed_roles_for_fallback = [user_role, "general"]
        print(f"[search_knowledge_base] Standard user: Access limited to {allowed_roles_for_fallback}.")
        search_kwargs["filter"] = {"role": {"$in": allowed_roles_for_fallback}}

    # --- Retrieve Context ---
    context_pieces = []
    if CHROMA_AVAILABLE:
        try:
            print("[search_knowledge_base] Attempting Chroma DB retrieval...")
            embeddings = load_embeddings()
            vector_store = Chroma(persist_directory=DB_PATH, embedding_function=embeddings)
            retriever = vector_store.as_retriever(search_kwargs=search_kwargs)
            results = retriever.invoke(query) 
            for r in results:
                context_pieces.append(getattr(r, "page_content", ""))
            if len(context_pieces) > 0:
                print(f"[search_knowledge_base] Retrieved {len(context_pieces)} docs from Chroma.")
        except Exception as e:
            print(f"[search_knowledge_base] Chroma retrieval error: {e}") 

    if not context_pieces:
        docs = load_snapshot()
        if docs:
            print("[search_knowledge_base] FALLBACK: Using JSON snapshot.")
            selected = snapshot_retriever(query, docs, top_k=3, role_filter=allowed_roles_for_fallback)
            if selected:
                context_pieces.extend(selected)

    if not context_pieces:
        print("--- No allowed context found. RBAC filter active. ---")
        return FALLBACK_PHRASE

    context = "\n\n".join(context_pieces).strip()
    
    if not context:
        print("--- No context found. Returning fallback phrase. ---")
        return FALLBACK_PHRASE
    
    # --- Generate Answer using LLM (ZEPHYR FORMAT) ---
    print(f"--- Context found. Passing to LLM. ---")
    
    context_with_numbers = "\n\n".join([
        f"Document {i+1}:\n{piece}" 
        for i, piece in enumerate(context_pieces)
    ])
    
    # Zephyr chat template format
    prompt_template = """<|system|>
You are a helpful company knowledge base assistant. Your job is to answer questions using the Context provided below.

Instructions:
- Read the Context carefully - multiple documents may be provided
- The documents are ranked by relevance, with Document 1 being most relevant
- If the Context contains information that answers the question, provide a clear answer
- Focus on the most relevant information to answer the specific question asked
- If the Context does not contain relevant information, say: "I do not have that information in the knowledge base."
- Be direct and helpful</s>
<|user|>
Context:
{context}

Question: {question}

Provide a clear answer based on the Context above.</s>
<|assistant|>
"""
    
    prompt = prompt_template.format(context=context_with_numbers, question=query)

    try:
        answer = call_llm(prompt, llm)
        
        if not answer or answer == "Error: The AI model failed to generate a response.":
            return FALLBACK_PHRASE
        
        # Clean up response (remove Zephyr template tokens)
        for token in ["<|system|>", "<|user|>", "<|assistant|>", "</s>"]:
            answer = answer.replace(token, "")
        answer = answer.strip()
        
        answer_lower = answer.lower()
        if "answer:" in answer_lower:
            idx = answer_lower.index("answer:")
            answer = answer[idx + 7:].strip()
        
        leakage_terms = ["context:", "question:", "instructions:"]
        if any(term in answer_lower for term in leakage_terms):
            for term in leakage_terms:
                if term in answer_lower:
                    parts = answer_lower.split(term)
                    if len(parts) > 1:
                        continue
            if any(term in answer.lower() for term in leakage_terms):
                return FALLBACK_PHRASE
        
        if "do not have" in answer_lower and "information" in answer_lower:
            return FALLBACK_PHRASE
        
        if not answer or len(answer) < 5:
            return FALLBACK_PHRASE
        
        # --- ADD SOURCE CITATIONS ---
        sources = []
        if CHROMA_AVAILABLE:
            try:
                embeddings = load_embeddings()
                vector_store = Chroma(persist_directory=DB_PATH, embedding_function=embeddings)
                retriever = vector_store.as_retriever(search_kwargs=search_kwargs)
                results = retriever.invoke(query)
                
                seen_sources = set()
                for doc in results:
                    source = doc.metadata.get("source", "")
                    if source and source not in seen_sources:
                        source_clean = source.replace("\\", "/").replace("knowledge_base/", "")
                        sources.append(source_clean)
                        seen_sources.add(source)
            except Exception:
                pass
        
        if sources and answer != FALLBACK_PHRASE:
            sources_text = "\n\n📚 **Sources:**\n" + "\n".join([f"- {s}" for s in sources[:3]])
            answer = answer + sources_text
            
        return answer.strip()
        
    except Exception as e:
        print(f"[search_knowledge_base] Error running LLM: {e}")
        traceback.print_exc()
        return "Error: Could not generate an answer from the model."

# --- Agent shim and BasicAgent implementation ---
class AgentExecutorShim:
    def __init__(self, agent, verbose: bool = False):
        self.agent = agent
        self.verbose = verbose

    def invoke(self, payload):
        try:
            input_text = payload.get("input", "")
            result = self.agent.run(input_text)
            return {"output": str(result)}
        except Exception as e:
            err = f"Agent execution error: {e}"
            if self.verbose:
                print(err)
            return {"output": err}

class BasicAgent:
    def __init__(self, rag_callable: Callable[[str], str], pto_callable: Callable[[], str]):
        self.rag_callable = rag_callable
        self.pto_callable = pto_callable

    def run(self, input_text: str) -> str:
        if is_balance_query(input_text):
            print("[Router] Matched PTO tool (balance).")
            return self.pto_callable()
        
        print("[Router] Matched RAG tool.")
        return self.rag_callable(input_text)

# --- Factory ---
def create_agent_executor(user_role: str, username: str):
    """Build and return an AgentExecutorShim around a BasicAgent."""
    print(f"[create_agent_executor] user={username} role={user_role}")
    llm = load_llm()

    def rag_callable(query_text: str):
        return search_knowledge_base(query_text, user_role, llm)

    def pto_callable():
        return get_pto_balance(username)

    agent = BasicAgent(rag_callable=rag_callable, pto_callable=pto_callable)
    shim = AgentExecutorShim(agent=agent, verbose=True)
    print("[create_agent_executor] Agent executor created successfully.")
    return shim

# --- Quick tests when run directly ---
if __name__ == "__main__":
    print("--- Running query.py agent test mode ---\n")
    agent_admin = create_agent_executor(user_role="admin", username="admin")
    
    print("\n[Test 1] PTO policy (admin):")
    result = agent_admin.invoke({"input": "What is the PTO policy?"})
    print(result["output"])
    
    print("\n[Test 2] PTO balance (admin):")
    result = agent_admin.invoke({"input": "How much PTO do I have left?"})
    print(result["output"])
    
    print("\n[Test 3] Bonus query (admin) - should use RAG:")
    result = agent_admin.invoke({"input": "What is the bonus policy?"})
    print(result["output"])