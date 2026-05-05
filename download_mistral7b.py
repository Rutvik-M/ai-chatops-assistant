import os
from huggingface_hub import hf_hub_download

REPO_ID = "TheBloke/Mistral-7B-Instruct-v0.2-GGUF"
MODEL_FILENAME = "mistral-7b-instruct-v0.2.Q4_K_M.gguf"
DEST_FOLDER = "models"

os.makedirs(DEST_FOLDER, exist_ok=True)

print(f"Downloading {MODEL_FILENAME} from {REPO_ID} to ./{DEST_FOLDER}/ ...")

local_path = hf_hub_download(
    repo_id=REPO_ID,
    filename=MODEL_FILENAME,
    cache_dir=DEST_FOLDER,
    local_dir=DEST_FOLDER,
    local_dir_use_symlinks=False
)

print(f"✅ Downloaded to: {local_path}")
