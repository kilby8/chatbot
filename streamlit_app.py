import json

import streamlit as st
from openai import OpenAI


st.set_page_config(page_title="Chatbot Studio", page_icon="💬")


def stream_demo_response(prompt: str, system_prompt: str):
    prompt_line = f"You said: {prompt}"
    system_line = (
        f"System prompt in use: {system_prompt.strip()}"
        if system_prompt.strip()
        else "No system prompt set."
    )
    text = (
        "Demo mode is active, so this reply is generated locally without calling OpenAI. "
        f"{system_line} "
        f"{prompt_line}"
    )
    for token in text.split():
        yield token + " "


def build_model_messages(system_prompt: str):
    messages = []
    if system_prompt.strip():
        messages.append({"role": "system", "content": system_prompt.strip()})
    messages.extend(
        {"role": message["role"], "content": message["content"]}
        for message in st.session_state.messages
    )
    return messages


def clear_chat():
    st.session_state.messages = []


if "messages" not in st.session_state:
    st.session_state.messages = []

st.title("💬 Chatbot Studio")
st.write(
    "Build and test prompts quickly with local demo mode or OpenAI mode. "
    "Use the sidebar to configure model settings, reset chat history, and export conversation JSON."
)

with st.sidebar:
    st.header("Settings")
    mode = st.radio("Mode", options=["Demo (no API key)", "OpenAI"])
    model = st.selectbox("Model", ["gpt-4o-mini", "gpt-4.1-mini", "gpt-4.1"])
    temperature = st.slider("Temperature", min_value=0.0, max_value=1.0, value=0.7, step=0.1)
    system_prompt = st.text_area(
        "System prompt",
        value="",
        placeholder="You are a helpful assistant.",
    )

    openai_api_key = ""
    if mode == "OpenAI":
        openai_api_key = st.text_input("OpenAI API Key", type="password")
        if not openai_api_key:
            st.info("Add an OpenAI API key to send messages in OpenAI mode.", icon="🗝️")

    st.divider()
    if st.button("Clear chat", use_container_width=True):
        clear_chat()
        st.success("Chat history cleared.")

    st.download_button(
        label="Export chat as JSON",
        data=json.dumps(st.session_state.messages, indent=2),
        file_name="chat_history.json",
        mime="application/json",
        use_container_width=True,
    )

if not st.session_state.messages:
    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": (
                "Hello! Use Demo mode to try the app instantly, or switch to OpenAI mode and add an API key."
            ),
        }
    )

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

chat_disabled = mode == "OpenAI" and not openai_api_key
if prompt := st.chat_input("Send a message", disabled=chat_disabled):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        if mode == "Demo (no API key)":
            response = st.write_stream(stream_demo_response(prompt, system_prompt))
        else:
            try:
                client = OpenAI(api_key=openai_api_key)
                stream = client.chat.completions.create(
                    model=model,
                    messages=build_model_messages(system_prompt),
                    temperature=temperature,
                    stream=True,
                )
                response = st.write_stream(stream)
            except Exception as error:
                response = f"OpenAI request failed: {error}"
                st.error(response)

    st.session_state.messages.append({"role": "assistant", "content": response})
