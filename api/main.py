from fastapi import FastAPI
from collections import defaultdict
from dotenv import load_dotenv
from pathlib import Path

import google.generativeai as genai
import duckdb
import os
import json

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

print("KEY LOADED:", os.getenv("GEMINI_API_KEY"))

app = FastAPI()

DB_PATH = BASE_DIR / "ecommerce_project" / "dev.duckdb"



chat_history = defaultdict(list)
last_metric = defaultdict(lambda: None)

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.5-flash-lite")

METRICS = {
    "top_products": {
        "table": "top_products",
        "comparison_table": "top_products_month",
        "description": "Best selling products by revenue"
    },
    "revenue_by_segment": {
        "table": "revenue_by_segment",
        "comparison_table": "revenue_by_segment_month",
        "description": "Revenue grouped by customer segment"
    },
    "monthly_revenue": {
        "table": "monthly_revenue",
        "comparison_table": "monthly_revenue_month",
        "description": "Revenue trends over time"
    }    
}


def run_query(table_name: str):

    if table_name not in {
        "top_products",
        "top_products_month",
        "revenue_by_segment",
        "revenue_by_segment_month",
        "monthly_revenue"
    }:
        raise ValueError(f"Invalid table: {table_name}")

    con = duckdb.connect(str(DB_PATH))

    result = con.execute(f"""
        SELECT *
        FROM {table_name}
    """).fetchdf()

    con.close()

    return result.to_dict(orient="records")


def is_comparison_question(question: str) -> bool:

    keywords = [
        "compare",
        "vs",
        "versus",
        "last month",
        "previous month",
        "difference",
        "change"
    ]

    q = question.lower()

    return any(k in q for k in keywords)


def llm_route_question(question: str):

    metric_list = {
        key: value["description"]
        for key, value in METRICS.items()
    }

    prompt = f"""
    You are an analytics routing system.

    Available metrics:
    {json.dumps(metric_list, indent=2)}

    Rules:
    - Return ONLY the metric key
    - If nothing matches return "none"

    Question:
    {question}
    """

    response = model.generate_content(
        prompt,
        generation_config={
            "temperature": 0
        }
    )

    metric = response.text.strip().lower()

    print(f"LLM selected metric: {metric}")

    if metric in METRICS:
        return metric

    return None


def generate_chat_insight(chat_context, results):

    prompt = f"""
    You are a senior analytics assistant.

    Conversation:
    {json.dumps(chat_context, indent=2)}

    Latest Results:
    {json.dumps(results, indent=2)}

    Rules:
    - Be concise
    - Explain business meaning
    - Do not hallucinate values
    - Keep response between 3 and 5 sentences
    """

    response = model.generate_content(
        prompt,
        generation_config={
            "temperature": 0.3
        }
    )

    return response.text.strip()


def generate_comparison_insight(metric_name, comparison_results):

    prompt = f"""
    You are a senior business analyst.

    Metric:
    {metric_name}

    Comparison Results:
    {json.dumps(comparison_results, indent=2)}

    Explain:
    - Month-over-month changes
    - Key drivers
    - Notable increases or decreases

    Keep the explanation concise.
    """

    response = model.generate_content(
        prompt,
        generation_config={
            "temperature": 0.3
        }
    )

    return response.text.strip()


@app.get("/")
def home():

    return {
        "message": "AI Analytics API is running"
    }


@app.get("/ask")
def ask(question: str, session_id: str = "default"):

    chat_history[session_id].append(
        {
            "role": "user",
            "content": question
        }
    )

    if is_comparison_question(question):

        metric = last_metric[session_id]

        if not metric:
            return {
                "error": "Ask about a metric first. Example: top products"
            }

        comparison_table = METRICS[metric]["comparison_table"]
        comparison_results = run_query(comparison_table)

        try:
            comparison_insight = generate_comparison_insight(
                metric,
                comparison_results
    )
        except Exception as e:
            print(f"Comparison insight error: {e}")
            comparison_insight = "Unable to generate comparison insight."

        return {
            "question": question,
            "metric": metric,
            "comparison_results": comparison_results,
            "comparison_insight": comparison_insight
        }

    try:
        metric = llm_route_question(question)
    except Exception as e:
        print(f"LLM routing error: {e}")

        question_lower = question.lower()

        if "segment" in question_lower:
            metric = "revenue_by_segment"
        elif "product" in question_lower:
            metric = "top_products"
        elif "revenue" in question_lower:
            metric = "monthly_revenue"
        else:
            metric = None

    if not metric:
        return {
            "question": question,
            "error": "No matching metric found"
        }

    last_metric[session_id] = metric

    table_name = METRICS[metric]["table"]
    results = run_query(table_name)

    context = chat_history[session_id][-6:]

    try:
        insight = generate_chat_insight(
            context,
            results
    )
    except Exception as e:
        print(f"Insight generation error: {e}")
        insight = "Unable to generate AI insight."

    chat_history[session_id].append(
        {
            "role": "assistant",
            "content": insight
        }
    )

    return {
    "question": question,
    "metric": metric,
    "table_used": table_name,
    "results": results,
    "insight": insight
    }


@app.get("/top-products")
def top_products():

    return run_query("top_products")


@app.get("/revenue-by-segment")
def revenue_by_segment():

    return run_query("revenue_by_segment")


@app.get("/monthly-revenue")
def monthly_revenue():

    return run_query("monthly_revenue")

