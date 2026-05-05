"""
auto_reindex.py - Automated Document Re-indexing System

This script monitors the knowledge_base directory for changes and automatically
triggers re-indexing when new files are added or existing files are modified.

Usage:
    python auto_reindex.py          # Run once
    python auto_reindex.py --watch  # Continuous monitoring mode
"""

import os
import sys
import time
import hashlib
import json
import subprocess
from pathlib import Path
from datetime import datetime
import argparse

# Configuration
KNOWLEDGE_BASE_PATH = "knowledge_base"
STATE_FILE = "reindex_state.json"
CHECK_INTERVAL = 60  # seconds (1 minute)
SUPPORTED_EXTENSIONS = [".txt", ".pdf", ".docx", ".md"]

class ReindexMonitor:
    def __init__(self, kb_path=KNOWLEDGE_BASE_PATH):
        self.kb_path = Path(kb_path)
        self.state_file = STATE_FILE
        self.current_state = {}
        self.load_state()
    
    def calculate_file_hash(self, filepath):
        """Calculate MD5 hash of a file."""
        try:
            with open(filepath, "rb") as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception as e:
            print(f"[ERROR] Failed to hash {filepath}: {e}")
            return None
    
    def scan_knowledge_base(self):
        """Scan all files in knowledge base and return their states."""
        file_states = {}
        
        if not self.kb_path.exists():
            print(f"[ERROR] Knowledge base path not found: {self.kb_path}")
            return file_states
        
        for root, dirs, files in os.walk(self.kb_path):
            # Skip hidden directories
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            
            for file in files:
                # Skip hidden files
                if file.startswith('.'):
                    continue
                
                # Check if supported file type
                ext = os.path.splitext(file)[1].lower()
                if ext not in SUPPORTED_EXTENSIONS:
                    continue
                
                filepath = Path(root) / file
                relative_path = str(filepath.relative_to(self.kb_path))
                
                # Get file info
                try:
                    stat = filepath.stat()
                    file_hash = self.calculate_file_hash(filepath)
                    
                    file_states[relative_path] = {
                        "hash": file_hash,
                        "size": stat.st_size,
                        "modified": stat.st_mtime,
                        "last_checked": time.time()
                    }
                except Exception as e:
                    print(f"[ERROR] Failed to process {filepath}: {e}")
        
        return file_states
    
    def load_state(self):
        """Load previous state from file."""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r") as f:
                    self.current_state = json.load(f)
                print(f"[INFO] Loaded state for {len(self.current_state)} files")
            except Exception as e:
                print(f"[ERROR] Failed to load state file: {e}")
                self.current_state = {}
        else:
            print("[INFO] No previous state found. This is the first run.")
            self.current_state = {}
    
    def save_state(self, state):
        """Save current state to file."""
        try:
            with open(self.state_file, "w") as f:
                json.dump(state, f, indent=2)
            print(f"[INFO] Saved state for {len(state)} files")
        except Exception as e:
            print(f"[ERROR] Failed to save state: {e}")
    
    def detect_changes(self, new_state):
        """Detect changes between old and new states."""
        added = []
        modified = []
        deleted = []
        
        # Find added and modified files
        for filepath, info in new_state.items():
            if filepath not in self.current_state:
                added.append(filepath)
            elif info["hash"] != self.current_state[filepath].get("hash"):
                modified.append(filepath)
        
        # Find deleted files
        for filepath in self.current_state:
            if filepath not in new_state:
                deleted.append(filepath)
        
        return {
            "added": added,
            "modified": modified,
            "deleted": deleted
        }
    
    def trigger_reindexing(self):
        """Trigger the ingestion script to rebuild the database."""
        print("\n" + "="*60)
        print(f"[REINDEX] Starting re-indexing at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)
        
        try:
            # Run ingest.py
            result = subprocess.run(
                [sys.executable, "ingest.py"],
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )
            
            if result.returncode == 0:
                print("[SUCCESS] Re-indexing completed successfully!")
                print(result.stdout)
                return True
            else:
                print("[ERROR] Re-indexing failed!")
                print("STDOUT:", result.stdout)
                print("STDERR:", result.stderr)
                return False
                
        except subprocess.TimeoutExpired:
            print("[ERROR] Re-indexing timed out after 10 minutes")
            return False
        except Exception as e:
            print(f"[ERROR] Failed to trigger re-indexing: {e}")
            return False
    
    def check_once(self):
        """Perform a single check for changes."""
        print(f"\n[SCAN] Scanning knowledge base: {self.kb_path}")
        new_state = self.scan_knowledge_base()
        
        if not new_state:
            print("[WARNING] No files found in knowledge base")
            return False
        
        changes = self.detect_changes(new_state)
        
        # Report changes
        has_changes = any([changes["added"], changes["modified"], changes["deleted"]])
        
        if has_changes:
            print("\n[CHANGES DETECTED]")
            
            if changes["added"]:
                print(f"  ✅ Added ({len(changes['added'])}):")
                for f in changes["added"][:5]:  # Show first 5
                    print(f"    - {f}")
                if len(changes["added"]) > 5:
                    print(f"    ... and {len(changes['added']) - 5} more")
            
            if changes["modified"]:
                print(f"  ✏️  Modified ({len(changes['modified'])}):")
                for f in changes["modified"][:5]:
                    print(f"    - {f}")
                if len(changes["modified"]) > 5:
                    print(f"    ... and {len(changes['modified']) - 5} more")
            
            if changes["deleted"]:
                print(f"  ❌ Deleted ({len(changes['deleted'])}):")
                for f in changes["deleted"][:5]:
                    print(f"    - {f}")
                if len(changes["deleted"]) > 5:
                    print(f"    ... and {len(changes['deleted']) - 5} more")
            
            # Trigger re-indexing
            if self.trigger_reindexing():
                self.save_state(new_state)
                self.current_state = new_state
                return True
            else:
                print("[ERROR] Not updating state due to re-indexing failure")
                return False
        else:
            print("[INFO] No changes detected")
            # Update state anyway to refresh timestamps
            self.save_state(new_state)
            self.current_state = new_state
            return False
    
    def watch(self, interval=CHECK_INTERVAL):
        """Continuously monitor for changes."""
        print("\n" + "="*60)
        print("🔍 AUTO-REINDEX MONITOR STARTED")
        print("="*60)
        print(f"Watching: {self.kb_path.absolute()}")
        print(f"Check interval: {interval} seconds")
        print("Press Ctrl+C to stop\n")
        
        try:
            while True:
                self.check_once()
                print(f"\n[WAITING] Next check in {interval} seconds...")
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\n\n[STOP] Monitor stopped by user")
            print("="*60)

def main():
    parser = argparse.ArgumentParser(
        description="Automated document re-indexing for AI ChatOps Assistant"
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Run in continuous monitoring mode"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=CHECK_INTERVAL,
        help=f"Check interval in seconds (default: {CHECK_INTERVAL})"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-indexing even if no changes detected"
    )
    
    args = parser.parse_args()
    
    monitor = ReindexMonitor()
    
    if args.force:
        print("[FORCE] Forcing re-indexing...")
        monitor.trigger_reindexing()
        # Update state after force reindex
        new_state = monitor.scan_knowledge_base()
        monitor.save_state(new_state)
    elif args.watch:
        monitor.watch(interval=args.interval)
    else:
        monitor.check_once()

if __name__ == "__main__":
    main()