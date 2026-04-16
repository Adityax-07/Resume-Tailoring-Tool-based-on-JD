import streamlit as st
from supabase import create_client, Client


def get_supabase() -> Client | None:
    """
    Returns a per-session Supabase client stored in st.session_state.
    Returns None if Supabase secrets are not configured.
    """
    if "_sb" not in st.session_state:
        try:
            st.session_state["_sb"] = create_client(
                st.secrets["SUPABASE_URL"],
                st.secrets["SUPABASE_KEY"],
            )
        except Exception:
            st.session_state["_sb"] = None
    return st.session_state["_sb"]
