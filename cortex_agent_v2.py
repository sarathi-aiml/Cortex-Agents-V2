import json
import os
from collections import defaultdict

import numpy as np
import pandas as pd
import requests
import sseclient
import streamlit as st
from dotenv import load_dotenv

# Load environment variables from env.dev file
load_dotenv('env.dev')

from models import (
    ChartEventData,
    DataAgentRunRequest,
    ErrorEventData,
    Message,
    MessageContentItem,
    StatusEventData,
    TableEventData,
    TextContentItem,
    TextDeltaEventData,
    ThinkingDeltaEventData,
    ThinkingEventData,
    ToolResultEventData,
    ToolUseEventData,
)

# Import thread manager
from models.thread_manager import clear_chat_session
from models.db_manager import save_thread_info, load_conversation_context, get_user_threads

PAT = os.getenv("CORTEX_AGENT_DEMO_PAT")
HOST = os.getenv("CORTEX_AGENT_DEMO_HOST")
DATABASE = os.getenv("CORTEX_AGENT_DEMO_DATABASE", "SNOWFLAKE_INTELLIGENCE")
SCHEMA = os.getenv("CORTEX_AGENT_DEMO_SCHEMA", "AGENTS")
AGENT = os.getenv("CORTEX_AGENT_DEMO_AGENT", "SALES_INTELLIGENCE_AGENT")

def agent_run() -> requests.Response:
    """Calls the REST API and returns a streaming client."""
    # Check if we have an active thread for thread-based conversation
    if hasattr(st.session_state, 'current_thread_id') and st.session_state.current_thread_id:
        # Thread-based conversation - only send current message (server maintains context with correct parent_message_id)
        request_body = DataAgentRunRequest(
            thread_id=st.session_state.current_thread_id,
            parent_message_id=st.session_state.parent_message_id,
            messages=[st.session_state.messages[-1]],  # Only the latest message
        )
    else:
        # Original behavior - send all messages
        request_body = DataAgentRunRequest(
            model="claude-4-sonnet",
            messages=st.session_state.messages,
        )
    
    # Debug: Print the constructed URL
    url = f"https://{HOST}/api/v2/databases/{DATABASE}/schemas/{SCHEMA}/agents/{AGENT}:run"

    # Debug: Print the payload being sent
    payload_json = request_body.to_json()
    print(f"DEBUG - Sending payload: {payload_json}")

    # Log all payloads to file for comparison analysis
    import datetime
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    thread_info = f"thread_{st.session_state.current_thread_id}" if hasattr(st.session_state, 'current_thread_id') and st.session_state.current_thread_id else "no_thread"
    log_filename = f"payload_log_{thread_info}_{timestamp}.txt"

    try:
        with open(log_filename, 'w') as f:
            f.write(f"=== PAYLOAD LOG ===\n")
            f.write(f"Timestamp: {datetime.datetime.now()}\n")
            f.write(f"Thread ID: {getattr(st.session_state, 'current_thread_id', 'None')}\n")
            f.write(f"Parent Message ID: {getattr(st.session_state, 'parent_message_id', 'None')}\n")
            f.write(f"Session Messages Count: {len(st.session_state.messages)}\n")
            f.write(f"Using Thread Context: {hasattr(st.session_state, 'current_thread_id') and st.session_state.current_thread_id is not None}\n")
            f.write(f"URL: {url}\n")
            f.write(f"\n=== PAYLOAD JSON ===\n")
            f.write(payload_json)
            f.write(f"\n\n=== SESSION MESSAGES SUMMARY ===\n")
            for i, msg in enumerate(st.session_state.messages):
                f.write(f"Message {i}: {msg.role} - {msg.content[0].actual_instance.text[:100] if msg.content else 'No content'}...\n")
            f.write(f"\n=== END LOG ===\n")
        print(f"Payload logged to: {log_filename}")
    except Exception as e:
        print(f"Failed to log payload: {e}")

    resp = requests.post(
        url=url,
        data=payload_json,
        headers={
            "Authorization": f'Bearer {PAT}',
            "Content-Type": "application/json",
        },
        stream=True,
        verify=False,
    )
    if resp.status_code < 400:
        return resp  # type: ignore
    else:
        raise Exception(f"Failed request with status {resp.status_code}: {resp.text}")


def stream_events(response: requests.Response):
    content = st.container()
    # Content index to container section mapping
    content_map = defaultdict(content.empty)
    # Content index to text buffer
    buffers = defaultdict(str)
    spinner = st.spinner("Waiting for response...")
    spinner.__enter__()

    # Create response log file info
    import datetime
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    thread_info = f"thread_{st.session_state.current_thread_id}" if hasattr(st.session_state, 'current_thread_id') and st.session_state.current_thread_id else "no_thread"
    response_log_filename = f"response_log_{thread_info}_{timestamp}.txt"

    # Initialize response log
    response_events = []

    events = sseclient.SSEClient(response).events()

    for event in events:
        # Log raw event for comparison
        response_events.append(f"EVENT: {event.event}\nDATA: {event.data}\n{'='*50}\n")

        # Debug: Show all events we receive when we have a thread
        #if hasattr(st.session_state, 'current_thread_id'):
            #st.write(f"**Event Type:** {event.event}")
            #if event.event not in ['response.text.delta', 'response.thinking.delta']:  # Skip noisy events
                #st.write(f"**Event Data:** {event.data[:500]}...")

        # Debug: Show all events we receive
        #if hasattr(st.session_state, 'current_thread_id'):
            #st.write(f"**Debug Event:** {event.event} - Data: {event.data[:200]}...")

        match event.event:
            case "response.status":
                spinner.__exit__(None, None, None)
                data = StatusEventData.from_json(event.data)
                spinner = st.spinner(data.message)
                spinner.__enter__()
            case "response.text.delta":
                data = TextDeltaEventData.from_json(event.data)
                buffers[data.content_index] += data.text
                content_map[data.content_index].write(buffers[data.content_index])
            case "response.thinking.delta":
                data = ThinkingDeltaEventData.from_json(event.data)
                buffers[data.content_index] += data.text
                content_map[data.content_index].expander(
                    "Thinking", expanded=True
                ).write(buffers[data.content_index])
            case "response.thinking":
                # Thinking done, close the expander
                data = ThinkingEventData.from_json(event.data)
                content_map[data.content_index].expander("Thinking").write(data.text)
            case "response.tool_use":
                data = ToolUseEventData.from_json(event.data)
                content_map[data.content_index].expander("Tool use").json(data)
            case "response.tool_result":
                data = ToolResultEventData.from_json(event.data)
                content_map[data.content_index].expander("Tool result").json(data)
            case "response.chart":
                data = ChartEventData.from_json(event.data)
                spec = json.loads(data.chart_spec)
                content_map[data.content_index].vega_lite_chart(
                    spec,
                    use_container_width=True,
                )
            case "response.table":
                data = TableEventData.from_json(event.data)
                data_array = np.array(data.result_set.data)
                column_names = [
                    col.name for col in data.result_set.result_set_meta_data.row_type
                ]
                content_map[data.content_index].dataframe(
                    pd.DataFrame(data_array, columns=column_names)
                )
            case "error":
                data = ErrorEventData.from_json(event.data)
                st.error(f"Error: {data.message} (code: {data.code})")
                # Remove last user message, so we can retry from last successful response.
                st.session_state.messages.pop()
                return
            case "metadata":
                # Handle metadata events for thread message tracking
                try:
                    import json
                    metadata = json.loads(event.data)
                    #st.write(f"**Found metadata event:** {metadata}")
                    # Track both user and assistant message IDs
                    if 'metadata' in metadata and 'message_id' in metadata['metadata']:
                        message_id = int(metadata['metadata'].get('message_id'))
                        role = metadata['metadata'].get('role')
                        
                        if role == 'user':
                            st.session_state.current_user_message_id = message_id
                            # Save user message to database with complete JSON
                            if hasattr(st.session_state, 'current_thread_data') and st.session_state.messages:
                                user_message = st.session_state.messages[-1]  # Latest user message
                                user_content = user_message.content[0].actual_instance.text if user_message.content else ''
                                # Save complete message JSON structure
                                user_message_json = user_message.to_json()
                                save_thread_info(
                                    st.session_state.current_thread_id,
                                    st.session_state.current_thread_data.get('thread_name', ''),
                                    message_id,
                                    message_content=user_content.replace("'", "''"),  # Escape quotes
                                    message_role='user',
                                    message_json=user_message_json
                                )
                        elif role == 'assistant':
                            st.session_state.current_assistant_message_id = message_id
                            # The assistant's message_id becomes the parent_message_id for the next user message
                            st.session_state.parent_message_id = message_id
                            
                        # Store all message IDs for tracking
                        if not hasattr(st.session_state, 'message_ids_history'):
                            st.session_state.message_ids_history = []
                        st.session_state.message_ids_history.append({
                            'role': role,
                            'message_id': message_id
                        })
                except Exception as e:
                    st.write(f"**Metadata parsing error:** {e}")
            case "response":
                data = Message.from_json(event.data)

                # Create clean message for display (without thinking content)
                clean_content = []
                for content_item in data.content:
                    if hasattr(content_item.actual_instance, 'type'):
                        content_type = content_item.actual_instance.type
                        if content_type != 'thinking':  # Exclude thinking from display
                            clean_content.append(content_item)

                clean_display_message = Message(
                    role=data.role,
                    content=clean_content
                )

                # Store clean message for display (no thinking)
                st.session_state.messages.append(clean_display_message)

                # Save assistant message to database if we have thread context
                if (hasattr(st.session_state, 'current_thread_data') and
                    hasattr(st.session_state, 'current_assistant_message_id') and
                    st.session_state.current_assistant_message_id):

                    # Create clean message WITHOUT thinking content for storage
                    clean_content = []
                    assistant_content = ''

                    for content_item in data.content:
                        # Skip thinking content - only store final response elements
                        if hasattr(content_item.actual_instance, 'type'):
                            content_type = content_item.actual_instance.type
                            if content_type != 'thinking':  # Exclude thinking data
                                clean_content.append(content_item)

                                # Extract text for summary
                                if hasattr(content_item.actual_instance, 'text'):
                                    assistant_content += content_item.actual_instance.text

                    # Create clean message object with only final response elements (no thinking)
                    clean_message = Message(
                        role=data.role,
                        content=clean_content
                    )

                    # Save clean message JSON (without thinking) and complete response
                    clean_message_json = clean_message.to_json()
                    response_json = event.data  # Complete raw response as received

                    save_thread_info(
                        st.session_state.current_thread_id,
                        st.session_state.current_thread_data.get('thread_name', ''),
                        st.session_state.current_assistant_message_id,
                        message_content=assistant_content.replace("'", "''"),  # Escape quotes
                        message_role='assistant',
                        message_json=clean_message_json,  # Clean message without thinking
                        response_json=response_json
                    )

                # Check if this response contains message_id
                try:
                    response_data = json.loads(event.data)
                    #st.write(f"**Response event data:** {response_data}")
                except:
                    pass
            case _:
                # Catch any other events we might not be handling
                if hasattr(st.session_state, 'current_thread_id'):
                    a=1 #dummy statement to avoid warning
                    #st.write(f" ")
                    #st.write(f"**Unhandled event:** {event.event}")
    spinner.__exit__(None, None, None)

    # Write raw response log
    try:
        with open(response_log_filename, 'w') as f:
            f.write(f"=== RAW RESPONSE LOG ===\n")
            f.write(f"Timestamp: {datetime.datetime.now()}\n")
            f.write(f"Thread ID: {getattr(st.session_state, 'current_thread_id', 'None')}\n")
            f.write(f"Total Events: {len(response_events)}\n")
            f.write(f"\n=== RAW EVENT STREAM ===\n")
            for event_log in response_events:
                f.write(event_log)
            f.write(f"\n=== END RESPONSE LOG ===\n")
        print(f"Response logged to: {response_log_filename}")
    except Exception as e:
        print(f"Failed to log response: {e}")


def process_new_message(prompt: str) -> None:
    message = Message(
        role="user",
        content=[MessageContentItem(TextContentItem(type="text", text=prompt))],
    )
    render_message(message)
    st.session_state.messages.append(message)

    with st.chat_message("assistant"):
        with st.spinner("Sending request..."):
            response = agent_run()
        st.markdown(
            f"```request_id: {response.headers.get('X-Snowflake-Request-Id')}```"
        )
        stream_events(response)


def render_message(msg: Message):
    with st.chat_message(msg.role):
        for content_item in msg.content:
            match content_item.actual_instance.type:
                case "text":
                    st.markdown(content_item.actual_instance.text)
                case "chart":
                    spec = json.loads(content_item.actual_instance.chart.chart_spec)
                    st.vega_lite_chart(spec, use_container_width=True)
                case "table":
                    data_array = np.array(
                        content_item.actual_instance.table.result_set.data
                    )
                    column_names = [
                        col.name
                        for col in content_item.actual_instance.table.result_set.result_set_meta_data.row_type
                    ]
                    st.dataframe(pd.DataFrame(data_array, columns=column_names))
                case _:
                    st.expander(content_item.actual_instance.type).json(
                        content_item.actual_instance.to_json()
                    )


st.title("Cortex Agents")

with st.sidebar:
    # Thread name input
    thread_name_input = st.text_input("Thread Name (optional)", placeholder="Enter custom thread name")
    
    # Start New Thread button with functionality
    if st.button("Start New Thread"):
        custom_name = thread_name_input.strip() if thread_name_input.strip() else None
        thread_data = clear_chat_session(custom_name)
        if thread_data:
            st.success(f"New thread created!")
            st.rerun()
    
    st.divider()
    
    # Retrieve Conversation section
    st.subheader("Retrieve Conversation")
    
    # Method 1: Direct thread ID input
    with st.expander("Load by Thread ID"):
        input_thread_id = st.number_input("Thread ID", min_value=1, step=1, format="%d")
        if st.button("Load Conversation"):
            if input_thread_id:
                if load_conversation_context(input_thread_id):
                    st.success(f"Loaded thread {input_thread_id}")
                    st.rerun()
                else:
                    st.error("Thread not found or failed to load")
    
    # Method 2: Select from recent threads
    with st.expander("Recent Threads"):
        recent_threads = get_user_threads()
        if recent_threads:
            for thread in recent_threads[:5]:  # Show last 5 threads
                thread_label = f"{thread['thread_name']} (ID: {thread['thread_id']}) - {thread['last_updated']}"
                if st.button(thread_label, key=f"load_{thread['thread_id']}"):
                    if load_conversation_context(thread['thread_id']):
                        st.success(f"Loaded: {thread['thread_name']}")
                        st.rerun()
        else:
            st.write("No recent threads found")
    
    st.divider()
    
    # Show current thread metadata if exists
    if hasattr(st.session_state, 'current_thread_data'):
        st.write(f"**Thread Data:** {st.session_state.current_thread_data}")
    
    # Session Data expandable panel at bottom
    with st.expander("Session Data"):
        if st.session_state:
            for key, value in st.session_state.items():
                st.write(f"**{key}**: {value}")
        else:
            st.write("No session data")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    render_message(message)

if user_input := st.chat_input("What is your question?"):
    process_new_message(prompt=user_input)