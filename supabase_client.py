# supabase_client.py
# ─────────────────────────────────────────────────────────────────────────────
# Provides a per-session Supabase client for auth and database operations.
#
# Why per-session instead of a shared/cached client?
#   Streamlit's @st.cache_resource creates one shared object across all users.
#   If we cached the Supabase client that way, signing in as User A would
#   attach User A's auth token to the shared client — meaning User B's queries
#   would run under User A's identity, leaking data across sessions.
#
#   Storing the client in st.session_state creates a separate instance per
#   browser session, so each user's auth state is fully isolated.
# ─────────────────────────────────────────────────────────────────────────────

import streamlit as st
from supabase import create_client, Client


def get_supabase() -> Client | None:
    """
    Returns a per-session Supabase client stored in st.session_state.
    Returns None if Supabase secrets are not configured (e.g. local dev
    without a secrets.toml), so the rest of the app can degrade gracefully
    rather than crashing on startup.
    """
    if "_sb" not in st.session_state:
        # First access this session — create and cache the client.
        # Reads SUPABASE_URL and SUPABASE_KEY from .streamlit/secrets.toml
        # locally, or from the Streamlit Cloud secrets panel in production.
        try:
            st.session_state["_sb"] = create_client(
                st.secrets["SUPABASE_URL"],
                st.secrets["SUPABASE_KEY"],
            )
        except Exception:
            # Secrets not found — auth and history features will be disabled.
            st.session_state["_sb"] = None

    return st.session_state["_sb"]
