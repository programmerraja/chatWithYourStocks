import re
from typing import Dict, Any, List
from src.core.config import settings


class QueryValidator:

    ALLOWED_COLLECTIONS = settings.allowed_collections
    ALLOWED_OPERATIONS = settings.allowed_operations
    MAX_EXECUTION_TIME = settings.max_execution_time_ms
    MAX_RESULTS = settings.max_result_size
    MAX_COMPLEXITY = settings.max_query_complexity

    BLOCKED_OPERATIONS = [
        "insert",
        "insertOne",
        "insertMany",
        "update",
        "updateOne",
        "updateMany",
        "delete",
        "deleteOne",
        "deleteMany",
        "drop",
        "dropDatabase",
        "createCollection",
        "createIndex",
        "dropIndex",
        "renameCollection",
    ]

    DANGEROUS_PATTERNS = [
        r"\$where",
        r"function\s*\(",
        r"eval\s*\(",
    ]

    def validate_collection(self, collection: str) -> bool:
        if collection not in self.ALLOWED_COLLECTIONS:
            raise ValueError(
                f"Invalid collection: {collection}. "
                f"Allowed collections: {', '.join(self.ALLOWED_COLLECTIONS)}"
            )
        return True

    def validate_operation(self, operation: str) -> bool:
        if operation not in self.ALLOWED_OPERATIONS:
            raise ValueError(
                f"Invalid operation: {operation}. "
                f"Allowed operations: {', '.join(self.ALLOWED_OPERATIONS)}"
            )
        if operation in self.BLOCKED_OPERATIONS:
            raise ValueError(f"Blocked operation: {operation}")
        return True

    def validate_query(self, query: Any) -> bool:
        query_str = str(query)

        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, query_str, re.IGNORECASE):
                raise ValueError(f"Query contains dangerous pattern: {pattern}")

        return True

    def estimate_complexity(
        self, operation: str, query: Any, options: Dict[str, Any] = None
    ) -> int:
        complexity = 0

        if operation == "aggregate":
            if isinstance(query, list):
                complexity = len(query)
        elif operation == "find":
            complexity = 1

        return complexity

    def validate_complexity(self, complexity: int) -> bool:
        if complexity > self.MAX_COMPLEXITY:
            raise ValueError(
                f"Query too complex. Maximum {self.MAX_COMPLEXITY} "
                f"stages allowed, got {complexity}"
            )
        return True

    def validate_tool_params(self, params: Dict[str, Any]) -> bool:
        collection = params.get("collection")
        operation = params.get("operation")
        query = params.get("query", {})
        options = params.get("options", {})

        self.validate_collection(collection)

        self.validate_operation(operation)

        self.validate_query(query)

        complexity = self.estimate_complexity(operation, query, options)
        self.validate_complexity(complexity)

        return True

    def apply_safety_limits(self, options: Dict[str, Any]) -> Dict[str, Any]:
        if options is None:
            options = {}

        if "limit" not in options:
            options["limit"] = self.MAX_RESULTS
        else:
            options["limit"] = min(options["limit"], self.MAX_RESULTS)

        options["maxTimeMS"] = self.MAX_EXECUTION_TIME

        return options


query_validator = QueryValidator()
