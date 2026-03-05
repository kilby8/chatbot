import json

import streamlit as st
from openai import OpenAI

st.set_page_config(page_title="Chat App", page_icon=":speech_balloon:", layout="centered")

st.title(":speech_balloon: Chat App")
st.caption("A simple, configurable AI chat app built with Streamlit + OpenAI.")

if "messages" not in st.session_state:
    st.session_state.messages = []

if "system_prompt" not in st.session_state:
    st.session_state.system_prompt = "You are a helpful assistant."

with st.sidebar:
    st.header("Settings")
    st.write("Use your OpenAI API key and tune the model behavior.")

    secret_key = ""
    if "OPENAI_API_KEY" in st.secrets:
        secret_key = st.secrets["OPENAI_API_KEY"]

    openai_api_key = st.text_input(
        "OpenAI API Key",
        value=secret_key,
        type="password",
        help="You can also store this as OPENAI_API_KEY in .streamlit/secrets.toml",
    )
    model = st.selectbox(
        "Model",
        options=["gpt-4o-mini", "gpt-4.1-mini", "gpt-4.1"],
        index=0,
    )
    temperature = st.slider("Temperature", min_value=0.0, max_value=1.5, value=0.7, step=0.1)
    st.session_state.system_prompt = st.text_area(
        "System Prompt",
        value=st.session_state.system_prompt,
        height=120,
    )

    if st.button("Clear chat history", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    chat_export = json.dumps(st.session_state.messages, indent=2)
    st.download_button(
        "Download chat history",
        data=chat_export,
        file_name="chat_history.json",
        mime="application/json",
        use_container_width=True,
    )

if not openai_api_key:
    st.info("Enter an OpenAI API key in the sidebar to start chatting.", icon=":key:")
    st.stop()

client = OpenAI(api_key=openai_api_key)

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Ask me anything"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    api_messages = [{"role": "system", "content": st.session_state.system_prompt}]
    api_messages.extend(st.session_state.messages)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                completion = client.chat.completions.create(
                    model=model,
                    messages=api_messages,
                    temperature=temperature,
                )
                response = completion.choices[0].message.content or "I could not generate a response."
                st.markdown(response)
            except Exception as err:  # noqa: BLE001
                response = f"Sorry, I hit an error: `{err}`"
                st.error(response)

    st.session_state.messages.append({"role": "assistant", "content": response})
