import os
import streamlit as st

try:
    import openai
    OPENAI_AVAILABLE = True
except Exception:
    OPENAI_AVAILABLE = False
    openai = None

OPENAI_API_KEY = None
if OPENAI_AVAILABLE:
    OPENAI_API_KEY = st.secrets.get("openai_api_key", os.getenv("OPENAI_API_KEY"))


def setup_openai_api():
    """Configure OpenAI API key if available.

    Returns
    -------
    tuple
        (has_key: bool, source: str) where source describes the key origin.
    """
    if not OPENAI_AVAILABLE:
        return False, "unavailable"

    api_key = OPENAI_API_KEY or st.session_state.get("openai_api_key")
    if not api_key:
        return False, "missing"

    try:
        # openai>=1 uses OpenAI client, but setting api_key keeps backward compat
        openai.api_key = api_key
        st.session_state["openai_api_key"] = api_key
        return True, "configured"
    except Exception:
        return False, "invalid"
