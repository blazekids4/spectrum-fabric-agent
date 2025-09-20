#!/usr/bin/env python3
"""
Batch-run Fabric Data Agent queries from a questions JSON file and write a markdown report.

Usage:
  - Configure TENANT_ID and DATA_AGENT_URL via environment variables or edit below
  - Ensure `charter/backend/data_transcripts/questions_only.json` exists
  - Run: python fabric_agent_batch_report.py

Outputs:
  - charter/backend/data_transcripts/questions_report.md

The script is tolerant when credentials are missing: it will write the prompts and note that responses were not run.
"""
import os
import json
import datetime
from fabric_data_agent_client import FabricDataAgentClient

BASE_DIR = os.path.dirname(__file__)
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
DATA_DIR = os.path.join(BASE_DIR, "data_transcripts")
QUESTIONS_PATH = os.path.join(DATA_DIR, "questions_only.json")
OUTPUT_MD = os.path.join(OUTPUT_DIR, "questions_report.md")

# Configuration from env
TENANT_ID = os.getenv("TENANT_ID", "your-tenant-id-here")
DATA_AGENT_URL = os.getenv("DATA_AGENT_URL", "your-data-agent-url-here")


def load_questions(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def init_client():
    if TENANT_ID == "your-tenant-id-here" or DATA_AGENT_URL == "your-data-agent-url-here":
        return None
    return FabricDataAgentClient(tenant_id=TENANT_ID, data_agent_url=DATA_AGENT_URL)


def ask_agent(client, prompt):
    if client is None:
        return None
    try:
        return client.ask(prompt)
    except Exception as e:
        return f"ERROR: {e}"


def write_report(entries, path):
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# Fabric Data Agent Questions Report\n")
        f.write(f"Generated: {datetime.datetime.utcnow().isoformat()}Z\n\n")
        for idx, entry in enumerate(entries, start=1):
            f.write(f"## {idx}. Question\n\n")
            f.write(f"**Prompt:** {entry['question']}\n\n")
            f.write("**Response:**\n\n")
            if entry.get("response") is None:
                f.write("_No response (client not configured or dry run)._|\n\n")
            else:
                # If the response is a string or dict-like, stringify it
                resp = entry['response']
                if isinstance(resp, dict) or isinstance(resp, list):
                    try:
                        f.write("```")
                        f.write(json.dumps(resp, indent=2))
                        f.write("```\n\n")
                    except Exception:
                        f.write(str(resp) + "\n\n")
                else:
                    f.write(str(resp) + "\n\n")


def main():
    questions = load_questions(QUESTIONS_PATH)
    client = init_client()

    report_entries = []
    for q in questions:
        prompt = q
        response = ask_agent(client, prompt)
        report_entries.append({"question": prompt, "response": response})
        print(f"Processed: {prompt[:60]}{'...' if len(prompt)>60 else ''}")

    write_report(report_entries, OUTPUT_MD)
    print(f"Report written to: {OUTPUT_MD}")


if __name__ == '__main__':
    main()
