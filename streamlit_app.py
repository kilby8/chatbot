from __future__ import annotations

import re

import pandas as pd
import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError

st.set_page_config(page_title="SQL Database UI", page_icon="🗄️", layout="wide")


@st.cache_resource(show_spinner=False)
def get_engine(connection_url: str):
    return create_engine(connection_url, future=True)


def list_tables(connection_url: str) -> list[str]:
    inspector = inspect(get_engine(connection_url))
    return inspector.get_table_names()


def run_query(connection_url: str, query: str) -> tuple[pd.DataFrame | None, str]:
    with get_engine(connection_url).connect() as connection:
        result = connection.execute(text(query))
        if result.returns_rows:
            rows = result.fetchall()
            frame = pd.DataFrame(rows, columns=result.keys())
            return frame, f"Returned {len(frame)} row(s)."
        connection.commit()
        return None, f"Query executed successfully. {result.rowcount} row(s) affected."


def is_read_only_query(query: str) -> bool:
    normalized = re.sub(r"/\*.*?\*/", "", query, flags=re.S)
    normalized = re.sub(r"--.*?$", "", normalized, flags=re.M).strip().lower()
    return normalized.startswith("select") or normalized.startswith("with")


st.title("🗄️ SQL Database UI")
st.caption("Connect to your SQL database, browse tables, and run queries from one place.")

try:
    default_url = st.secrets["DATABASE_URL"]
except (StreamlitSecretNotFoundError, KeyError, FileNotFoundError):
    default_url = "sqlite:///example.db"
connection_url = st.sidebar.text_input(
    "SQLAlchemy connection URL",
    value=default_url,
    help="Examples: sqlite:///example.db, mysql+pymysql://user:pass@host/dbname",
)
max_preview_rows = st.sidebar.slider("Preview rows", min_value=5, max_value=200, value=25)
read_only_mode = st.sidebar.checkbox("Read-only mode (allow SELECT/WITH only)", value=True)

if not connection_url.strip():
    st.info("Add a connection URL in the sidebar to begin.")
    st.stop()

try:
    tables = list_tables(connection_url)
except SQLAlchemyError as error:
    st.error(f"Could not connect to database: {error}")
    st.stop()

st.success("Connected")
st.subheader("Table browser")

if tables:
    table_name = st.selectbox("Choose a table", options=tables)
    preview_query = f'SELECT * FROM "{table_name}" LIMIT {max_preview_rows}'
    try:
        table_preview, message = run_query(connection_url, preview_query)
    except SQLAlchemyError as error:
        st.error(f"Could not preview table `{table_name}`: {error}")
    else:
        st.write(message)
        st.dataframe(table_preview, width="stretch", hide_index=True)
else:
    st.info("No tables found in this database.")

st.divider()
st.subheader("SQL runner")

default_sql = (
    "SELECT name FROM sqlite_master WHERE type='table';"
    if connection_url.startswith("sqlite")
    else "SELECT 1;"
)
query = st.text_area("SQL query", value=default_sql, height=160)

if st.button("Run query", type="primary"):
    if not query.strip():
        st.warning("Enter a SQL query first.")
    elif read_only_mode and not is_read_only_query(query):
        st.error("Read-only mode is enabled. Run only SELECT or WITH queries.")
    else:
        try:
            data, message = run_query(connection_url, query)
        except SQLAlchemyError as error:
            st.error(f"Query failed: {error}")
        else:
            st.success(message)
            if data is not None:
                st.dataframe(data, width="stretch", hide_index=True)
                st.download_button(
                    "Download results as CSV",
                    data=data.to_csv(index=False).encode("utf-8"),
                    file_name="query_results.csv",
                    mime="text/csv",
                )
