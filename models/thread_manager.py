import os
import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv('env.dev')

PAT = os.getenv("CORTEX_AGENT_DEMO_PAT")
HOST = os.getenv("CORTEX_AGENT_DEMO_HOST")

def create_new_thread():
    """Create a new thread and return thread ID"""
    url = f"https://{HOST}/api/v2/cortex/threads"
    
    headers = {
        'Authorization': f'Bearer {PAT}',
        'Content-Type': 'application/json'
    }
    
    payload = {
        "origin_application": "cortex_agent"
    }
    
    response = requests.post(url, headers=headers, json=payload)
    
    if response.status_code < 400:
        response_data = response.json()
        return response_data
    else:
        st.error(f"Failed to create thread: {response.status_code} - {response.text}")
        return None

def update_thread_name(thread_id, thread_name):
    """Update thread name"""
    url = f"https://{HOST}/api/v2/cortex/threads/{thread_id}"
    
    headers = {
        'Authorization': f'Bearer {PAT}',
        'Content-Type': 'application/json'
    }
    
    payload = {
        "thread_name": thread_name
    }
    
    response = requests.post(url, headers=headers, json=payload)
    
    if response.status_code < 400:
        return True
    else:
        st.error(f"Failed to update thread name: {response.status_code} - {response.text}")
        return False

def clear_chat_session(custom_name=None):
    """Clear the chat messages and create new thread with optional custom name"""
    st.session_state.messages = []
    thread_data = create_new_thread()
    if thread_data:
        thread_id = thread_data.get('thread_id')
        
        # Set custom name if provided
        if custom_name:
            if update_thread_name(thread_id, custom_name):
                thread_data['thread_name'] = custom_name
        
        # Initialize thread conversation tracking
        st.session_state.current_thread_data = thread_data
        st.session_state.current_thread_id = thread_id
        st.session_state.parent_message_id = 0  # Start with 0 (integer) for first message
        st.session_state.current_user_message_id = None
        st.session_state.current_assistant_message_id = None
        st.session_state.message_ids_history = []
        
    return thread_data