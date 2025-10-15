# backend/agent/agent.py
from typing import Any, Dict, Callable
from openai import OpenAI
from backend.core.settings import settings
from backend.agent.tools import retrieve_documents, check_policy
import json

client = OpenAI(api_key=settings.OPENAI_API_KEY)

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "retrieve_documents",
            "description": "Retrieve relevant document chunks for compliance questions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "top_k": {"type": "integer", "minimum": 1, "maximum": 12}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_policy",
            "description": "Check structured policy rows for a specific rule phrase (e.g., 'key rotation').",
            "parameters": {
                "type": "object",
                "properties": {
                    "rule": {"type": "string"}
                },
                "required": ["rule"]
            }
        }
    }
]

FN_MAP: Dict[str, Callable[..., Any]] = {
    "retrieve_documents": retrieve_documents,
    "check_policy": check_policy,
}

SYSTEM_PROMPT = (
    "You are an Agentic Knowledge Assistant for a regulated industry. "
    "Plan your steps; call tools as needed; cite sources when possible. "
    "If the answer is not supported by retrieved evidence, say you don't know."
)

def run_agent(question: str) -> Dict[str, Any]:
    messages: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]

    # Small loop is enough for demo
    for _ in range(6):
        resp = client.chat.completions.create(
            model=settings.ANSWER_MODEL,
            messages=messages,
            tools=TOOLS,           # tool calling (functions)
            tool_choice="auto",
            temperature=0.2,
        )
        choice = resp.choices[0]
        assistant_msg = choice.message

        # If the model asked to call tools:
        if assistant_msg.tool_calls and len(assistant_msg.tool_calls) > 0:
            # 1) Append the assistant message WITH tool_calls first (required by API)
            tool_calls_payload = []
            for tc in assistant_msg.tool_calls:
                tool_calls_payload.append({
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments or "{}",
                    },
                })
            messages.append({
                "role": "assistant",
                "content": assistant_msg.content or "",
                "tool_calls": tool_calls_payload,
            })

            # 2) Execute each tool and append a matching role="tool" message
            for tc in assistant_msg.tool_calls:
                fn = FN_MAP.get(tc.function.name)
                args = json.loads(tc.function.arguments or "{}")
                result = fn(**args) if fn else {"error": f"Unknown tool {tc.function.name}"}
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "name": tc.function.name,
                    "content": json.dumps(result),
                })

            # Go to next loop iteration so the model can read tool outputs
            continue

        # No tool calls => final answer
        if assistant_msg.content:
            return {"answer": assistant_msg.content}

    return {"answer": "I don't know."}
