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

    response = requests.get(url)

    data = response.json()

    if "results" in data:

        st.subheader("Results")

        df = pd.DataFrame(data["results"])

        st.dataframe(df)

    else:
        st.error(data["error"])