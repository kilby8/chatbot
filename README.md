# 🗄️ SQL Database UI (Streamlit)

A Streamlit app that connects to your SQL database and provides:
- table browsing with row previews
- an interactive SQL query runner
- optional read-only mode for safer querying
- CSV export for query results

### How to run it

1. Install the requirements

   ```
   $ pip install -r requirements.txt
   ```

2. Run the app

   ```
   $ streamlit run streamlit_app.py
   ```

3. Add your DB URL in the sidebar

   Examples:
   - `sqlite:///example.db`
   - `mysql+pymysql://user:password@host:3306/database`
