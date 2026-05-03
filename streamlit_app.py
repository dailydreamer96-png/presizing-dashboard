import streamlit as st

st.set_page_config(
    page_title="Presizing Dashboard",
    layout="wide",
)

summary_page = st.Page("pages/summary_page.py", title="Summary", icon=":material/dashboard:", default=True)
quality_page = st.Page("pages/quality_page.py", title="Quality", icon=":material/analytics:")
mode_page = st.Page("pages/mode_page.py", title="Mode", icon=":material/tune:")

pg = st.navigation(
    [summary_page, quality_page, mode_page],
    position="sidebar",  # change to "top" if you prefer top navigation
)

pg.run()
