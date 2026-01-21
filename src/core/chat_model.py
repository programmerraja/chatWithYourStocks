from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from bson import ObjectId


class Message(BaseModel):

    role: str
    content: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    query_used: Optional[Any] = None
    data: Optional[List[Dict[str, Any]]] = None


class ChatSession(BaseModel):

    id: Optional[str] = Field(default=None, alias="_id")
    title: str = "New Chat"
    messages: List[Message] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

    def add_message(
        self,
        role: str,
        content: str,
        query_used: Optional[Any] = None,
        data: Optional[List[Dict[str, Any]]] = None,
    ):
        message = Message(role=role, content=content, query_used=query_used, data=data)
        self.messages.append(message)
        self.updated_at = datetime.utcnow()

        if role == "user" and len(self.messages) == 1:
            self.title = content

    def clear_messages(self):
        self.messages = []
        self.updated_at = datetime.utcnow()

    def to_dict(self):
        return {
            "title": self.title,
            "messages": [
                {
                    "role": m.role,
                    "content": m.content,
                    "timestamp": m.timestamp,
                    "query_used": m.query_used,
                    "data": m.data,
                }
                for m in self.messages
            ],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChatSession":
        messages = [Message(**msg) for msg in data.get("messages", [])]
        chat_id = data.get("_id")
        if isinstance(chat_id, ObjectId):
            chat_id = str(chat_id)

        return cls(
            id=chat_id,
            title=data.get("title", "New Chat"),
            messages=messages,
            created_at=data.get("created_at", datetime.utcnow()),
            updated_at=data.get("updated_at", datetime.utcnow()),
        )
