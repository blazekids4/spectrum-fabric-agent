# two_agent_competitor_insights.py
# --------------------------------
# Purpose: Deterministic numbers (Agent A plan -> pandas execution) + Narrative (Agent B)
# Matches the style of your reference: metrics, env model routing, HTML/CSV reports.

import os, json, time, argparse, csv, re
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

import pandas as pd

from dotenv import load_dotenv
load_dotenv()

from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from opentelemetry import trace

# Optional: if you have this module in your repo, keep it. Otherwise, no-op the telemetry.
try:
    from telemetry import configure_tracing
except Exception:
    def configure_tracing(*args, **kwargs): pass

tracer = trace.get_tracer(__name__)

# ---------------------------
# Metrics (same pattern)
# ---------------------------
class SearchMetrics:
    def __init__(self):
        self.start_time = time.time()
        self.first_token_time = None
        self.completion_time = None
        self.tokens_in = 0
        self.tokens_out = 0
        self.total_tokens = 0
        self.total_time = None
        self.time_to_first_token = None

    def complete(self):
        self.completion_time = time.time()
        self.total_time = self.completion_time - self.start_time
        if self.first_token_time:
            self.time_to_first_token = self.first_token_time - self.start_time

    def to_dict(self) -> Dict:
        return {
            "total_time": round(self.total_time, 2) if self.total_time else None,
            "time_to_first_token": round(self.time_to_first_token, 2) if self.time_to_first_token else None,
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "total_tokens": self.total_tokens,
        }

# ---------------------------
# Data structures
# ---------------------------
@dataclass
class AgentAPlan:
    ok: bool
    question: str
    query_type: str
    filters: Dict[str, Any]
    computations: List[str]
    projections: List[str]
    notes: List[str]

@dataclass
class AgentAResult:
    plan: AgentAPlan
    dataframe_json: str  # computed result rows as JSON (list[dict])
    derived_json: str    # totals/avgs/diffs/ranks json string

@dataclass
class AgentBInsight:
    headline: str
    insights: List[str]
    actions: List[str]
    caveat: str

# ---------------------------
# Prompts
# ---------------------------
AGENT_A_SYSTEM = """You are Agent A (SQL/Data Planner).
Return ONLY a strict JSON plan for executing the user’s question on ONE table with columns:
[Week, Brand, Mentions, Promotions, SwitchesTo, SwitchesFrom].

Rules:
- No prose. Output ONLY valid JSON with keys:
  ok (bool), question (str), query_type (lookup|aggregate|compare|trend|topn|filter),
  filters: {weeks: [..], brands: [..], conditions: "..."}, computations: ["sum","avg","diff","rank"...],
  projections: list of columns to return, notes: list of strings for disambiguation.
- Be conservative. If ambiguous, choose the narrowest interpretation and note it.
- Never invent numbers or results; you only plan the query.
"""

AGENT_A_USER_TMPL = """Question: {question}

Return ONLY the JSON with this schema:
{{
  "ok": true,
  "question": "...",
  "query_type": "...",
  "filters": {{"weeks": [], "brands": [], "conditions": ""}},
  "computations": [],
  "projections": [],
  "notes": []
}}
"""

AGENT_B_SYSTEM = """You are Agent B (Insight/Narrative).
Use ONLY:
- the original user question,
- Agent A's JSON plan,
- the executed numeric result (rows) and derived metrics.

Never invent new numbers. If needed data is missing, ask precisely for a re-run specifying the missing field.

Output JSON with:
{
  "headline": "1–2 sentence exec summary with cited numbers",
  "insights": ["3–5 bullets with inline numbers from the result/derived"],
  "actions": ["2–3 concrete next steps"],
  "caveat": "1 caveat/assumption"
}
"""

AGENT_B_USER_TMPL = """User Question: {question}

AGENT_A_PLAN_JSON:
{plan_json}

EXECUTED_RESULT_ROWS_JSON:
{rows_json}

DERIVED_JSON:
{derived_json}

Produce ONLY the JSON object with keys: headline, insights, actions, caveat.
"""

# ---------------------------
# LLM helpers
# ---------------------------
def get_llm_clients() -> Tuple[AIProjectClient, Any]:
    """
    Returns (project_client, openai_client) using MODEL_ROUTER_ENDPOINT.
    """
    endpoint = os.environ.get("MODEL_ROUTER_ENDPOINT")
    if not endpoint:
        raise ValueError("MODEL_ROUTER_ENDPOINT is required")
    project_client = AIProjectClient(endpoint=endpoint, credential=DefaultAzureCredential())
    openai_client = project_client.get_openai_client(api_version="2024-12-01-preview")
    return project_client, openai_client

def chat_json(openai_client, model: str, system: str, user: str, temperature: float = 0.0) -> Tuple[Dict, SearchMetrics]:
    m = SearchMetrics()
    resp = openai_client.chat.completions.create(
        model=model,
        messages=[{"role":"system","content":system},
                  {"role":"user","content":user}],
        temperature=temperature,
    )
    m.complete()
    if hasattr(resp, "usage"):
        m.tokens_in = getattr(resp.usage, "prompt_tokens", 0)
        m.tokens_out = getattr(resp.usage, "completion_tokens", 0)
        m.total_tokens = getattr(resp.usage, "total_tokens", 0)
    text = resp.choices[0].message.content.strip()
    try:
        return json.loads(text), m
    except Exception:
        # if model wrapped code fences, strip them and retry
        cleaned = re.sub(r"^```(?:json)?|```$", "", text, flags=re.MULTILINE).strip()
        return json.loads(cleaned), m

# ---------------------------
# Execution engine (pandas)
# ---------------------------
def execute_plan_on_df(df: pd.DataFrame, plan: AgentAPlan) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    qtype = plan.query_type
    result = df.copy()

    # filters
    weeks = set(plan.filters.get("weeks", []) or [])
    brands = set(plan.filters.get("brands", []) or [])
    cond = (plan.filters.get("conditions") or "").strip().lower()

    if weeks:
        result = result[result["Week"].isin(weeks)]
    if brands:
        result = result[result["Brand"].isin(brands)]
    if cond:
        # simple demo: allow >, <, >=, <= on Mentions or SwitchesTo/SwitchesFrom
        # e.g., "Mentions > 500"
        m = re.match(r"(mentions|switchesto|switchesfrom)\s*(>=|<=|>|<|==)\s*(\d+)", cond)
        if m:
            col, op, val = m.group(1), m.group(2), int(m.group(3))
            col_map = {"mentions":"Mentions","switchesto":"SwitchesTo","switchesfrom":"SwitchesFrom"}
            c = col_map[col]
            if op == ">": result = result[result[c] > val]
            elif op == "<": result = result[result[c] < val]
            elif op == ">=": result = result[result[c] >= val]
            elif op == "<=": result = result[result[c] <= val]
            elif op == "==": result = result[result[c] == val]

    # projections
    proj = plan.projections or ["Week","Brand","Mentions","Promotions","SwitchesTo","SwitchesFrom"]
    result = result[proj]

    # computations
    derived: Dict[str, Any] = {}
    comps = [c.lower() for c in (plan.computations or [])]

    if "sum" in comps:
        sums = result.select_dtypes(include="number").sum(numeric_only=True).to_dict()
        derived.setdefault("totals", {}).update(sums)
    if "avg" in comps or "mean" in comps:
        avgs = result.select_dtypes(include="number").mean(numeric_only=True).to_dict()
        derived.setdefault("averages", {}).update({k: float(v) for k,v in avgs.items()})
    if "diff" in comps and len(result) == 2 and "Mentions" in result.columns:
        # difference of mentions between two rows
        vals = result["Mentions"].tolist()
        derived.setdefault("diffs", {})["Mentions_diff_row0_row1"] = vals[0] - vals[1]
    if "rank" in comps and "Mentions" in result.columns:
        ranks = (result
                 .groupby([])  # no group -> overall
                 .apply(lambda _: result.sort_values("Mentions", ascending=False)[["Brand","Mentions"]])
                 .reset_index(drop=True))
        derived["rankings_mentions"] = ranks.to_dict(orient="records")

    return result.reset_index(drop=True), derived

# ---------------------------
# Orchestration
# ---------------------------
@tracer.start_as_current_span("run_two_agent_pipeline")
def run_two_agent_pipeline(
    openai_client,
    model_a: str,
    model_b: str,
    df: pd.DataFrame,
    question: str
) -> Dict[str, Any]:
    # 1) Agent A -> JSON plan
    a_user = AGENT_A_USER_TMPL.format(question=question)
    plan_json, a_metrics = chat_json(openai_client, model_a, AGENT_A_SYSTEM, a_user, temperature=0.0)

    # Validate minimal schema
    required_keys = {"ok","question","query_type","filters","computations","projections","notes"}
    if not set(plan_json.keys()) >= required_keys or not plan_json.get("ok"):
        return {
            "error":"Agent A returned invalid plan or ok=false",
            "plan_json": plan_json,
            "a_metrics": a_metrics.to_dict()
        }

    plan = AgentAPlan(
        ok=True,
        question=plan_json["question"],
        query_type=plan_json["query_type"],
        filters=plan_json.get("filters", {}),
        computations=plan_json.get("computations", []),
        projections=plan_json.get("projections", []),
        notes=plan_json.get("notes", []),
    )

    # 2) Execute plan deterministically
    exec_df, derived = execute_plan_on_df(df, plan)
    rows_json = exec_df.to_dict(orient="records")
    plan_str = json.dumps(plan_json, indent=2)
    rows_str = json.dumps(rows_json, indent=2)
    derived_str = json.dumps(derived, indent=2)

    # 3) Agent B -> narrative based ONLY on rows+derived
    b_user = AGENT_B_USER_TMPL.format(
        question=question,
        plan_json=plan_str,
        rows_json=rows_str,
        derived_json=derived_str
    )
    insight_json, b_metrics = chat_json(openai_client, model_b, AGENT_B_SYSTEM, b_user, temperature=0.2)

    return {
        "plan_json": plan_json,
        "executed_rows": rows_json,
        "derived": derived,
        "insight": insight_json,
        "a_metrics": a_metrics.to_dict(),
        "b_metrics": b_metrics.to_dict(),
    }

# ---------------------------
# Paired Test Harness (10 tests)
# ---------------------------
DEFAULT_TESTS = [
    # 1
    "What was the number of T-Mobile mentions in week 2025-W34?",
    # 2
    "What is the total number of mentions for Verizon across all 12 weeks?",
    # 3
    "In week 2025-W30, how many more mentions did T-Mobile have compared to AT&T?",
    # 4
    "Which brand had the highest average mentions per week across the dataset? Return brand and value.",
    # 5
    "Which brand gained the most switches-to-brand in week 2025-W32?",
    # 6
    "Show the week-over-week change in mentions for T-Mobile between 2025-W28 and 2025-W32.",
    # 7
    "Rank all brands by their total mentions from highest to lowest.",
    # 8
    "What was the average increase in T-Mobile mentions per week between 2025-W30 and 2025-W37?",
    # 9
    "List all T-Mobile promotions that led to more than 300 switches in any week.",
    # 10
    "Provide totals for switches-to-brand and switches-from-brand per competitor across all 12 weeks.",
]

def load_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    # Normalize expected columns
    rename_map = {
        "Switches to Brand": "SwitchesTo",
        "Switches from Brand": "SwitchesFrom",
        "Promotions Driving Switching": "Promotions"
    }
    for k, v in rename_map.items():
        if k in df.columns and v not in df.columns:
            df[v] = df[k]
    return df[["Week","Brand","Mentions","Promotions","SwitchesTo","SwitchesFrom"]]

def save_reports(all_runs: List[Dict[str,Any]], outdir: str):
    os.makedirs(outdir, exist_ok=True)
    # JSON
    with open(os.path.join(outdir, "all_runs.json"), "w", encoding="utf-8") as f:
        json.dump(all_runs, f, indent=2)

    # CSV summary for quick scanning
    with open(os.path.join(outdir, "summary.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["idx","question","ok_plan","rows_count","has_insight","a_tokens","b_tokens","a_time_s","b_time_s"])
        for i, r in enumerate(all_runs, 1):
            ok_plan = "plan_json" in r and isinstance(r["plan_json"], dict)
            rows_count = len(r.get("executed_rows", []))
            has_insight = 1 if "insight" in r else 0
            a_tok = r.get("a_metrics",{}).get("total_tokens")
            b_tok = r.get("b_metrics",{}).get("total_tokens")
            a_time = r.get("a_metrics",{}).get("total_time")
            b_time = r.get("b_metrics",{}).get("total_time")
            w.writerow([i, r.get("question",""), ok_plan, rows_count, has_insight, a_tok, b_tok, a_time, b_time])

    # Lightweight HTML (exec summary)
    html = [
        "<html><head><meta charset='utf-8'><title>Two-Agent Report</title>",
        "<style>body{font-family:Arial;padding:16px}pre{background:#f5f5f5;padding:10px;border-radius:6px}</style>",
        "</head><body>",
        f"<h1>Two-Agent Insights Report</h1><p>Generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p><hr/>"
    ]
    for i, r in enumerate(all_runs, 1):
        html.append(f"<h2>Test {i}</h2>")
        html.append(f"<p><b>Question:</b> {r['question']}</p>")
        html.append("<h3>Agent A Plan</h3><pre>"+json.dumps(r.get("plan_json",{}), indent=2)+"</pre>")
        html.append("<h3>Executed Rows</h3><pre>"+json.dumps(r.get("executed_rows",[]), indent=2)+"</pre>")
        html.append("<h3>Derived</h3><pre>"+json.dumps(r.get("derived",{}), indent=2)+"</pre>")
        html.append("<h3>Agent B Insight</h3><pre>"+json.dumps(r.get("insight",{}), indent=2)+"</pre>")
        html.append("<h4>Perf</h4><pre>"+json.dumps({
            "a_metrics": r.get("a_metrics",{}),
            "b_metrics": r.get("b_metrics",{})
        }, indent=2)+"</pre><hr/>")
    html.append("</body></html>")
    with open(os.path.join(outdir, "report.html"), "w", encoding="utf-8") as f:
        f.write("\n".join(html))

@tracer.start_as_current_span("main_two_agent")
def main():
    p = argparse.ArgumentParser(description="Two-Agent (Planner+Insight) harness over competitor dataset")
    p.add_argument("--data_csv", required=True, help="Path to synthetic CSV with columns: Week,Brand,Mentions,Promotions,SwitchesTo,SwitchesFrom")
    p.add_argument("--output", default=f"two_agent_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    p.add_argument("--limit_tests", type=int, default=None)
    p.add_argument("--model_a", default=os.environ.get("AGENT_A_DEPLOYMENT","gpt-4o-mini"))
    p.add_argument("--model_b", default=os.environ.get("AGENT_B_DEPLOYMENT","gpt-4o"))
    args = p.parse_args()

    # Clients
    project_client, openai_client = get_llm_clients()
    configure_tracing(project_client)

    # Data
    df = load_csv(args.data_csv)

    # Tests
    tests = DEFAULT_TESTS[: args.limit_tests] if args.limit_tests else DEFAULT_TESTS

    all_runs = []
    for q in tests:
        try:
            out = run_two_agent_pipeline(openai_client, args.model_a, args.model_b, df, q)
            out["question"] = q
            all_runs.append(out)
            print(f"[OK] {q}")
        except Exception as e:
            print(f"[ERR] {q}: {e}")
            all_runs.append({"question": q, "error": str(e)})

    save_reports(all_runs, args.output)
    print(f"\nDone. Reports in: {args.output}")
    print(f"- HTML: {os.path.join(args.output,'report.html')}")
    print(f"- JSON: {os.path.join(args.output,'all_runs.json')}")
    print(f"- CSV : {os.path.join(args.output,'summary.csv')}")

if __name__ == "__main__":
    main()
