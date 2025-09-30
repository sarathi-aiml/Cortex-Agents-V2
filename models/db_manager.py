import os
from snowflake.snowpark import Session
import streamlit as st
from dotenv import load_dotenv

load_dotenv('env.dev')

def get_session():
    """Get Snowflake session using PAT"""
    connection_parameters = {
        "account": os.getenv("SNOWFLAKE_ACCOUNT"),
        "user": os.getenv("SNOWFLAKE_USER"),
      
        "password": os.getenv("SNOWFLAKE_PASSWORD"),
        "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE"),
        "database": os.getenv("SNOWFLAKE_DATABASE"),
        "schema": os.getenv("SNOWFLAKE_SCHEMA")
    }
    return Session.builder.configs(connection_parameters).create()

def save_thread_info(thread_id, thread_name, parent_message_id, user_id="default_user", message_content=None, message_role=None, message_json=None, response_json=None):
    """Save or update thread information with message content and complete JSON structures"""
    session = get_session()

    thread_name = thread_name or f"Thread_{thread_id}"
    message_content = message_content or ''
    message_role = message_role or ''
    message_json = message_json or ''
    response_json = response_json or ''

    # Use Snowpark DataFrame with proper JSON handling - no SQL escaping issues
    import json

    # Parse JSON to Python objects for proper VARIANT storage
    message_json_obj = None
    response_json_obj = None

    if message_json and message_json != '':
        try:
            if isinstance(message_json, str):
                message_json_obj = json.loads(message_json)
            else:
                message_json_obj = message_json
        except Exception as e:
            print(f"Error parsing message_json: {e}")
            message_json_obj = None

    if response_json and response_json != '':
        try:
            if isinstance(response_json, str):
                response_json_obj = json.loads(response_json)
            else:
                response_json_obj = response_json
        except Exception as e:
            print(f"Error parsing response_json: {e}")
            response_json_obj = None

    # Create DataFrame with only the columns we want to insert
    # This avoids the column count mismatch by not including auto-generated columns
    from snowflake.snowpark.types import StructType, StructField, StringType, IntegerType, VariantType, BooleanType

    # Define schema for our 12 columns (excluding ID, CREATED_AT, LAST_UPDATED, IS_ACTIVE)
    schema = StructType([
        StructField("THREAD_ID", IntegerType()),
        StructField("THREAD_NAME", StringType()),
        StructField("PARENT_MESSAGE_ID", IntegerType()),
        StructField("USER_ID", StringType()),
        StructField("SESSION_ID", StringType()),
        StructField("AGENT_NAME", StringType()),
        StructField("DATABASE_NAME", StringType()),
        StructField("SCHEMA_NAME", StringType()),
        StructField("MESSAGE_CONTENT", StringType()),
        StructField("MESSAGE_ROLE", StringType()),
        StructField("MESSAGE_JSON", VariantType()),
        StructField("RESPONSE_JSON", VariantType())
    ])

    # Create data row
    data = [(
        thread_id,
        thread_name,
        parent_message_id,
        user_id,
        'session_001',
        'SALES_INTELLIGENCE_AGENT',
        'SNOWFLAKE_INTELLIGENCE',
        'DATA',
        message_content,
        message_role,
        message_json_obj,
        response_json_obj
    )]

    # Create DataFrame
    df = session.create_dataframe(data, schema)

    # Write to a temp table first, then insert into main table to avoid column mismatch
    temp_table_name = f"TEMP_CONVERSATION_INSERT_{thread_id}_{parent_message_id}"

    # Save to temp table
    df.write.mode("overwrite").save_as_table(temp_table_name)

    # Insert from temp table to main table (this way Snowflake handles the missing columns)
    session.sql(f"""
        INSERT INTO CONVERSATION_TRACKING (
            THREAD_ID, THREAD_NAME, PARENT_MESSAGE_ID, USER_ID, SESSION_ID,
            AGENT_NAME, DATABASE_NAME, SCHEMA_NAME, MESSAGE_CONTENT, MESSAGE_ROLE,
            MESSAGE_JSON, RESPONSE_JSON
        )
        SELECT
            THREAD_ID, THREAD_NAME, PARENT_MESSAGE_ID, USER_ID, SESSION_ID,
            AGENT_NAME, DATABASE_NAME, SCHEMA_NAME, MESSAGE_CONTENT, MESSAGE_ROLE,
            MESSAGE_JSON, RESPONSE_JSON
        FROM {temp_table_name}
    """).collect()

    # Clean up temp table
    session.sql(f"DROP TABLE {temp_table_name}").collect()

    session.close()

def get_thread_info(thread_id, user_id="default_user"):
    """Get thread information for continuation - get LATEST parent_message_id"""
    session = get_session()

    # Get the latest parent_message_id for this thread (highest value)
    result = session.sql(f"""
        SELECT THREAD_ID, THREAD_NAME, MAX(PARENT_MESSAGE_ID) as LATEST_PARENT_MESSAGE_ID
        FROM CONVERSATION_TRACKING
        WHERE THREAD_ID = {thread_id} AND USER_ID = '{user_id}'
        GROUP BY THREAD_ID, THREAD_NAME
    """).collect()

    session.close()

    if result:
        row = result[0]
        return {
            'thread_id': row[0],
            'thread_name': row[1],
            'parent_message_id': row[2]  # This is now the MAX/latest parent_message_id
        }
    return None

def get_user_threads(user_id="default_user"):
    """Get list of user's recent threads"""
    session = get_session()

    results = session.sql(f"""
        SELECT THREAD_ID, THREAD_NAME, PARENT_MESSAGE_ID, LAST_UPDATED
        FROM (
            SELECT THREAD_ID, THREAD_NAME, PARENT_MESSAGE_ID, LAST_UPDATED,
                   ROW_NUMBER() OVER (PARTITION BY THREAD_ID ORDER BY LAST_UPDATED DESC) as rn
            FROM CONVERSATION_TRACKING
            WHERE USER_ID = '{user_id}'
        )
        WHERE rn = 1
        ORDER BY LAST_UPDATED DESC
        LIMIT 5
    """).collect()
    
    session.close()
    
    threads = []
    for row in results:
        threads.append({
            'thread_id': row[0],
            'thread_name': row[1],
            'parent_message_id': row[2],
            'last_updated': row[3]
        })
    
    return threads

def get_thread_messages(thread_id, user_id="default_user"):
    """Get all messages for a specific thread in chronological order with JSON data"""
    session = get_session()

    results = session.sql(f"""
        SELECT MESSAGE_ROLE, MESSAGE_CONTENT, MESSAGE_JSON, RESPONSE_JSON, LAST_UPDATED
        FROM CONVERSATION_TRACKING
        WHERE THREAD_ID = {thread_id} AND USER_ID = '{user_id}'
        AND MESSAGE_ROLE IS NOT NULL AND MESSAGE_CONTENT IS NOT NULL
        AND MESSAGE_ROLE != '' AND MESSAGE_CONTENT != ''
        ORDER BY LAST_UPDATED ASC
    """).collect()

    session.close()

    messages = []
    for row in results:
        messages.append({
            'role': row[0],
            'content': row[1],
            'message_json': row[2],
            'response_json': row[3],
            'timestamp': row[4]
        })

    return messages

def load_conversation_context(thread_id, user_id="default_user"):
    """Load conversation context for thread continuation with display history"""
    from models import Message, MessageContentItem, TextContentItem

    thread_info = get_thread_info(thread_id, user_id)

    if thread_info:
        # Set thread context for continuation
        st.session_state.current_thread_id = thread_info['thread_id']
        st.session_state.parent_message_id = thread_info['parent_message_id']
        st.session_state.current_thread_data = {
            'thread_id': thread_info['thread_id'],
            'thread_name': thread_info['thread_name'],
            'origin_application': 'cortex_agent'
        }

        # Load conversation history for DISPLAY ONLY (not for sending to API)
        thread_messages = get_thread_messages(thread_id, user_id)
        display_messages = []

        for msg in thread_messages:
            # Try to reconstruct from clean JSON first, fallback to text
            if msg['message_json'] and msg['message_json'] != '':
                try:
                    import json
                    message_data = json.loads(str(msg['message_json'])) if isinstance(msg['message_json'], str) else msg['message_json']
                    message = Message.from_json(json.dumps(message_data))
                    display_messages.append(message)
                except Exception as e:
                    print(f"Failed to parse message JSON: {e}, falling back to text")
                    # Fallback to text-based message
                    message = Message(
                        role=msg['role'],
                        content=[MessageContentItem(TextContentItem(type="text", text=msg['content']))]
                    )
                    display_messages.append(message)
            else:
                # Fallback to text-based message
                message = Message(
                    role=msg['role'],
                    content=[MessageContentItem(TextContentItem(type="text", text=msg['content']))]
                )
                display_messages.append(message)

        # Set messages for DISPLAY only - new messages will still be sent individually with thread_id
        st.session_state.messages = display_messages

        # Reset message tracking
        st.session_state.current_user_message_id = None
        st.session_state.current_assistant_message_id = None
        st.session_state.message_ids_history = []

        print(f"Loaded thread {thread_id} with {len(display_messages)} messages for display - Server maintains conversation context")
        return True

    return False