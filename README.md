# :speech_balloon: Chat App

A configurable Streamlit chat app powered by OpenAI models.

## Features

- Chat interface with persistent session history
- Model selector (gpt-4o-mini, gpt-4.1-mini, gpt-4.1)
- Temperature control
- Editable system prompt
- Clear chat history button
- Download chat history as JSON

## Run locally

1. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. Start the app:

   ```bash
   streamlit run streamlit_app.py
   ```

3. In the app sidebar, provide your OpenAI API key.

### Optional: use Streamlit secrets

Create `.streamlit/secrets.toml`:

```toml
OPENAI_API_KEY = "your-api-key-here"
```
