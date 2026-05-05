from huggingface_hub import hf_hub_download
import os


# Match the model in query.py
MODEL_REPO_ID = "TheBloke/Zephyr-7B-beta-GGUF"
MODEL_FILE = "zephyr-7b-beta.Q4_K_M.gguf"


# Set this to avoid the symlink warning
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"


print(f"Downloading model: {MODEL_REPO_ID}")
print(f"File: {MODEL_FILE}")
print("This may take 10-20 minutes...")
print(f"Size: ~4.5GB (Q4_K_M quantization)\n")


try:
    hf_hub_download(
        repo_id=MODEL_REPO_ID,
        filename=MODEL_FILE,
        local_files_only=False
    )
    print("\n✅ Model file downloaded successfully to Hugging Face cache.")
    print(f"Location: ~/.cache/huggingface/hub/models--TheBloke--Zephyr-7B-beta-GGUF/")
except Exception as e:
    print(f"\n❌ Download failed: {e}")
    print("Troubleshooting:")
    print("1. Check internet connection")
    print("2. Ensure sufficient disk space (5GB+)")
    print("3. Try again in a few minutes")


print("\n" + "="*60)
print("Next steps:")
print("1. Place your documents in knowledge_base/[role]/")
print("2. Run: python ingest.py")
print("3. Run: streamlit run app.py")
print("="*60)
