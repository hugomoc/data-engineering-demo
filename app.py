"""Streamlit front end for asking natural-language ecommerce questions.

The UI is intentionally thin: it collects a question, calls the FastAPI agent,
and renders the response. Data access, planning, and analytics calculations
stay behind the API so the presentation layer remains easy to reason about.
"""

import streamlit as st
import requests
import pandas as pd

st.title("AI Data Analytics Demo")

question = st.text_input(
    "Ask a business question",
    placeholder="Example: top products"
)

if question:

    url = f"http://127.0.0.1:8000/ask?question={question}"

    # The API owns the agent workflow; Streamlit only passes the question and
    # displays the response returned by FastAPI.
    response = requests.get(url)

    data = response.json()

    if "results" in data:

        st.subheader("Results")

        df = pd.DataFrame(data["results"])

        st.dataframe(df)

    else:
        st.error(data["error"])
