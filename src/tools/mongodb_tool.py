"""MongoDB query tool for LLM function calling."""

import logging
from typing import Dict, Any, List, Union, Optional
from datetime import datetime
from bson import json_util
import json
from src.core.database import get_db
from src.core.query_validator import query_validator

logger = logging.getLogger(__name__)

# Schema dictionary kept for reference or backup, but AFC will infer from function
MONGODB_TOOL_SCHEMA = {
    "type": "object",
    "properties": {
        "collection": {
            "type": "string",
            "description": "Collection name: 'holdings' or 'trades'",
        },
        "operation": {
            "type": "string",
            "enum": ["find", "aggregate", "countDocuments", "distinct"],
            "description": "MongoDB operation type",
        },
        "query": {
            "type": "array",
            "description": "for find/count/distinct: query filter object inside array; for aggregate: aggregation pipeline stages",
            "items": {"type": "object"},
        },
        "options": {
            "type": "object",
            "nullable": True,
            "description": "Query options (sort, limit, skip, projection)",
        },
        "field": {
            "type": "string",
            "nullable": True,
            "description": "Field for distinct operation",
        },
    },
    "required": ["collection", "operation", "query"],
}


def execute_mongodb_query(
    collection: str,
    operation: str,
    query: Dict,
    options: Optional[Dict[str, Any]] = None,
    field: Optional[str] = None,
) -> str:
    try:
        params = {
            "collection": collection,
            "operation": operation,
            "query": query,
            "options": options or {},
        }
        query_validator.validate_tool_params(params)

        options = query_validator.apply_safety_limits(options or {})

        db = get_db()
        coll = db.get_collection(collection)

        results = []
        count = 0

        if operation == "find":
            cursor = coll.find(
                query[0] if isinstance(query, list) else query,
                options.get("projection"),
            )
            if "sort" in options:
                cursor = cursor.sort(list(options["sort"].items()))
            if "limit" in options:
                cursor = cursor.limit(options["limit"])
            if "skip" in options:
                cursor = cursor.skip(options["skip"])

            results = list(cursor)
            count = len(results)

        elif operation == "aggregate":
            pipeline = query if isinstance(query, list) else [query]

            normalized_pipeline = []
            for i, stage in enumerate(pipeline):
                if isinstance(stage, str):
                    try:
                        parsed_stage = json.loads(stage)
                        logger.info(
                            f"Converted pipeline stage {i} from JSON string to dict"
                        )
                        normalized_pipeline.append(parsed_stage)
                    except json.JSONDecodeError:
                        raise ValueError(
                            f"Pipeline stage {i} is an invalid JSON string. "
                            f"Each stage must be a valid dictionary/object or JSON string."
                        )
                elif not isinstance(stage, dict):
                    raise ValueError(
                        f"Pipeline stage {i} must be a dictionary/object, got {type(stage).__name__}"
                    )
                else:
                    normalized_pipeline.append(stage)

            pipeline = normalized_pipeline

            has_limit = any("$limit" in stage for stage in pipeline)
            if not has_limit:
                pipeline.append({"$limit": options.get("limit", 1000)})

            results = list(coll.aggregate(pipeline))
            count = len(results)

        elif operation == "countDocuments":
            count = coll.count_documents(query if isinstance(query, list) else query)
            results = [{"count": count}]

        elif operation == "distinct":
            if not field:
                raise ValueError("Field name required for distinct operation")
            values = coll.distinct(field, query if isinstance(query, list) else query)
            results = [{"values": values, "count": len(values)}]
            count = len(values)

        results_json = json.loads(json_util.dumps(results))

        # Log to verifying execution is happening
        logger.warning(f"EXECUTING MONGODB TOOL: {collection}.{operation}")
        print(f"DEBUG: Executing MongoDB Tool: {collection}.{operation}", flush=True)

        logger.info(
            f"Query executed successfully: {collection}.{operation}, "
            f"returned {count} results"
        )

        response_dict = {
            "success": True,
            "data": results_json,
            "count": count,
            "query_info": {
                "collection": collection,
                "operation": operation,
                "executed_at": datetime.utcnow().isoformat(),
            },
        }

        # Return as JSON string to ensure SDK handles it correctly
        return json.dumps(response_dict)

    except ValueError as e:
        logger.warning(f"Query validation failed: {e}")
        return json.dumps({"success": False, "error": str(e), "data": [], "count": 0})

    except Exception as e:
        logger.error(f"Query execution failed: {e}")
        return json.dumps(
            {
                "success": False,
                "error": f"Query execution failed: {str(e)}",
                "data": [],
                "count": 0,
            }
        )


def get_tool_schema() -> Dict[str, Any]:
    """Get the MongoDB tool schema for LLM function calling."""
    return MONGODB_TOOL_SCHEMA
