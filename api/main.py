from fastapi import FastAPI
from openai import OpenAI
from collections import defaultdict
from dotenv import load_dotenv

import duckdb
import os
import json

load_dotenv()
app = FastAPI()

DB_PATH = "data.db"

chat_history = defaultdict(list)
last_metric = defaultdict(lambda: None)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

METRICS = {
    "top_products": {
        "file": "sql/top_products.sql",
        "comparison_file": "sql/top_products_month.sql",
        "description": "Best selling products by revenue"
    },
    "revenue_by_segment": {
        "file": "sql/revenue_by_segment.sql",
        "comparison_file": "sql/revenue_by_segment_month.sql",
        "description": "Revenue grouped by customer segment"
    },
    "monthly_revenue": {
        "file": "sql/monthly_revenue.sql",
        "comparison_file": "sql/monthly_revenue_month.sql",
        "description": "Revenue trends over time"
    }
}


def run_query(sql_path: str):

    con = duckdb.connect(DB_PATH)

    with open(sql_path, "r") as file:
        query = file.read()

    result = con.execute(query).fetchdf()

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

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "You are an analytics routing assistant."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0
    )

    metric = (
        response
        .choices[0]
        .message
        .content
        .strip()
        .lower()
    )

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

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "You are a helpful analytics assistant."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.3
    )

    return response.choices[0].message.content.strip()


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

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "You are an analytics comparison expert."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.3
    )

    return response.choices[0].message.content.strip()


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

        comparison_file = METRICS[metric]["comparison_file"]

        comparison_results = run_query(comparison_file)

        comparison_insight = generate_comparison_insight(
            metric,
            comparison_results
        )

        return {
            "question": question,
            "metric": metric,
            "comparison_results": comparison_results,
            "comparison_insight": comparison_insight
        }

    metric = llm_route_question(question)

    if not metric:
        return {
            "question": question,
            "error": "No matching metric found"
        }

    last_metric[session_id] = metric

    sql_file = METRICS[metric]["file"]

    results = run_query(sql_file)

    context = chat_history[session_id][-6:]

    insight = generate_chat_insight(
        context,
        results
    )

    chat_history[session_id].append(
        {
            "role": "assistant",
            "content": insight
        }
    )

    return {
        "question": question,
        "metric": metric,
        "sql_used": sql_file,
        "results": results,
        "insight": insight
    }


@app.get("/top-products")
def top_products():

    return run_query("sql/top_products.sql")


@app.get("/revenue-by-segment")
def revenue_by_segment():

    return run_query("sql/revenue_by_segment.sql")


@app.get("/monthly-revenue")
def monthly_revenue():

    return run_query("sql/monthly_revenue.sql")

