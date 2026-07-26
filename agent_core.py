from __future__ import annotations

import asyncio
import os
from typing import Any

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.messages import AIMessage
from langchain_core.messages import HumanMessage
from langchain_core.messages import ToolMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.checkpoint.memory import InMemorySaver

load_dotenv()

MCP_SERVER_URL = os.getenv(
    "MCP_SERVER_URL",
    "http://127.0.0.1:8000/mcp",
)

OPENAI_MODEL = os.getenv(
    "OPENAI_MODEL",
    "gpt-5.4-nano",
)

memory = InMemorySaver()

SYSTEM_PROMPT = """
Eres un asistente especializado en el seguimiento de compras y pagos.

Debes utilizar exclusivamente las tools MCP para consultar o modificar
información del sistema.

Reglas obligatorias:

1. No inventes folios, proveedores, importes, estados o fechas.
2. Si una respuesta depende de la base de datos, usa una tool.
3. Antes de cualquier escritura:
   - reúne todos los datos obligatorios;
   - resume exactamente la operación;
   - pregunta al usuario si confirma.
4. No llames una tool de escritura con confirmar=true hasta recibir una
   confirmación explícita en el siguiente turno.
5. Una confirmación solo autoriza la acción inmediatamente anterior.
6. No permitas actualización ni eliminación.
7. No permitas pagos parciales.
8. Explica claramente los errores devueltos por las tools.
9. Mantén referencias como "esa requisición", "el proveedor anterior",
   "esa factura" o "su vencimiento".
10. Al finalizar, menciona de forma breve qué tools utilizaste.
"""


def content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts: list[str] = []

        for block in content:
            if isinstance(block, dict):
                text = block.get("text")
                if text:
                    parts.append(text)
            else:
                parts.append(str(block))

        return "\n".join(parts)

    return str(content)


def extract_current_messages(
    messages: list,
    prompt: str,
) -> list:
    last_user_index = -1

    for index, message in enumerate(messages):
        if (
            isinstance(message, HumanMessage)
            and content_to_text(message.content) == prompt
        ):
            last_user_index = index

    return messages[last_user_index + 1 :]


def build_trace(messages: list) -> list[dict]:
    trace: list[dict] = []

    for message in messages:
        if isinstance(message, AIMessage):
            for tool_call in message.tool_calls:
                trace.append(
                    {
                        "tipo": "tool_call",
                        "tool": tool_call.get("name"),
                        "argumentos": tool_call.get("args"),
                        "tool_call_id": tool_call.get("id"),
                    }
                )

        if isinstance(message, ToolMessage):
            trace.append(
                {
                    "tipo": "tool_result",
                    "tool": getattr(message, "name", None),
                    "tool_call_id": message.tool_call_id,
                    "resultado": content_to_text(
                        message.content
                    ),
                }
            )

    return trace


async def run_agent_async(
    prompt: str,
    session_id: str,
) -> dict:
    client = MultiServerMCPClient(
        {
            "compras": {
                "transport": "http",
                "url": MCP_SERVER_URL,
            }
        }
    )

    tools = await client.get_tools()

    agent = create_agent(
        model=f"openai:{OPENAI_MODEL}",
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
        checkpointer=memory,
    )

    config = {
        "configurable": {
            "thread_id": session_id,
        }
    }

    result = await agent.ainvoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ]
        },
        config=config,
    )

    all_messages = result["messages"]
    current_messages = extract_current_messages(
        all_messages,
        prompt,
    )

    final_message = all_messages[-1]

    return {
        "answer": content_to_text(final_message.content),
        "trace": build_trace(current_messages),
    }


def run_agent(
    prompt: str,
    session_id: str,
) -> dict:
    return asyncio.run(
        run_agent_async(
            prompt=prompt,
            session_id=session_id,
        )
    )