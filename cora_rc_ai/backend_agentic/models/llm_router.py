import os
import httpx
import json
import logging
from typing import AsyncGenerator, List, Dict, Any, Optional
from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai.types import Content, Part, FunctionCall

logger = logging.getLogger(__name__)


def _convert_schema(schema) -> Dict[str, Any]:
    """Convert a google.genai Schema into an OpenAI/JSON-Schema dict."""
    if schema is None:
        return {"type": "object", "properties": {}}
    result: Dict[str, Any] = {}
    t = getattr(schema, "type", None)
    if t is not None:
        type_str = t.value if hasattr(t, "value") else str(t)
        result["type"] = type_str.lower()
    if getattr(schema, "description", None):
        result["description"] = schema.description
    if getattr(schema, "enum", None):
        result["enum"] = list(schema.enum)
    props = getattr(schema, "properties", None)
    if props:
        result["properties"] = {k: _convert_schema(v) for k, v in props.items()}
    if getattr(schema, "required", None):
        result["required"] = list(schema.required)
    items = getattr(schema, "items", None)
    if items is not None:
        result["items"] = _convert_schema(items)
    if "type" not in result:
        result["type"] = "object"
    return result


def _build_openai_tools(llm_request: LlmRequest) -> Optional[List[Dict[str, Any]]]:
    """Translate ADK tool declarations into the OpenAI `tools` payload."""
    config = getattr(llm_request, "config", None)
    if not config or not getattr(config, "tools", None):
        return None
    tools: List[Dict[str, Any]] = []
    for tool in config.tools:
        for fd in getattr(tool, "function_declarations", None) or []:
            tools.append({
                "type": "function",
                "function": {
                    "name": fd.name,
                    "description": getattr(fd, "description", "") or "",
                    "parameters": _convert_schema(getattr(fd, "parameters", None)),
                },
            })
    return tools or None


def _tool_calls_to_parts(tool_calls: List[Dict[str, Any]]) -> List[Part]:
    """Convert raw OpenAI tool_calls into ADK FunctionCall parts."""
    parts: List[Part] = []
    for tc in tool_calls:
        fn = tc.get("function", {}) or {}
        raw_args = fn.get("arguments") or "{}"
        try:
            args = json.loads(raw_args) if isinstance(raw_args, str) else dict(raw_args)
        except json.JSONDecodeError:
            logger.warning(f"Could not parse tool arguments: {raw_args}")
            args = {}
        parts.append(
            Part(function_call=FunctionCall(id=tc.get("id"), name=fn.get("name"), args=args))
        )
    return parts


class OpenSourceLlmRouter(BaseLlm):
    """
    Adapter subclassing Google ADK's BaseLlm to route inference requests
    to a local open-source LLM server (like Ollama or vLLM).
    """
    #model: str = "llama3.2:3b"
    model: str = "llama3.1:8b"

    @classmethod
    def supported_models(cls) -> list[str]:
        return [r".*"]

    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:
        api_base = os.getenv("OLLAMA_API_BASE", "http://localhost:11434/v1")
        model_name = os.getenv("OLLAMA_MODEL", self.model)
        request_timeout = float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "180"))
        
        # Prepare system instruction
        system_instructions = ""
        if llm_request.config and llm_request.config.system_instruction:
            si = llm_request.config.system_instruction
            logger.info(f"System instructions: {si}")
            if isinstance(si, str):
                system_instructions = si
            elif hasattr(si, "parts"):
                system_instructions = "\n".join(p.text for p in si.parts if p.text)
            else:
                system_instructions = str(si)
            logger.info(f"Processed system instructions: {system_instructions}")

        
        # Map Google ADK Content objects to OpenAI API standard messages
        messages = []
        if system_instructions:
            messages.append({"role": "system", "content": system_instructions})

        for content in llm_request.contents:
            role = "assistant" if content.role == "model" else "user"
            text_parts: List[str] = []
            tool_calls: List[Dict[str, Any]] = []
            tool_result_msgs: List[Dict[str, Any]] = []
            for p in content.parts:
                if getattr(p, "text", None):
                    text_parts.append(p.text)
                fc = getattr(p, "function_call", None)
                if fc is not None:
                    tool_calls.append({
                        "id": fc.id or f"call_{fc.name}",
                        "type": "function",
                        "function": {
                            "name": fc.name,
                            "arguments": json.dumps(fc.args or {}),
                        },
                    })
                fr = getattr(p, "function_response", None)
                if fr is not None:
                    resp = fr.response
                    tool_result_msgs.append({
                        "role": "tool",
                        "tool_call_id": fr.id or f"call_{fr.name}",
                        "content": resp if isinstance(resp, str) else json.dumps(resp, default=str),
                    })
            logger.info(f"Content parts for role {role}: {text_parts}")
            if tool_calls:
                messages.append({
                    "role": "assistant",
                    "content": "\n".join(text_parts) or None,
                    "tool_calls": tool_calls,
                })
            elif text_parts:                            # skip empty turns
                messages.append({"role": role, "content": "\n".join(text_parts)})
            # Tool results must follow the assistant tool_call message
            messages.extend(tool_result_msgs)

        headers = {"Content-Type": "application/json"}
        payload = {
            "model": model_name,
            "messages": messages,
            "stream": stream,
            "temperature": llm_request.config.temperature if llm_request.config and llm_request.config.temperature is not None else 0.1
        }
        openai_tools = _build_openai_tools(llm_request)
        if openai_tools:
            payload["tools"] = openai_tools
            payload["tool_choice"] = "auto"
        logger.info(f"Payload being sent: {json.dumps(payload, default=str)}")
        logger.info(f"Routing LLM request to: {api_base}/chat/completions (model: {model_name})")
        
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            if stream:
                try:
                    async with client.stream(
                        "POST", f"{api_base}/chat/completions", json=payload, headers=headers
                    ) as response:
                        if response.status_code != 200:
                            err_text = await response.aread()
                            yield LlmResponse(
                                error_code=str(response.status_code),
                                error_message=f"LLM API Error: {err_text.decode('utf-8', errors='ignore')}",
                                partial=False
                            )
                            return
                            
                        accumulated_text = ""
                        tool_calls_acc: Dict[int, Dict[str, Any]] = {}
                        async for line in response.iter_lines():
                            if not line.strip():
                                continue
                            if line.startswith("data: "):
                                data_str = line[6:]
                                if data_str.strip() == "[DONE]":
                                    break
                                try:
                                    data = json.loads(data_str)
                                    choice = data["choices"][0]
                                    delta = choice.get("delta", {})
                                    content_chunk = delta.get("content", "")
                                    if content_chunk:
                                        accumulated_text += content_chunk
                                        # Yield partial chunk response
                                        yield LlmResponse(
                                            content=Content(role="model", parts=[Part.from_text(text=content_chunk)]),
                                            partial=True
                                        )
                                    for tc in delta.get("tool_calls", []) or []:
                                        idx = tc.get("index", 0)
                                        entry = tool_calls_acc.setdefault(
                                            idx, {"id": None, "function": {"name": "", "arguments": ""}}
                                        )
                                        if tc.get("id"):
                                            entry["id"] = tc["id"]
                                        fn = tc.get("function", {}) or {}
                                        if fn.get("name"):
                                            entry["function"]["name"] = fn["name"]
                                        if fn.get("arguments"):
                                            entry["function"]["arguments"] += fn["arguments"]
                                except Exception as e:
                                    logger.error(f"Error parsing streaming token: {e}")

                        # If the model requested tool calls, emit them and stop
                        if tool_calls_acc:
                            ordered = [tool_calls_acc[i] for i in sorted(tool_calls_acc)]
                            yield LlmResponse(
                                content=Content(role="model", parts=_tool_calls_to_parts(ordered)),
                                partial=False,
                                turn_complete=True
                            )
                            return

                        # Yield the final complete response
                        yield LlmResponse(
                            content=Content(role="model", parts=[Part.from_text(text=accumulated_text)]),
                            partial=False,
                            turn_complete=True
                        )
                except Exception as e:
                    msg = str(e) or repr(e) or "Unknown streaming error"
                    logger.exception(f"Exception during LLM stream: {msg}")
                    yield LlmResponse(error_code="STREAM_ERROR", error_message=msg, partial=False)
            else:
                try:
                    res = await client.post(f"{api_base}/chat/completions", json=payload, headers=headers)
                    if res.status_code != 200:
                        yield LlmResponse(
                            error_code=str(res.status_code),
                            error_message=f"LLM API Error: {res.text}",
                            partial=False
                        )
                        return
                    data = res.json()
                    choice = data["choices"][0]
                    message = choice.get("message", {}) or {}
                    tool_calls = message.get("tool_calls")
                    if tool_calls:
                        yield LlmResponse(
                            content=Content(role="model", parts=_tool_calls_to_parts(tool_calls)),
                            partial=False,
                            turn_complete=True
                        )
                        return
                    response_text = message.get("content") or ""
                    yield LlmResponse(
                        content=Content(role="model", parts=[Part.from_text(text=response_text)]),
                        partial=False,
                        turn_complete=True
                    )
                except Exception as e:
                    msg = str(e) or repr(e) or "Unknown LLM call error"
                    logger.exception(f"Exception during LLM call: {msg}")
                    yield LlmResponse(error_code="LLM_ERROR", error_message=msg, partial=False)
