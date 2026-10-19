"""FastAPI service for the ecommerce analytics agent.

Architecture:
SOURCE DATA -> INGESTION -> VALIDATION -> TRANSFORMATION/DBT ->
BUSINESS-READY ANALYTICS -> FASTAPI -> AI AGENT -> NATURAL-LANGUAGE RESPONSE.

The LLM is used for planning and summarization. The business metrics are read
from dbt-built marts or calculated by deterministic Python helper functions.
"""

from fastapi import FastAPI
from collections import defaultdict
from dotenv import load_dotenv
from pathlib import Path
from dataclasses import dataclass, field
from google.api_core.exceptions import ResourceExhausted

import google.generativeai as genai
import duckdb
import os
import json
import logging

from api.metrics import (
    compute_revenue_delta, compute_product_contribution,
    compute_segment_contribution, detect_sales_anomalies, build_fallback_summary,
)

logger = logging.getLogger(__name__)


@dataclass
class AgentState:
    """Mutable state passed through the agent nodes for one question."""

    question: str
    selected_tools: list = field(default_factory=list)
    raw_data: dict = field(default_factory=dict)
    computed_data: dict = field(default_factory=dict)
    final_answer: str | None = None

BASE_DIR = Path(__file__).resolve().parent.parent


app = FastAPI()

DB_PATH = Path(os.environ.get("DEMO_DB_PATH", BASE_DIR / "ecommerce_project" / "dev.duckdb"))

chat_history = defaultdict(list)

model = None


def get_model():
    """Load credentials and initialize Gemini only when the agent is used."""
    global model
    if model is None:
        load_dotenv(BASE_DIR / ".env")
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is required to call the agent")
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.5-flash-lite")
    return model


def run_query(table_name: str):
    """Read a whitelisted dbt analytics table from DuckDB."""

    # Table names cannot be parameterized in DuckDB, so the explicit allow-list
    # protects the f-string query from arbitrary table access.
    if table_name not in {
        "top_products",
        "top_products_month",
        "revenue_by_segment",
        "revenue_by_segment_month",
        "monthly_revenue"
    }:
        raise ValueError(f"Invalid table: {table_name}")

    con = duckdb.connect(str(DB_PATH), read_only=True)

    result = con.execute(f"""
        SELECT *
        FROM {table_name}
    """).fetchdf()

    con.close()

    return result.to_dict(orient="records")






def get_top_products():
    """Tool: return the dbt mart used for product revenue questions."""

    return run_query("top_products")

def get_revenue_by_segment():
    """Tool: return the dbt mart used for segment revenue questions."""

    return run_query("revenue_by_segment")

def get_monthly_revenue():
    """Tool: return the dbt mart used for month-over-month questions."""

    return run_query("monthly_revenue")

def get_anomalies_sales():
    """Tool: derive anomaly rows from the monthly revenue mart."""

    monthly_data = run_query("monthly_revenue")
    return detect_sales_anomalies(monthly_data)


TOOLS = {
    "top_products": get_top_products,
    "revenue_by_segment": get_revenue_by_segment,
    "monthly_revenue": get_monthly_revenue,
    "anomalies_sales": get_anomalies_sales,
}

ALLOWED_TOOLS = set(TOOLS.keys())


def planner_node(state: AgentState):
    """Select the predefined analytics tools needed for the user's question.

    The planner interprets the natural-language question and is instructed to
    return only valid tool names. It does not calculate business metrics; the
    selected tools fetch data, and later nodes compute deterministic metrics.
    Returned names are filtered against TOOLS before execution.
    """

    tool_prompt = f"""
    You are the planner for an analytics agent.

    Available tools:

    - top_products
      Returns the highest revenue products.

    - revenue_by_segment
      Returns revenue grouped by customer segment.

    - monthly_revenue
      Returns monthly revenue history.

    - anomalies_sales
      Returns months with unusual revenue.

    Rules:
    - Choose every tool needed to answer the question.
    - Return ONLY comma-separated tool names.
    - Never invent tool names.
    - Maximum 3 tools.

    Question:
    {state.question}
    """

    try:

        response = get_model().generate_content(
            tool_prompt,
            generation_config={"temperature": 0}
        )

        state.selected_tools = list(dict.fromkeys([
            t.strip()
            for t in response.text.split(",")
            if t.strip() in TOOLS
        ]))
        

    except Exception as e:

        print(f"Planner error: {e}")
        state.selected_tools = ["monthly_revenue"]

    if not state.selected_tools:
        q = state.question.lower()

        if "segment" in q:
            state.selected_tools = ["revenue_by_segment"]

        elif "product" in q:
            state.selected_tools = ["top_products"]

        elif "anomal" in q:
            state.selected_tools = ["anomalies_sales"]

        else:
            state.selected_tools = ["monthly_revenue"]

    return state
    

def tool_node(state: AgentState):
    """Execute each selected analytics tool and store its raw rows."""

    for tool in state.selected_tools:
        state.raw_data[tool] = TOOLS[tool]()
    return state


def compute_node(state: AgentState):
    """Add deterministic metrics derived from the selected tool outputs."""

    if "monthly_revenue" in state.raw_data:
        state.computed_data["revenue_delta"] = compute_revenue_delta(
            state.raw_data["monthly_revenue"]
        )

    if "top_products" in state.raw_data:
        state.computed_data["product_contribution"] = compute_product_contribution(
            state.raw_data["top_products"]
        )

    if "revenue_by_segment" in state.raw_data:
        state.computed_data["segment_contribution"] = compute_segment_contribution(
            state.raw_data["revenue_by_segment"]
        )
    
    if "anomalies_sales" in state.raw_data:
        state.computed_data["anomalies_sales"] = state.raw_data["anomalies_sales"]
            

    return state
    
    
def analyst_node(state: AgentState):
    """Ask Gemini to summarize raw data and computed metrics for the user."""

    prompt = f"""
    Question:
    {state.question}

    Tools Used:
    {", ".join(state.selected_tools)}

    Raw Data:
    {json.dumps(state.raw_data, indent=2)}

    Computed Metrics:
    {json.dumps(state.computed_data, indent=2)}

    Answer the user's question using ALL available data.
    If multiple datasets were provided, combine them into a single explanation.
    """

    try:
        response = get_model().generate_content(prompt)
        state.final_answer = response.text

    except ResourceExhausted:

        # If the model quota is exhausted, the API still returns a useful
        # deterministic summary from the metrics already computed in Python.
        state.final_answer = build_fallback_summary(state.computed_data)

    return state
    

def run_agent(question: str):
    """Run the planner -> tool -> compute -> analyst workflow."""

    get_model()
    state = AgentState(question)

    state = planner_node(state)
    state = tool_node(state)
    state = compute_node(state)
    state = analyst_node(state)

    return {
    "answer": state.final_answer,
    "tools_used": state.selected_tools,
    "metrics": state.computed_data
    }


@app.get("/")
def home():

    return {
        "message": "AI Analytics API is running"
    }
    
    


@app.get("/ask")
def ask(question: str, session_id: str = "default"):
    """Main API endpoint used by the Streamlit app."""

    chat_history[session_id].append(
        {
            "role": "user",
            "content": question
        }
    )

    try:

        agent_response = run_agent(question)

        chat_history[session_id].append(
            {
                "role": "assistant",
                "content": agent_response["answer"]
            }
        )

        return agent_response

    except Exception as e:

        logger.exception("Agent failed to answer question")

        return {
            "question": question,
            "error": "The agent could not answer this question."
        }



@app.get("/top-products")
def top_products():
    return get_top_products()


@app.get("/revenue-by-segment")
def revenue_by_segment():
    return get_revenue_by_segment()


@app.get("/monthly-revenue")
def monthly_revenue():
    return get_monthly_revenue()

@app.get("/anomalies_sales")
def anomalies_sales():   
    monthly_data = run_query("monthly_revenue")
    return detect_sales_anomalies(monthly_data)
    

@app.get("/agent")
def agent(question: str):
    return run_agent(question)
