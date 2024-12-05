import json
import os
from datetime import datetime
from enum import Enum
from typing import Dict, Optional

import redis
from dotenv import load_dotenv


class ProcessingStatus(Enum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    STORING_DOCUMENT = "STORING_DOCUMENT"
    CONTEXTUALIZING = "CONTEXTUALIZING"
    CREATING_EMBEDDINGS = "CREATING_EMBEDDINGS"
    STORING_VECTORS = "STORING_VECTORS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


if os.path.exists(".env"):
    load_dotenv()

REDIS_URL = os.getenv("REDIS_URL")
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")


class StatusTracker:
    def __init__(self):
        self.redis_client = redis.Redis(
            host=REDIS_URL,
            port=6379,
            password=REDIS_PASSWORD,
            ssl=True,
            decode_responses=True
        )

    def _get_key(self, user_id: str, document_id: str) -> str:
        return f"doc_status:{user_id}:{document_id}"

    def create_status(self, user_id: str, document_id: str, document_title: str) -> None:
        """Initialize status for a new document"""
        status_data = {
            "document_id": document_id,
            "title": document_title,
            "status": ProcessingStatus.QUEUED.value,
            "progress": 0,
            "start_time": datetime.utcnow().isoformat(),
            "last_updated": datetime.utcnow().isoformat(),
            "error": None
        }
        self.redis_client.set(
            self._get_key(user_id, document_id),
            json.dumps(status_data)
        )

    def update_status(
        self,
        user_id: str,
        document_id: str,
        status: ProcessingStatus,
        progress: Optional[float] = None,
        error: Optional[str] = None
    ) -> None:
        """Update processing status for a document"""
        key = self._get_key(user_id, document_id)
        current_data = json.loads(self.redis_client.get(key))

        current_data.update({
            "status": status.value,
            "last_updated": datetime.utcnow().isoformat()
        })

        if progress is not None:
            current_data["progress"] = progress

        if error is not None:
            current_data["error"] = error

        ttl = 60 * 60  # 1 hour
        if current_data.get("status") == ProcessingStatus.COMPLETED.value:
            ttl = 10 * 60
        self.redis_client.set(key, json.dumps(current_data), ex=ttl)

    def get_status(self, user_id: str, document_id: str) -> Dict:
        """Get current status of a document"""
        key = self._get_key(user_id, document_id)
        data = self.redis_client.get(key)
        return json.loads(data) if data else None

    def get_all_user_statuses(self, user_id: str) -> list[Dict]:
        """Get status of all documents for a user"""
        pattern = f"doc_status:{user_id}:*"
        keys = self.redis_client.keys(pattern)
        statuses = []
        for key in keys:
            data = self.redis_client.get(key)
            if data:
                statuses.append(json.loads(data))
        return statuses


TRACKER = StatusTracker()
