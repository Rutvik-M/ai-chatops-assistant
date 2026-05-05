import os
from ctransformers import AutoModelForCausalLM

def load_llm():
    model_repo = "TheBloke/Zephyr-7B-beta-GGUF"
    model_file = "zephyr-7b-beta.Q4_K_M.gguf"
    EMBEDDING_MODEL = "BAAI/bge-large-en-v1.5"



    print("=== Testing Mistral Loader ===")

    print(f"[LLM] Loading model:\n  Repo: {model_repo}\n  File: {model_file}\n")

    llm = AutoModelForCausalLM.from_pretrained(
        model_repo,
        model_file=model_file,
        model_type="mistral",
        gpu_layers=0,              # CPU only
        context_length=4096,
        threads=8
    )

    print("\n=== Model Loaded Successfully! ===")
    print("Model object:", llm)
    print("=================================\n")

    return llm


if __name__ == "__main__":
    load_llm()
