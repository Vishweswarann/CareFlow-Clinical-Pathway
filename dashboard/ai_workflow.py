
import os
import time
import streamlit as st
from google import genai
from google.genai import errors


def _generate_ai_response(prompt):
    api_key = (
        st.secrets.get("GEMINI_API_KEY")
        or os.getenv("GEMINI_API_KEY")
    )

    if not api_key:
        raise ValueError("Gemini API key is missing.")

    client = genai.Client(api_key=api_key)

    models = [
        "gemini-3.8-flash",
        "gemini-3.5-flash-lite",
    ]

    for model in models:
        for attempt in range(2):
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=prompt,
                )
                return response.text

            except errors.ServerError as exc:
                if "503" not in str(exc):
                    raise

                if attempt == 0:
                    time.sleep(2)

    raise RuntimeError(
        "Both Gemini models are temporarily unavailable. "
        "Please try again later."
    )


def generate_workflow_summary(summary_data):
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

    return _generate_ai_response(prompt)


def generate_bottleneck_analysis(transition_data):
    prompt = f"""
    Analyse these hospital workflow transition statistics:
    {transition_data}

    Explain:
    1. Which transitions have the highest mean elapsed time.
    2. Which transitions deserve further operational investigation.
    3. How mean and median times differ.
    4. Practical workflow improvement opportunities.

    Use the supplied data only. Do not invent causes or claim
    that elapsed time proves a clinical delay.
    Do not make diagnoses or clinical decisions.
    Mention that findings depend on the selected sample.
    """

    return _generate_ai_response(prompt)
