from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.database import Database
from pymongo.collection import Collection
from typing import Optional
import logging
from src.core.config import settings

logger = logging.getLogger(__name__)


class MongoDB:
    
    def __init__(self):
        self.client: Optional[MongoClient] = None
        self.db: Optional[Database] = None
        
    def connect(self):
        try:
            self.client = MongoClient(
                settings.mongodb_uri,
                serverSelectionTimeoutMS=5000
            )
            # Test connection
            self.client.server_info()
            self.db = self.client[settings.mongodb_database]
            logger.info(f"Connected to MongoDB: {settings.mongodb_database}")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise
    
    def disconnect(self):
        if self.client:
            self.client.close()
            logger.info("Disconnected from MongoDB")
    
    def get_collection(self, name: str) -> Collection:
        if self.db is None:
            raise RuntimeError("Database not connected")
        return self.db[name]
    
    @property
    def holdings(self) -> Collection:
        return self.get_collection("holdings")
    
    @property
    def trades(self) -> Collection:
        return self.get_collection("trades")
    
    @property
    def chat_sessions(self) -> Collection:
        return self.get_collection("chat_sessions")


mongodb = MongoDB()


def get_db() -> MongoDB:
    return mongodb
