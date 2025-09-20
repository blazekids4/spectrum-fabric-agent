"""
Multi-LLM (Agent) orchestrator for Fabric Data Agent

This script implements a simple multi-agent sequence:
 - IntentAgent: determines which supplemental data sources to call (e.g. transcript CSV)
 - DataSourceManager: fetches contextual snippets from selected data sources
 - Orchestrator: combines the original user query with supplemental context and calls
   the Fabric Data Agent client (FabricDataAgentClient) to get the final answer.

Notes:
 - This is intentionally lightweight: it uses rule-based intent detection with an
   optional LLM fallback (if OPENAI_API_KEY is set).
 - The transcript CSV handler looks in the local `data_transcripts` directory and
   returns either matching rows or a short head preview.
"""

import os
import csv
import glob
import re
import time
import json
from typing import List, Dict, Optional

# Local import - uses the FabricDataAgentClient implemented in this repo
from fabric_data_agent_client import FabricDataAgentClient

# Optional LLM for intent fallback
try:
    from openai import OpenAI
except Exception:
    OpenAI = None

from charter_agent import TelecomThreeAgentSystem


class IntentAgent:
    """Determines which supplemental data sources should be consulted for a query.

    The detection is rule-based (keywords). If an OPENAI_API_KEY is present and
    the rule-based result is ambiguous, an LLM-based fallback can be used.
    """

    TRANSCRIPT_KEYWORDS = [
        "transcript",
        "conversation",
        "meeting",
        "call",
        "utterance",
        "speaker",
        "dialog",
        "dialogue",
    ]

    WEB_KEYWORDS = ["web", "google", "bing", "search", "news", "article"]

    KNOWLEDGE_KEYWORDS = ["kb", "knowledge", "wiki", "documentation", "docs"]

    def __init__(self, openai_api_key: Optional[str] = None):
        self.openai_api_key = openai_api_key
        if openai_api_key and OpenAI is None:
            print("⚠️ openai package not available; LLM fallback will be disabled")
            self.openai_api_key = None

    def detect_sources(self, query: str) -> List[str]:
        """Return a list of source ids (e.g. ['transcript','web']) recommended for this query."""
        q = query.lower()
        sources = set()

        for kw in self.TRANSCRIPT_KEYWORDS:
            if kw in q:
                sources.add("transcript")
                break

        for kw in self.WEB_KEYWORDS:
            if kw in q:
                sources.add("web")
                break

        for kw in self.KNOWLEDGE_KEYWORDS:
            if kw in q:
                sources.add("knowledgebase")
                break

        # If none detected, and LLM available, use LLM to classify intent
        if not sources and self.openai_api_key and OpenAI is not None:
            try:
                llm = OpenAI(api_key=self.openai_api_key)
                prompt = (
                    "You are an intent classifier. Given a user question, reply with a JSON array "
                    "of supplemental source identifiers to consult from the set: [\"transcript\", "
                    "\"web\", \"knowledgebase\"]. Only return the JSON array.\n\nQuestion: \""
                    + query.replace('"', '\\"')
                    + "\"\n"
                )

                # Try a lightweight chat/response where available
                try:
                    resp = llm.responses.create(
                        model="gpt-4o-mini",  # fallback-friendly model id; may be changed by user
                        input=prompt,
                        max_output_tokens=200,
                    )
                    text = ''
                    # responses SDK may return a variety of shapes -> handle common cases
                    if hasattr(resp, 'output') and resp.output:
                        # The textual content may be in resp.output_text or nested
                        text = getattr(resp, 'output_text', None) or str(resp.output)
                    else:
                        text = str(resp)

                    # Try to extract a JSON array from text
                    json_match = re.search(r'(\[[\s\S]*?\])', text)
                    if json_match:
                        arr = json.loads(json_match.group(1))
                        for a in arr:
                            if a in ("transcript", "web", "knowledgebase"):
                                sources.add(a)
                except Exception as e:
                    print(f"⚠️ LLM fallback failed: {e}")
            except Exception as e:
                print(f"⚠️ Cannot create OpenAI client for intent fallback: {e}")

        # Default to transcript if nothing else found - safe fallback for this repo
        if not sources:
            sources.add("transcript")

        return list(sources)


class DataSourceManager:
    """Provides access to supplemental data sources (currently: transcript CSVs).

    The transcript CSV handler searches for .csv files in the `data_transcripts`
    directory (relative to this file's location), retrieves either the head
    of the file or rows that match terms from the query, and formats a compact
    markdown snippet suitable to be appended to a question.
    """

    def __init__(self, base_dir: Optional[str] = None):
        # Determine default data_transcripts directory path
        if base_dir:
            self.base_dir = base_dir
        else:
            # current file dir -> parent is backend folder in this repo
            self.base_dir = os.path.join(os.path.dirname(__file__), "data_transcripts")

    def _list_csv_files(self) -> List[str]:
        pattern = os.path.join(self.base_dir, "*.csv")
        files = glob.glob(pattern)
        # Sort by modification time descending
        files.sort(key=lambda p: os.path.getmtime(p), reverse=True)
        return files

    def transcript_snippet(self, query: str, max_rows: int = 20) -> str:
        """Return a compact markdown snippet from the most relevant transcript CSV.

        Strategy:
        - Pick the most recently modified CSV
        - Scan rows for keywords from the query; if matches found, return up to
          `max_rows` matching lines formatted as a small markdown table
        - If no matches, return the header plus the first N rows as a preview
        """
        files = self._list_csv_files()
        if not files:
            return "(no transcript CSV files found)"

        csv_path = files[0]
        try:
            with open(csv_path, newline='', encoding='utf-8') as fh:
                reader = csv.DictReader(fh)
                headers = reader.fieldnames or []

                # Build simple keyword set from query
                keywords = [t.lower() for t in re.findall(r"\w+", query) if len(t) > 2]

                matched_rows = []
                preview_rows = []

                for row in reader:
                    row_text = ' '.join([str(v) for v in row.values() if v])
                    if any(k in row_text.lower() for k in keywords):
                        matched_rows.append(row)
                        if len(matched_rows) >= max_rows:
                            break
                    if len(preview_rows) < max_rows:
                        preview_rows.append(row)

                # Prefer matched rows
                chosen = matched_rows if matched_rows else preview_rows

                # Format as markdown table (header + up to 10 rows)
                if not chosen:
                    return f"(transcript file {os.path.basename(csv_path)} present but empty)"

                out_lines = []
                out_lines.append(f"**Transcript file:** {os.path.basename(csv_path)}")
                # Limit columns for snippet readability
                show_headers = headers[:6]
                out_lines.append("| " + " | ".join(show_headers) + " |")
                out_lines.append("|" + "---|" * len(show_headers))

                for r in chosen[:10]:
                    vals = [str(r.get(h, '')).replace('\n', ' ')[:120] for h in show_headers]
                    out_lines.append("| " + " | ".join(vals) + " |")

                out_lines.append(f"\n(Showing {min(len(chosen),10)} rows from {os.path.basename(csv_path)})")
                return "\n".join(out_lines)

        except Exception as e:
            return f"(error reading transcript CSV: {e})"


class AIFoundryAdapter:
    """Adapter to run tasks using the TelecomThreeAgentSystem (AI Foundry projects & agents).

    This encapsulates the context management used in `charter_agent.TelecomThreeAgentSystem`
    and exposes simple methods to run web search and table reading tasks via the Agents
    API. Initialization will be best-effort and mark the adapter unavailable if any
    required environment configuration is missing.
    """

    def __init__(self):
        try:
            self.system = TelecomThreeAgentSystem()
            self.available = True
        except Exception as e:
            print(f"⚠️ AI Foundry adapter init failed: {e}")
            self.system = None
            self.available = False

    def run_web_search(self, context: str) -> str:
        if not self.available:
            return "(AI Foundry unavailable)"

        try:
            with self.system.agent_project_client:
                with self.system.agent_project_client.agents as agents_client:
                    # Ensure agents exist
                    self.system.table_reader_agent_id = self.system.get_or_create_table_reader_agent(agents_client)
                    self.system.web_search_agent_id = self.system.get_or_create_web_search_agent(agents_client)

                    # Run web search task
                    return self.system.web_search_task(agents_client, context)
        except Exception as e:
            return f"(AI Foundry web search failed: {e})"

    def run_table_reader(self, table_data: str, query: str) -> str:
        if not self.available:
            return "(AI Foundry unavailable)"

        try:
            with self.system.agent_project_client:
                with self.system.agent_project_client.agents as agents_client:
                    # Ensure agents exist
                    self.system.table_reader_agent_id = self.system.get_or_create_table_reader_agent(agents_client)

                    # Run table reader task
                    return self.system.table_reader_task(agents_client, table_data, query)
        except Exception as e:
            return f"(AI Foundry table reader failed: {e})"


class MultiAgentOrchestrator:
    """Coordinates intent detection, data gathering, and Fabric Data Agent calls."""

    def __init__(self, tenant_id: str, data_agent_url: str, openai_api_key: Optional[str] = None, 
                use_ai_foundry: bool = True, skip_fabric: bool = False):
        self.intent_agent = IntentAgent(openai_api_key=openai_api_key)
        self.data_manager = DataSourceManager()
        self.skip_fabric = skip_fabric

        # Initialize FabricDataAgentClient lazily (auth is interactive) - create on first use
        self.tenant_id = tenant_id
        self.data_agent_url = data_agent_url
        self._fabric_client = None

        # AI Foundry adapter: optional, enabled via flag and available environment
        self.ai_adapter = None
        if use_ai_foundry:
            # Try to initialize adapter; it will mark itself unavailable if config missing
            self.ai_adapter = AIFoundryAdapter()

    def _get_fabric_client(self) -> FabricDataAgentClient:
        if self._fabric_client is None:
            self._fabric_client = FabricDataAgentClient(
                tenant_id=self.tenant_id,
                data_agent_url=self.data_agent_url
            )
        return self._fabric_client

    def run(self, query: str, timeout: int = 120) -> Dict:
        print(f"\n[Orchestrator] Starting multi-agent run for query: {query}\n")

        # 1) Determine which sources to consult
        sources = self.intent_agent.detect_sources(query)
        print(f"[Orchestrator] Detected sources: {sources}")

        # 2) Gather supplemental context
        supplemental_blocks = []
        transcript_snippet = None
        if 'transcript' in sources:
            snippet = self.data_manager.transcript_snippet(query)
            transcript_snippet = snippet
            supplemental_blocks.append("## Transcript snippet\n" + snippet)

        # Check if AI Foundry adapter is available
        ai_foundry_available = self.ai_adapter and self.ai_adapter.available
        
        # Use AI Foundry for table analysis if available
        table_analysis_result = None
        if ai_foundry_available:
            # Try to locate CSV data to use with table reader agent
            csv_files = self.data_manager._list_csv_files()
            if csv_files:
                try:
                    # Read the CSV file for table analysis
                    with open(csv_files[0], 'r', encoding='utf-8') as file:
                        table_data = file.read()
                    
                    print("[Orchestrator] Running AI Foundry table reader agent...\n")
                    table_analysis_result = self.ai_adapter.run_table_reader(table_data, query)
                    if table_analysis_result and "failed" not in table_analysis_result.lower():
                        supplemental_blocks.append("## Table analysis (AI Foundry)\n" + table_analysis_result)
                except Exception as e:
                    print(f"[Orchestrator] Table analysis failed: {e}")
        
        # Use AI Foundry web agent if requested and adapter available
        web_results = None
        if 'web' in sources:
            if ai_foundry_available:
                # Create a search context that merges transcript snippet (if any) with query
                search_context = "User query:\n" + query
                if transcript_snippet:
                    search_context += "\n\nTranscript context:\n" + transcript_snippet
                if table_analysis_result:
                    search_context += "\n\nTable analysis:\n" + table_analysis_result

                print("[Orchestrator] Running AI Foundry web search agent...\n")
                web_results = self.ai_adapter.run_web_search(search_context)
                supplemental_blocks.append("## Web search results (AI Foundry)\n" + web_results)
            else:
                supplemental_blocks.append("## Web: (web lookup requested)\n(implement web lookup in DataSourceManager)")

        # Knowledgebase via AI Foundry: reuse web agent as placeholder or implement KB search
        if 'knowledgebase' in sources:
            if ai_foundry_available:
                kb_context = "Knowledge lookup for query:\n" + query
                if transcript_snippet:
                    kb_context += "\n\nTranscript context:\n" + transcript_snippet
                print("[Orchestrator] Running AI Foundry knowledge/web agent...\n")
                kb_results = self.ai_adapter.run_web_search(kb_context)
                supplemental_blocks.append("## Knowledgebase results (AI Foundry)\n" + kb_results)
            else:
                supplemental_blocks.append("## Knowledgebase: (kb lookup requested)\n(implement KB lookup in DataSourceManager)")

        # Limit total size of supplemental context
        combined_context = "\n\n".join(supplemental_blocks)
        if len(combined_context) > 4000:
            combined_context = combined_context[:4000] + "\n\n...(truncated)"

        # If we have AI Foundry available and obtained results, use the reasoning model for final analysis
        final_answer = None
        if ai_foundry_available and (table_analysis_result or web_results):
            try:
                print("[Orchestrator] Running AI Foundry reasoning analysis...\n")
                
                # Prepare the analysis inputs
                reasoning_input = query
                if table_analysis_result:
                    final_answer = self.ai_adapter.system.reasoning_analysis(
                        question=query,
                        table_result=table_analysis_result,
                        web_results=web_results
                    )
                    print("[Orchestrator] AI Foundry reasoning complete\n")
            except Exception as e:
                print(f"[Orchestrator] AI Foundry reasoning failed: {e}")
                final_answer = None

        # 3) Construct the final question for the Fabric Data Agent
        combined_question = query
        if combined_context.strip():
            combined_question = (
                "Context:\n" + combined_context + "\n\nUser question:\n" + query
            )

        # 4) Call the Fabric Data Agent if we don't have a final answer from AI Foundry
        if not final_answer and not self.skip_fabric:
            fabric_client = self._get_fabric_client()
            print("[Orchestrator] Sending combined question to Fabric Data Agent...\n")
            final_answer = fabric_client.ask(combined_question, timeout=timeout)
        elif not final_answer and self.skip_fabric:
            print("[Orchestrator] Skip Fabric flag set and no AI Foundry result available.")
            final_answer = "No answer available. AI Foundry did not provide a result and Fabric Data Agent was skipped."

        # Return a structured result
        result = {
            "query": query,
            "detected_sources": sources,
            "supplemental_context": combined_context,
            "answer": final_answer,
            "timestamp": time.time(),
            "source": "ai_foundry_reasoning" if ai_foundry_available and (table_analysis_result or web_results) else "fabric_data_agent"
        }

        return result


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Multi-LLM Fabric Data Agent orchestrator")
    parser.add_argument('--tenant-id', default=os.getenv('TENANT_ID', ''), help='Azure tenant id')
    parser.add_argument('--data-agent-url', default=os.getenv('DATA_AGENT_URL', ''), help='Fabric Data Agent base URL')
    parser.add_argument('--openai-api-key', default=os.getenv('OPENAI_API_KEY', ''), help='Optional OpenAI API key for intent agent fallback')
    parser.add_argument('--query', default='', help='Question to ask the orchestrator')
    parser.add_argument('--use-ai-foundry', action='store_true', help='Enable AI Foundry agents (telecom three-agent system)')
    parser.add_argument('--skip-fabric', action='store_true', help='Skip Fabric Data Agent call and use AI Foundry exclusively when available')
    args = parser.parse_args()

    if not args.tenant_id or not args.data_agent_url:
        if args.use_ai_foundry and args.skip_fabric:
            print("Running with AI Foundry only mode - no Fabric Data Agent will be used")
        else:
            print("Please set TENANT_ID and DATA_AGENT_URL via environment variables or command-line flags.")
            return

    if not args.query:
        print("Enter an interactive question (empty line to quit):")
        orchestrator = MultiAgentOrchestrator(
            args.tenant_id, 
            args.data_agent_url, 
            openai_api_key=args.openai_api_key, 
            use_ai_foundry=args.use_ai_foundry,
            skip_fabric=args.skip_fabric
        )
        try:
            while True:
                q = input('\n> ').strip()
                if not q:
                    break
                res = orchestrator.run(q)
                print('\n' + '='*60)
                print(f"Answer (Source: {res.get('source', 'unknown')}):")
                print(res.get('answer'))
                print('='*60 + '\n')
        except KeyboardInterrupt:
            print('\nCancelled by user')
    else:
        orchestrator = MultiAgentOrchestrator(
            args.tenant_id, 
            args.data_agent_url, 
            openai_api_key=args.openai_api_key, 
            use_ai_foundry=args.use_ai_foundry,
            skip_fabric=args.skip_fabric
        )
        res = orchestrator.run(args.query)
        print(json.dumps(res, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
