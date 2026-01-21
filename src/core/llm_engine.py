"""LLM Engine using Google GenAI SDK with Automatic Function Calling."""

import logging
from typing import List, Dict, Any, Optional
import json
from google import genai
from google.genai import types
from src.core.config import settings
from src.prompts.system_prompt import get_system_prompt
from src.tools.mongodb_tool import execute_mongodb_query, MONGODB_TOOL_SCHEMA

logger = logging.getLogger(__name__)


class LLMEngine:

    def __init__(self):
        self.model = settings.llm_model
        self.temperature = settings.llm_temperature
        self.max_tokens = settings.llm_max_tokens
        self.system_prompt = get_system_prompt()

        self.client = genai.Client(api_key=settings.google_api_key)

    def _format_contents(
        self, user_query: str, history: Optional[List[Dict[str, str]]] = None
    ) -> List[types.Content]:
        contents = []

        if history:
            for msg in history:
                role = msg["role"]
                if role == "assistant":
                    role = "model"

                contents.append(
                    types.Content(
                        role=role, parts=[types.Part.from_text(text=msg["content"])]
                    )
                )

        contents.append(
            types.Content(role="user", parts=[types.Part.from_text(text=user_query)])
        )

        return contents

    def process_query(
        self, user_query: str, history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:

        try:
            current_history = self._format_contents(user_query, history)

            logger.info(f"Processing query: {user_query[:100]}...")

            mongodb_function = types.FunctionDeclaration(
                name="execute_mongodb_query",
                description="Execute MongoDB queries (find, aggregate, countDocuments, distinct)",
                parameters_json_schema=MONGODB_TOOL_SCHEMA,
            )

            tool = types.Tool(function_declarations=[mongodb_function])

            config = types.GenerateContentConfig(
                system_instruction=self.system_prompt,
                tools=[tool],
                temperature=0.1,
                max_output_tokens=self.max_tokens,
                automatic_function_calling=types.AutomaticFunctionCallingConfig(
                    disable=True,
                ),
            )

            max_turns = 5
            for turn in range(max_turns):
                logger.info(f"LLM Loop Turn: {turn + 1}")

                response = self.client.models.generate_content(
                    model=self.model, contents=current_history, config=config
                )

                function_call = None
                if (
                    response.candidates
                    and response.candidates[0].content
                    and response.candidates[0].content.parts
                ):
                    for part in response.candidates[0].content.parts:
                        if part.function_call:
                            function_call = part.function_call
                            break

                if function_call:
                    logger.info(
                        f"LLM requested tool: {function_call.name} with args: {function_call.args}"
                    )

                    current_history.append(response.candidates[0].content)

                    tool_result_json = "{}"
                    if function_call.name == "execute_mongodb_query":
                        args = function_call.args
                        if hasattr(args, "to_dict"):
                            args = args.to_dict()
                        elif not isinstance(args, dict):
                            try:
                                args = dict(args)
                            except Exception:
                                args = {}

                        tool_result_json = execute_mongodb_query(**args)
                    else:
                        tool_result_json = json.dumps(
                            {
                                "success": False,
                                "error": f"Unknown tool {function_call.name}",
                            }
                        )

                    response_part = types.Part.from_function_response(
                        name=function_call.name, response=json.loads(tool_result_json)
                    )

                    current_history.append(
                        types.Content(role="tool", parts=[response_part])
                    )

                    continue

                return {
                    "answer": response.text,
                    "success": True,
                    "data": None,
                    "query_used": "Handled internally",
                }

            return {
                "answer": "I apologize, but I couldn't complete the task within the maximum number of attempts limit.",
                "success": False,
                "error": "Max tool turns reached",
                "data": None,
                "query_used": None,
            }

        except Exception as e:
            logger.error(f"LLM processing failed: {e}")
            return {
                "answer": f"I encountered an error processing your query: {str(e)}",
                "success": False,
                "error": str(e),
                "data": None,
                "query_used": None,
            }


llm_engine = LLMEngine()


def get_llm_engine() -> LLMEngine:
    return llm_engine
