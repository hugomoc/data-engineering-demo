"""Streamlit front end for asking natural-language ecommerce questions.

The UI is intentionally thin: it collects a question, calls the FastAPI agent,
and renders the response. Data access, planning, and analytics calculations
stay behind the API so the presentation layer remains easy to reason about.
"""

import streamlit as st
import requests
import os

API_URL = os.environ.get("API_URL", "http://127.0.0.1:8000")

st.title("AI Data Analytics Demo")

question = st.text_input(
    "Ask a business question",
    placeholder="Example: top products"
)

if question:

    try:
        response = requests.get(
            f"{API_URL}/ask", params={"question": question}, timeout=60
        )
        if response.status_code != 200:
            st.error(f"The analytics API returned HTTP {response.status_code}.")
        else:
            data = response.json()
            if data.get("error"):
                st.error(data["error"])
            elif "answer" in data:
                st.markdown(data["answer"])
            else:
                st.error("The analytics API returned an unexpected response.")
    except requests.RequestException:
        st.error("Could not connect to the analytics API. Please try again.")
    except ValueError:
        st.error("The analytics API returned an invalid response.")
