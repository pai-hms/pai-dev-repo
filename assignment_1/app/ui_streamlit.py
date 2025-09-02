# ui_streamlit.py
import streamlit as st
import httpx
import uuid

# --- Page Configuration ---
st.set_page_config(
    page_title="Stock-Bot"
)
st.title("주가 계산 챗봇 (Stock-Bot)")
st.caption("This chatbot connects to a FastAPI backend.")

# --- Constants ---
API_URL = "http://127.0.0.1:8000/api/v1/stream"

# --- Session State Management ---
# Initialize chat history and thread_id if they don't exist
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "안녕하세요! 주식 가격이나 계산에 대해 물어보세요."}
    ]
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())

# --- Helper Function for API Call ---
def stream_api_response(prompt: str, thread_id: str):
    """Calls the FastAPI backend and streams the response."""
    with httpx.stream(
        "POST",
        API_URL,
        json={"message": prompt, "thread_id": thread_id},
        timeout=None,
    ) as response:
        for chunk in response.iter_text():
            yield chunk

# --- Chat Interface ---
# Display existing chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Get user input
if prompt := st.chat_input("엔비디아 5주랑 아마존 8주를 두명이 돈을 모아 사려고 하는데, 각자 얼마나 돈 챙겨야 해?"):
    # Add user message to session state and display it
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Display assistant's streaming response
    with st.chat_message("assistant"):
        full_response = st.write_stream(
            stream_api_response(prompt, st.session_state.thread_id)
        )
    
    # Add the complete assistant response to the session state
    st.session_state.messages.append({"role": "assistant", "content": full_response})