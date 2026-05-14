from fastapi import FastAPI
import duckdb

app = FastAPI()
DB_PATH = "data.db"


def run_query(sql_path: str):
    con = duckdb.connect(DB_PATH)

    with open(sql_path, "r") as file:
        query = file.read()

    result = con.execute(query).fetchdf()
    return result.to_dict(orient="records")


@app.get("/")
def home():
    return {"message": "Data Engineering API is running"}
    
@app.get("/ask")
def ask(question: str):

    sql_file = question_to_sql(question)

    if not sql_file:
        return {
            "error": "Sorry, I don't understand that question yet."
        }

    results = run_query(sql_file)

    return {
        "question": question,
        "results": results
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
    
def question_to_sql(question: str):

    question = question.lower()

    mappings = {
        "top products": "sql/top_products.sql",
        "best selling products": "sql/top_products.sql",
        "revenue by segment": "sql/revenue_by_segment.sql",
        "customer segments": "sql/revenue_by_segment.sql",
        "monthly revenue": "sql/monthly_revenue.sql",
        "sales trend": "sql/monthly_revenue.sql"
    }

    for key, sql_file in mappings.items():
        if key in question:
            return sql_file

    return None