"""LLM Engine using OpenAI SDK with Automatic Function Calling."""

import logging
from typing import List, Dict, Any, Optional
import json
from openai import OpenAI
from src.core.config import settings
from src.prompts.system_prompt import get_system_prompt
from src.tools.mongodb_tool import execute_mongodb_query, MONGODB_TOOL_SCHEMA
from src.tools.calculator_tool import execute_calculator, CALCULATOR_TOOL_SCHEMA

logger = logging.getLogger(__name__)


class LLMEngine:

    def __init__(self):
        self.model = settings.llm_model
        self.temperature = settings.llm_temperature
        self.max_tokens = settings.llm_max_tokens
        self.system_prompt = get_system_prompt()

        self.client = OpenAI(api_key=settings.openai_api_key)

    def _format_messages(
        self, user_query: str, history: Optional[List[Dict[str, str]]] = None
    ) -> List[Dict[str, str]]:
        messages = [{"role": "system", "content": self.system_prompt}]

        if history:
            for msg in history:
                role = msg["role"]
                if role == "model":  # Handle legacy role name if any
                    role = "assistant"
                messages.append({"role": role, "content": msg["content"]})

        messages.append({"role": "user", "content": user_query})
        return messages

    def process_query(
        self, user_query: str, history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:

        try:
            current_messages = self._format_messages(user_query, history)

            logger.info(f"Processing query: {user_query[:100]}...")

            tools = [MONGODB_TOOL_SCHEMA, CALCULATOR_TOOL_SCHEMA]

            queries_used = []
            max_turns = 5
            for turn in range(max_turns):
                logger.info(f"LLM Loop Turn: {turn + 1}")

                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=current_messages,
                    tools=tools,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                )

                response_message = response.choices[0].message

                # Check if the model wants to call a tool
                if response_message.tool_calls:
                    current_messages.append(
                        response_message
                    )  # append the assistant's message with tool_calls

                    for tool_call in response_message.tool_calls:
                        function_name = tool_call.function.name
                        function_args = json.loads(tool_call.function.arguments)

                        logger.info(
                            f"LLM requested tool: {function_name} with args: {function_args}"
                        )

                        tool_result_json = "{}"
                        if function_name == "execute_mongodb_query":
                            formatted_query = json.dumps(function_args, indent=2)
                            queries_used.append(formatted_query)
                            tool_result_json = execute_mongodb_query(**function_args)
                        elif function_name == "execute_calculator":
                            tool_result_json = execute_calculator(**function_args)
                        else:
                            tool_result_json = json.dumps(
                                {
                                    "success": False,
                                    "error": f"Unknown tool {function_name}",
                                }
                            )

                        current_messages.append(
                            {
                                "tool_call_id": tool_call.id,
                                "role": "tool",
                                "name": function_name,
                                "content": tool_result_json,
                            }
                        )
                    continue

                # If no tool calls, return the answer
                return {
                    "answer": response_message.content,
                    "success": True,
                    "data": None,
                    "query_used": queries_used if queries_used else None,
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
