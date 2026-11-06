
import os
import streamlit as st
from google import genai


def generate_workflow_summary(summary_data):
    api_key = (
        st.secrets.get("GEMINI_API_KEY")
        or os.getenv("GEMINI_API_KEY")
    )

    if not api_key:
        raise ValueError("Gemini API key is missing.")

    client = genai.Client(api_key=api_key)


    prompt = f"""
    Analyse these aggregate hospital workflow statistics:
    {summary_data}

    Explain:
    1. Overall workflow patterns.
    2. Frequently observed activities.
    3. Possible operational bottlenecks to investigate.

    Use simple language. Do not make diagnoses or clinical
    decisions. Mention that findings depend on the selected sample.
    """

    response = client.models.generate_content(
        model="gemini-flash-latest",
        contents=prompt,
    )

    return response.text