"""
Streamlit web interface for Medical Notes Chatbot.

This provides a user-friendly chat interface to interact with the medical notes
processing system using the chatbot API.
"""

import streamlit as st
import requests
import os
from typing import Dict, Any

# API Configuration - read from environment or use default
API_BASE = os.getenv("API_BASE", "http://localhost:8000")

# Page configuration
st.set_page_config(
    page_title="Medical Notes Chatbot",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .stChatMessage {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .user-message {
        background-color: #e3f2fd;
    }
    .assistant-message {
        background-color: #f5f5f5;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize session state for chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

if "conversation_count" not in st.session_state:
    st.session_state.conversation_count = 0

# Generate a unique session ID for this Streamlit session
if "session_id" not in st.session_state:
    import uuid
    st.session_state.session_id = str(uuid.uuid4())


def send_message(message: str) -> Dict[str, Any]:
    """Send a message to the chatbot API."""
    try:
        # Use longer timeout for "all patients" requests
        timeout = 120 if "all" in message.lower() else 60
        response = requests.post(
            f"{API_BASE}/chat",
            json={
                "message": message,
                "session_id": st.session_state.session_id  # Include session ID for memory
            },
            timeout=timeout
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"response": f"Error connecting to API: {str(e)}", "conversation_length": 0}


def reset_conversation():
    """Reset the conversation history."""
    try:
        response = requests.post(f"{API_BASE}/chat/reset", timeout=5)
        response.raise_for_status()
        st.session_state.messages = []
        st.session_state.conversation_count = 0
        return True
    except requests.exceptions.RequestException:
        return False


# Sidebar with information and controls
with st.sidebar:
    st.title("Medical Notes Chatbot")
    st.markdown("---")

    st.markdown("""
    ### Capabilities:
    - List available medical documents
    - Retrieve specific documents
    - Summarize medical notes
    - Extract structured data with medical codes
    - Get ICD-10 and RxNorm codes
    - Convert to FHIR format
    """)

    st.markdown("---")

    st.markdown("""
    ### Example Queries:
    - "What medical documents do you have?"
    - "Summarize document 1"
    - "Extract structured data from document 2"
    - "What medications were prescribed in document 3?"
    - "Show me the patient's vital signs from document 4"
    """)

    st.markdown("---")

    if st.button("Reset Conversation", use_container_width=True):
        if reset_conversation():
            st.success("Conversation reset")
            st.rerun()
        else:
            st.error("Failed to reset conversation")

    st.markdown("---")

    # System status
    st.markdown("### System Status")
    try:
        health_response = requests.get(f"{API_BASE}/health", timeout=5)
        if health_response.status_code == 200:
            st.success("API Connected")
        else:
            st.error("API Error")
    except:
        st.error("API Offline")

    if st.session_state.conversation_count > 0:
        st.info(f"Messages: {st.session_state.conversation_count}")

# Main chat interface
st.title("Medical Notes AI Assistant")
st.markdown("Query medical notes for summaries, structured extraction, and FHIR conversion.")

# Display chat messages
for idx, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

        # Add download button if message contains CSV
        if message["role"] == "assistant" and "```csv" in message["content"]:
            csv_start = message["content"].find("```csv\n") + 7
            csv_end = message["content"].find("\n```", csv_start)
            if csv_start > 6 and csv_end > csv_start:
                csv_content = message["content"][csv_start:csv_end]
                st.download_button(
                    label="Download CSV File",
                    data=csv_content,
                    file_name="medical_codes_export.csv",
                    mime="text/csv",
                    key=f"download_history_{idx}"
                )

# Chat input
if prompt := st.chat_input("Enter query..."):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)

    # Get bot response
    with st.chat_message("assistant"):
        with st.spinner("Processing..."):
            result = send_message(prompt)
            response = result.get("response", "Request could not be processed.")
            st.session_state.conversation_count = result.get("conversation_length", 0)

            # Display assistant response
            st.markdown(response)

            # If response contains CSV data, add download button
            if "```csv" in response:
                # Extract CSV content from code block
                csv_start = response.find("```csv\n") + 7
                csv_end = response.find("\n```", csv_start)
                if csv_start > 6 and csv_end > csv_start:
                    csv_content = response[csv_start:csv_end]

                    # Create download button
                    st.download_button(
                        label="Download CSV File",
                        data=csv_content,
                        file_name="medical_codes_export.csv",
                        mime="text/csv",
                        key=f"download_{len(st.session_state.messages)}"  # Unique key
                    )

    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": response})

# Welcome message for first-time users
if len(st.session_state.messages) == 0:
    with st.chat_message("assistant"):
        st.markdown("""
        Medical Notes AI Assistant ready.

        Available operations:
        - Browse and retrieve medical documents
        - Summarize medical notes
        - Extract structured data with medical codes (ICD-10, RxNorm)
        - Answer questions about patient information

        Try: **"What medical documents do you have?"**
        """)
