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


@dataclass
class AgentState:
    question: str
    planner_reason: str = ""
    selected_tools: list = field(default_factory=list)
    raw_data: dict = field(default_factory=dict)
    computed_data: dict = field(default_factory=dict)
    final_answer: str | None = None

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

print("Gemini API key loaded:", bool(os.getenv("GEMINI_API_KEY")))

app = FastAPI()

DB_PATH = BASE_DIR / "ecommerce_project" / "dev.duckdb"

chat_history = defaultdict(list)

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.5-flash-lite")


def run_query(table_name: str):

    if table_name not in {
        "top_products",
        "top_products_month",
        "revenue_by_segment",
        "revenue_by_segment_month",
        "monthly_revenue",
        "monthly_revenue_month"
    }:
        raise ValueError(f"Invalid table: {table_name}")

    con = duckdb.connect(str(DB_PATH))

    result = con.execute(f"""
        SELECT *
        FROM {table_name}
    """).fetchdf()

    con.close()

    return result.to_dict(orient="records")



def compute_revenue_delta(monthly_data):
    if not monthly_data or len(monthly_data) < 2:
        return {
            "error": "Need at least 2 months of data"
        }

    sorted_data = sorted(monthly_data, key=lambda x: x["month"])

    prev = sorted_data[-2]
    curr = sorted_data[-1]

    delta = curr["revenue"] - prev["revenue"]
    pct_change = (delta / prev["revenue"]) * 100 if prev["revenue"] else 0

    return {
        "previous_month": prev,
        "current_month": curr,
        "absolute_change": delta,
        "percent_change": pct_change
    }

def compute_product_contribution(top_products):
    total = sum(p["revenue"] for p in top_products)

    return [
        {
            "product": p["product_name"],
            "revenue": p["revenue"],
            "share": (p["revenue"] / total) * 100 if total else 0
        }
        for p in top_products
    ]

def compute_segment_contribution(segments):
    total = sum(s["revenue"] for s in segments)

    return [
        {
            "segment": s["segment"],
            "revenue": s["revenue"],
            "share": (s["revenue"] / total) * 100 if total else 0
        }
        for s in segments
    ]

def get_top_products():
    return run_query("top_products")

def get_revenue_by_segment():
    return run_query("revenue_by_segment")

def get_monthly_revenue():
    return run_query("monthly_revenue")

def get_anomalies_sales():
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

        response = model.generate_content(
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
    for tool in state.selected_tools:
        state.raw_data[tool] = TOOLS[tool]()
    return state


def compute_node(state: AgentState):

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
        response = model.generate_content(prompt)
        state.final_answer = response.text

    except ResourceExhausted:

        rev = state.computed_data.get("revenue_delta", {})
        products = state.computed_data.get("product_contribution", [])
        segments = state.computed_data.get("segment_contribution", [])
        anomalies = state.computed_data.get("anomalies_sales", [])

        top_product = products[0] if products else {}
        top_segment = max(segments, key=lambda x: x["share"]) if segments else {}

        state.final_answer = f"""
    Executive Summary

    Revenue increased from ${rev.get('previous_month', {}).get('revenue', 0):,.0f}
    to ${rev.get('current_month', {}).get('revenue', 0):,.0f},
    a change of {rev.get('percent_change', 0):.1f}%.

    Top Product:
    {top_product.get('product', 'N/A')}
    generated ${top_product.get('revenue', 0):,.0f}
    and contributed {top_product.get('share', 0):.1f}% of product revenue.

    Top Customer Segment:
    {top_segment.get('segment', 'N/A')}
    contributed {top_segment.get('share', 0):.1f}% of total revenue.

    Anomalies:
    {len(anomalies)} unusual month(s) detected.
    """

    return state
    

def run_agent(question: str):

    state = AgentState(question)

    state = planner_node(state)
    state = tool_node(state)
    state = compute_node(state)
    state = analyst_node(state)

    return {
    "answer": state.final_answer
    }


@app.get("/")
def home():

    return {
        "message": "AI Analytics API is running"
    }
    
    
def detect_sales_anomalies(monthly_data):

    anomalies = []

    revenues = [r["revenue"] for r in monthly_data]

    avg = sum(revenues) / len(revenues)

    for row in monthly_data:

        if row["revenue"] < avg * 0.8:
            anomalies.append({
                "month": row["month"],
                "revenue": row["revenue"],
                "reason": "Below expected range"
            })

    return anomalies


@app.get("/ask")
def ask(question: str, session_id: str = "default"):

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

        print(f"Agent error: {e}")

        return {
            "question": question,
            "error": str(e)
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
