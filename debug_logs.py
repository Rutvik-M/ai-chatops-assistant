"""
Debug script to check what's in your log files
Run this to see the actual timestamp format
"""

import os
import json
import pandas as pd

print("=" * 70)
print("LOG FILE DIAGNOSTIC TOOL")
print("=" * 70)

# Check JSONL file
if os.path.exists("chat_log.jsonl"):
    print("\n✅ Found chat_log.jsonl")
    print("-" * 70)
    
    with open("chat_log.jsonl", "r", encoding="utf8") as fh:
        lines = fh.readlines()
        print(f"Total lines: {len(lines)}")
        
        if lines:
            print("\n📋 First 3 entries:")
            for i, line in enumerate(lines[:3], 1):
                try:
                    obj = json.loads(line.strip())
                    print(f"\nEntry {i}:")
                    print(f"  Timestamp: {obj.get('timestamp', 'MISSING')}")
                    print(f"  User: {obj.get('user', 'MISSING')}")
                    print(f"  Query: {obj.get('query', 'MISSING')[:50]}...")
                    print(f"  Raw timestamp type: {type(obj.get('timestamp'))}")
                except Exception as e:
                    print(f"  Error parsing line {i}: {e}")
            
            print("\n" + "-" * 70)
            print("🔍 Analyzing ALL timestamps:")
            
            timestamps = []
            for line in lines:
                try:
                    obj = json.loads(line.strip())
                    ts = obj.get('timestamp')
                    if ts:
                        timestamps.append(ts)
                except:
                    pass
            
            print(f"Total timestamps found: {len(timestamps)}")
            if timestamps:
                print(f"First timestamp: {timestamps[0]}")
                print(f"Last timestamp: {timestamps[-1]}")
                
                # Check if they look like dates
                first_ts_str = str(timestamps[0])
                if 'T' in first_ts_str or '-' in first_ts_str:
                    print("✅ Timestamps appear to contain date information")
                else:
                    print("❌ Timestamps may be missing date information")
                    print(f"   Format looks like: {first_ts_str}")
        else:
            print("⚠️ File is empty")
else:
    print("\n❌ chat_log.jsonl not found")

# Check CSV file
if os.path.exists("chat_log.csv"):
    print("\n" + "=" * 70)
    print("✅ Found chat_log.csv")
    print("-" * 70)
    
    try:
        df = pd.read_csv("chat_log.csv")
        print(f"Total rows: {len(df)}")
        print(f"Columns: {list(df.columns)}")
        
        if 'timestamp' in df.columns:
            print(f"\n📋 First 5 timestamps:")
            print(df['timestamp'].head())
            
            print(f"\n📊 Timestamp statistics:")
            print(f"  Non-null: {df['timestamp'].notna().sum()}/{len(df)}")
            print(f"  Unique: {df['timestamp'].nunique()}")
        else:
            print("❌ No 'timestamp' column found!")
            
    except Exception as e:
        print(f"❌ Error reading CSV: {e}")
else:
    print("\n❌ chat_log.csv not found")

print("\n" + "=" * 70)
print("RECOMMENDATIONS:")
print("=" * 70)

if os.path.exists("chat_log.jsonl") or os.path.exists("chat_log.csv"):
    print("""
1. Check if timestamps have BOTH date and time (e.g., 2025-11-19T10:30:45)
2. If timestamps only show time (e.g., 23:59:59), the logging is broken
3. If no timestamp column exists, check app.py logging function
4. After fixing app.py, delete old logs and create new ones
""")
else:
    print("""
❌ No log files found!

To create logs:
1. Run: streamlit run app.py
2. Login and ask some questions
3. Logs will be created automatically
4. Then run analytics again
""")

print("=" * 70)