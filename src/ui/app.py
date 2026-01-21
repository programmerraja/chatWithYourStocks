import streamlit as st
from datetime import datetime
import json
from typing import Optional, List, Dict, Any
from bson import ObjectId
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.database import get_db
from src.core.llm_engine import get_llm_engine
from src.core.chat_model import ChatSession

import logging
from dotenv import load_dotenv

load_dotenv()


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)

st.set_page_config(
    page_title="Stock Trading Agent",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
    .user-message {
        padding: 10px;
        border-radius: 10px;
        margin: 5px 0;
    }
    .assistant-message {
        padding: 10px;
        border-radius: 10px;
        margin: 5px 0;
    }
    .query-box {
        background-color: #fff3e0;
        padding: 10px;
        border-radius: 5px;
        border-left: 3px solid #ff9800;
        margin: 10px 0;
        font-family: monospace;
        font-size: 12px;
    }
    .stButton>button {
        width: 100%;
    }
    .success-box {
        padding: 10px;
        border-radius: 5px;
        border-left: 3px solid #4caf50;
        margin: 10px 0;
    }
    .error-box {
        background-color: #ffebee;
        padding: 10px;
        border-radius: 5px;
        border-left: 3px solid #f44336;
        margin: 10px 0;
    }
</style>
""",
    unsafe_allow_html=True,
)


@st.cache_resource
def init_database():
    try:
        db = get_db()
        db.connect()
        return db
    except Exception as e:
        st.error(f"Failed to connect to database: {e}")
        st.stop()


if "current_chat_id" not in st.session_state:
    st.session_state.current_chat_id = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "chat_title" not in st.session_state:
    st.session_state.chat_title = "New Chat"
if "db_initialized" not in st.session_state:
    st.session_state.db = init_database()
    st.session_state.llm = get_llm_engine()
    st.session_state.db_initialized = True


def create_new_chat() -> Optional[str]:
    try:
        db = st.session_state.db
        chat_session = ChatSession()
        chat_dict = chat_session.to_dict()
        insert_result = db.chat_sessions.insert_one(chat_dict)
        return str(insert_result.inserted_id)
    except Exception as e:
        st.error(f"Error creating new chat: {e}")
        return None


def load_chat_history(chat_id: str) -> Optional[Dict[str, Any]]:
    try:
        db = st.session_state.db
        chat_doc = db.chat_sessions.find_one({"_id": ObjectId(chat_id)})
        if not chat_doc:
            return None

        chat_session = ChatSession.from_dict(chat_doc)
        return {
            "chat_id": chat_id,
            "title": chat_session.title,
            "messages": [
                {
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat(),
                    "query_used": msg.query_used,
                }
                for msg in chat_session.messages
            ],
        }
    except Exception as e:
        st.error(f"Error loading chat history: {e}")
        return None


def list_all_chats() -> List[Dict[str, Any]]:
    try:
        db = st.session_state.db
        chats = list(db.chat_sessions.find().sort("updated_at", -1))

        return [
            {
                "id": str(chat["_id"]),
                "title": chat.get("title", "New Chat"),
                "message_count": len(chat.get("messages", [])),
                "created_at": (
                    chat.get("created_at").isoformat()
                    if chat.get("created_at")
                    else None
                ),
                "updated_at": (
                    chat.get("updated_at").isoformat()
                    if chat.get("updated_at")
                    else None
                ),
            }
            for chat in chats
        ]
    except Exception as e:
        st.error(f"Error loading chats: {e}")
        return []


def delete_chat(chat_id: str) -> bool:
    try:
        db = st.session_state.db
        result = db.chat_sessions.delete_one({"_id": ObjectId(chat_id)})
        return result.deleted_count > 0
    except Exception as e:
        st.error(f"Error deleting chat: {e}")
        return False


def process_user_query(
    user_message: str, chat_id: Optional[str] = None
) -> Dict[str, Any]:
    try:
        db = st.session_state.db
        llm = st.session_state.llm

        if chat_id:
            chat_doc = db.chat_sessions.find_one({"_id": ObjectId(chat_id)})
            if not chat_doc:
                st.error("Chat session not found")
                return None
            chat_session = ChatSession.from_dict(chat_doc)
        else:
            chat_session = ChatSession()

        history = [
            {"role": msg.role, "content": msg.content} for msg in chat_session.messages
        ]

        result = llm.process_query(user_message, history)

        chat_session.add_message("user", user_message)
        chat_session.add_message(
            "assistant",
            result["answer"],
            query_used=result.get("query_used"),
            data=result.get("data"),
        )

        chat_dict = chat_session.to_dict()
        if chat_session.id:
            db.chat_sessions.update_one(
                {"_id": ObjectId(chat_session.id)}, {"$set": chat_dict}
            )
            final_chat_id = chat_session.id
        else:
            insert_result = db.chat_sessions.insert_one(chat_dict)
            final_chat_id = str(insert_result.inserted_id)

        return {
            "answer": result["answer"],
            "query_used": result.get("query_used"),
            "data": result.get("data"),
            "chat_id": final_chat_id,
            "success": result["success"],
        }

    except Exception as e:
        st.error(f"Error processing query: {e}")
        return {
            "answer": f"An error occurred: {str(e)}",
            "query_used": None,
            "data": None,
            "chat_id": chat_id,
            "success": False,
        }


with st.sidebar:
    st.title("📈 Stock Trading Agent")
    st.markdown("---")

    try:
        st.session_state.db.client.server_info()
        st.markdown(
            '<div class="success-box">🟢 Database Connected</div>',
            unsafe_allow_html=True,
        )
    except:
        st.markdown(
            '<div class="error-box">🔴 Database Disconnected</div>',
            unsafe_allow_html=True,
        )

    st.markdown("---")

    if st.button("➕ New Chat", use_container_width=True):
        chat_id = create_new_chat()
        if chat_id:
            st.session_state.current_chat_id = chat_id
            st.session_state.messages = []
            st.session_state.chat_title = "New Chat"
            st.rerun()

    st.markdown("---")

    st.subheader("💬 Chat History")
    chats = list_all_chats()

    if chats:
        for chat in chats:
            col1, col2 = st.columns([4, 1])
            with col1:
                display_title = chat["title"][:30]
                if len(chat["title"]) > 30:
                    display_title += "..."

                if st.button(
                    display_title, key=f"chat_{chat['id']}", use_container_width=True
                ):
                    history = load_chat_history(chat["id"])
                    if history:
                        st.session_state.current_chat_id = chat["id"]
                        st.session_state.chat_title = history["title"]
                        st.session_state.messages = history["messages"]
                        st.rerun()
            with col2:
                if st.button("🗑️", key=f"delete_{chat['id']}"):
                    if delete_chat(chat["id"]):
                        if st.session_state.current_chat_id == chat["id"]:
                            st.session_state.current_chat_id = None
                            st.session_state.messages = []
                            st.session_state.chat_title = "New Chat"
                        st.rerun()
    else:
        st.info("No chat history yet. Start a new chat!")

    st.markdown("---")

    st.subheader("💡 Example Queries")
    examples = [
        "How many active holdings do we have?",
        "Show me the top 10 holdings by market value",
        "What's the total YTD P&L across all portfolios?",
        "List recent trades from the last week",
        "What types of securities do we hold?",
        "Show me the distribution of long vs short positions",
        "Which portfolios have the best MTD performance?",
        "Count the number of trades by type",
    ]

    for example in examples:
        if st.button(example, key=f"ex_{example[:20]}", use_container_width=True):
            st.session_state.example_query = example
            st.rerun()


st.title(st.session_state.chat_title)

for message in st.session_state.messages:
    role = message["role"]
    content = message.get("content")

    # Skip messages with None content (function call intermediates)
    if not content:
        continue

    if role == "user":
        st.markdown(
            f'<div class="user-message"><b>You:</b><br>{content}</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div class="assistant-message"><b>Assistant:</b><br>{content}</div>',
            unsafe_allow_html=True,
        )

        if message.get("query_used"):
            with st.expander("🔍 View MongoDB Query"):
                st.code(message["query_used"], language="json")


if "example_query" in st.session_state:
    user_input = st.session_state.example_query
    del st.session_state.example_query

    st.session_state.messages.append(
        {"role": "user", "content": user_input, "timestamp": datetime.now().isoformat()}
    )

    with st.spinner("🤔 Thinking..."):
        result = process_user_query(user_input, st.session_state.current_chat_id)

    if result:
        if not st.session_state.current_chat_id:
            st.session_state.current_chat_id = result["chat_id"]

        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": result["answer"],
                "timestamp": datetime.now().isoformat(),
                "query_used": result.get("query_used"),
            }
        )

        if len(st.session_state.messages) == 2:
            st.session_state.chat_title = user_input[:50] + (
                "..." if len(user_input) > 50 else ""
            )

    st.rerun()

user_input = st.chat_input("Ask a question about your stock holdings and trades...")

if user_input:
    st.session_state.messages.append(
        {"role": "user", "content": user_input, "timestamp": datetime.now().isoformat()}
    )

    with st.spinner("🤔 Thinking..."):
        result = process_user_query(user_input, st.session_state.current_chat_id)

    if result:
        if not st.session_state.current_chat_id:
            st.session_state.current_chat_id = result["chat_id"]

        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": result["answer"],
                "timestamp": datetime.now().isoformat(),
                "query_used": result.get("query_used"),
            }
        )

        if len(st.session_state.messages) == 2:
            st.session_state.chat_title = user_input[:50] + (
                "..." if len(user_input) > 50 else ""
            )

        st.rerun()

st.markdown("---")
