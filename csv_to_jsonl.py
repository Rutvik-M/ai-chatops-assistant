# file: csv_to_jsonl.py
import pandas as pd
import json

df = pd.read_csv("chat_log.csv", dtype=str)
with open("chat_log.jsonl", "w", encoding="utf8") as out:
    for _, row in df.iterrows():
        obj = {
            "timestamp": row.get("timestamp", ""),
            "user": row.get("user", ""),
            "query": row.get("query", ""),
            "response": row.get("response", ""),
            "feedback": row.get("feedback", "N/A")
        }
        out.write(json.dumps(obj, ensure_ascii=False) + "\n")
print("Converted chat_log.csv -> chat_log.jsonl")
