"""Abstract LLM Client interface and provider implementations (Gemini, OpenAI, Anthropic, Mock).
Lazy-imports all SDKs so missing packages or keys never prevent application startup.
"""
import os
import time
import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from .config import agentic_settings

logger = logging.getLogger(__name__)


@dataclass
class ToolCall:
    """Standardized tool invocation payload across providers."""
    id: str
    name: str
    args: Dict[str, Any] = field(default_factory=dict)

    @property
    def arguments(self) -> Dict[str, Any]:
        """Alias for args for OpenAI schema compatibility."""
        return self.args


ToolCallRequest = ToolCall


class LLMMessage(dict):
    """Convenience dict subclass for LLM chat messages."""
    def __init__(self, role: str, content: str, name: Optional[str] = None, tool_call_id: Optional[str] = None, **kwargs):
        super().__init__(role=role, content=content, **kwargs)
        if name:
            self["name"] = name
        if tool_call_id:
            self["tool_call_id"] = tool_call_id



@dataclass
class LLMResponse:
    """Standardized response from any LLM provider."""
    content: Optional[str] = None
    tool_calls: List[ToolCall] = field(default_factory=list)
    model: str = "unknown"
    usage: Dict[str, int] = field(default_factory=dict)
    raw_response: Any = None


class LLMClient(ABC):
    """Abstract base class for all LLM providers supporting function-calling."""

    @abstractmethod
    def generate(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.2,
        response_json_schema: Optional[Dict[str, Any]] = None,
    ) -> LLMResponse:
        """Generate a response, optionally executing native function calling."""
        pass


class MockLLMClient(LLMClient):
    """Deterministic, offline LLM client for automated testing and fallback simulation."""

    def __init__(self, predefined_responses: Optional[List[LLMResponse]] = None):
        self.predefined_responses: List[LLMResponse] = predefined_responses or []
        self.call_history: List[Dict[str, Any]] = []

    def set_responses(self, responses: List[LLMResponse]):
        self.predefined_responses = list(responses)

    def generate(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.2,
        response_json_schema: Optional[Dict[str, Any]] = None,
    ) -> LLMResponse:
        self.call_history.append({
            "messages": messages,
            "tools": tools,
            "temperature": temperature,
            "schema": response_json_schema,
        })
        if self.predefined_responses:
            return self.predefined_responses.pop(0)

        # Inspect the last user message for automated intelligent mock responses
        user_msg = ""
        for m in reversed(messages):
            if m.get("role") in ["user", "human"]:
                user_msg = str(m.get("content", ""))
                break

        # If tools provided and question asks for Punjab multi-step:
        if tools and "punjab" in user_msg.lower() and ("over-exploited" in user_msg.lower() or "why" in user_msg.lower()):
            # Simulate multi-step tool calls
            return LLMResponse(
                content="I will check Punjab's stage of extraction, over-exploited units, and compare 2020 to 2026.",
                tool_calls=[
                    ToolCall(id="call_1", name="get_stage_of_extraction", args={"state": "Punjab", "assessment_year": "2025"}),
                    ToolCall(id="call_2", name="get_overexploited_units", args={"state": "Punjab", "assessment_year": "2025"}),
                    ToolCall(id="call_3", name="compare_assessment_years", args={"state": "Punjab", "parameter": "extraction", "year1": "2020", "year2": "2026"}),
                ],
                model="mock-agent-model",
            )

        # If asked for synthesis JSON output, ground figures dynamically in the provided evidence ledger
        evidence_numbers = []
        if "Verified Evidence Ledger:" in user_msg:
            from backend.app.agentic.verifier import extract_numbers_from_text
            ledger_text = user_msg.split("Verified Evidence Ledger:")[1].split("Expected JSON")[0] if "Expected JSON" in user_msg else user_msg
            evidence_numbers = extract_numbers_from_text(ledger_text)

        # Pick verified numbers from evidence ledger if available
        primary_val = evidence_numbers[0] if evidence_numbers else 101.75
        secondary_val = evidence_numbers[1] if len(evidence_numbers) > 1 else primary_val

        default_json = json.dumps({
            "summary": f"Groundwater assessment data shows recorded value of {primary_val:,.2f} for the evaluated location.",
            "numeric_breakdown": [
                {
                    "parameter": "Verified Groundwater Assessment Metric",
                    "location": "Assessed Unit",
                    "year": "2025",
                    "value": primary_val,
                    "unit": "Ham",
                    "verification_status": "VERIFIED"
                }
            ],
            "trend_analysis": f"Trajectory indicates comparative assessment metric of {secondary_val:,.2f} across evaluated cycles.",
            "interpretation": "[General Hydrogeological Context - Not from CGWB Database] Groundwater extraction levels reflect localized agricultural pumping and aquifer recharge patterns.",
            "policy_recommendations": [
                "[AI Suggestion - Not CGWB Guidance] Expand precision micro-irrigation systems.",
                "[AI Suggestion - Not CGWB Guidance] Construct artificial recharge structures in over-exploited sub-basins."
            ],
            "limitations": "Assessment cycle 2026 represents a benchmark projection in the dataset."
        })

        return LLMResponse(
            content=default_json,
            tool_calls=[],
            model="mock-agent-model",
        )


class GeminiClient(LLMClient):
    """Google Gemini native function calling client."""

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        self.api_key = api_key or agentic_settings.GEMINI_API_KEY
        self.model_name = model_name or agentic_settings.get_effective_model()
        self._genai = None

    def _get_sdk(self):
        if self._genai is None:
            try:
                import google.generativeai as genai
                if not self.api_key:
                    raise ValueError("GEMINI_API_KEY is not configured.")
                genai.configure(api_key=self.api_key)
                self._genai = genai
            except ImportError:
                raise ImportError("google-generativeai package is not installed. Install via pip install google-generativeai")
        return self._genai

    def generate(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.2,
        response_json_schema: Optional[Dict[str, Any]] = None,
    ) -> LLMResponse:
        genai = self._get_sdk()

        # Format system prompt and chat history
        system_instruction = None
        contents = []
        for m in messages:
            role = m.get("role")
            text = str(m.get("content", ""))
            if role == "system":
                system_instruction = text
            elif role in ["user", "human"]:
                contents.append({"role": "user", "parts": [text]})
            elif role in ["assistant", "model"]:
                contents.append({"role": "model", "parts": [text]})

        # Convert tool schemas to Gemini declarations if provided
        gemini_tools = None
        if tools:
            # We can pass JSON schema tool definitions
            gemini_tools = []
            for t in tools:
                gemini_tools.append({
                    "function_declarations": [{
                        "name": t["name"],
                        "description": t["description"],
                        "parameters": t.get("parameters", {"type": "object", "properties": {}}),
                    }]
                })

        model = genai.GenerativeModel(
            model_name=self.model_name,
            system_instruction=system_instruction,
            tools=gemini_tools,
        )

        # Retry with exponential backoff
        last_err = None
        for attempt in range(3):
            try:
                gen_config = {"temperature": temperature}
                if response_json_schema:
                    gen_config["response_mime_type"] = "application/json"

                response = model.generate_content(
                    contents=contents,
                    generation_config=gen_config,
                )

                tool_calls: List[ToolCall] = []
                content_text = ""

                # Parse candidates and function calls
                if response.candidates:
                    candidate = response.candidates[0]
                    for part in candidate.content.parts:
                        if hasattr(part, "function_call") and part.function_call:
                            fc = part.function_call
                            call_args = {}
                            if hasattr(fc, "args"):
                                for k, v in fc.args.items():
                                    call_args[k] = v
                            tool_calls.append(ToolCall(
                                id=f"call_{int(time.time() * 1000)}_{len(tool_calls)}",
                                name=fc.name,
                                args=call_args,
                            ))
                        elif hasattr(part, "text") and part.text:
                            content_text += part.text

                return LLMResponse(
                    content=content_text or None,
                    tool_calls=tool_calls,
                    model=self.model_name,
                    raw_response=response,
                )
            except Exception as e:
                last_err = e
                logger.warning(f"Gemini API attempt {attempt + 1} failed: {e}")
                time.sleep(0.5 * (2 ** attempt))

        raise RuntimeError(f"Gemini API failed after 3 attempts: {last_err}")


class OpenAIClient(LLMClient):
    """OpenAI API client supporting native function/tool calling."""

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        self.api_key = api_key or agentic_settings.OPENAI_API_KEY
        self.model_name = model_name or agentic_settings.get_effective_model()
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from openai import OpenAI
                if not self.api_key:
                    raise ValueError("OPENAI_API_KEY is not configured.")
                self._client = OpenAI(api_key=self.api_key)
            except ImportError:
                raise ImportError("openai package is not installed. Install via pip install openai")
        return self._client

    def generate(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.2,
        response_json_schema: Optional[Dict[str, Any]] = None,
    ) -> LLMResponse:
        client = self._get_client()

        openai_tools = None
        if tools:
            openai_tools = [
                {
                    "type": "function",
                    "function": {
                        "name": t["name"],
                        "description": t["description"],
                        "parameters": t.get("parameters", {"type": "object", "properties": {}}),
                    }
                }
                for t in tools
            ]

        kwargs: Dict[str, Any] = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
        }
        if openai_tools:
            kwargs["tools"] = openai_tools
        if response_json_schema:
            kwargs["response_format"] = {"type": "json_object"}

        last_err = None
        for attempt in range(3):
            try:
                res = client.chat.completions.create(**kwargs)
                choice = res.choices[0].message
                tool_calls: List[ToolCall] = []
                if choice.tool_calls:
                    for tc in choice.tool_calls:
                        parsed_args = {}
                        try:
                            parsed_args = json.loads(tc.function.arguments)
                        except Exception:
                            pass
                        tool_calls.append(ToolCall(
                            id=tc.id,
                            name=tc.function.name,
                            args=parsed_args,
                        ))

                return LLMResponse(
                    content=choice.content,
                    tool_calls=tool_calls,
                    model=self.model_name,
                    raw_response=res,
                )
            except Exception as e:
                last_err = e
                logger.warning(f"OpenAI API attempt {attempt + 1} failed: {e}")
                time.sleep(0.5 * (2 ** attempt))

        raise RuntimeError(f"OpenAI API failed after 3 attempts: {last_err}")


class AnthropicClient(LLMClient):
    """Anthropic Claude API client."""

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        self.api_key = api_key or agentic_settings.ANTHROPIC_API_KEY
        self.model_name = model_name or agentic_settings.get_effective_model()
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                import anthropic
                if not self.api_key:
                    raise ValueError("ANTHROPIC_API_KEY is not configured.")
                self._client = anthropic.Anthropic(api_key=self.api_key)
            except ImportError:
                raise ImportError("anthropic package is not installed.")
        return self._client

    def generate(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.2,
        response_json_schema: Optional[Dict[str, Any]] = None,
    ) -> LLMResponse:
        client = self._get_client()
        system_prompt = ""
        user_msgs = []
        for m in messages:
            if m.get("role") == "system":
                system_prompt += m.get("content", "") + "\n"
            else:
                user_msgs.append({"role": m.get("role"), "content": m.get("content")})

        claude_tools = None
        if tools:
            claude_tools = [
                {
                    "name": t["name"],
                    "description": t["description"],
                    "input_schema": t.get("parameters", {"type": "object", "properties": {}}),
                }
                for t in tools
            ]

        kwargs: Dict[str, Any] = {
            "model": self.model_name,
            "max_tokens": 2048,
            "messages": user_msgs,
            "temperature": temperature,
        }
        if system_prompt:
            kwargs["system"] = system_prompt
        if claude_tools:
            kwargs["tools"] = claude_tools

        res = client.messages.create(**kwargs)
        tool_calls: List[ToolCall] = []
        content_text = ""
        for block in res.content:
            if block.type == "text":
                content_text += block.text
            elif block.type == "tool_use":
                tool_calls.append(ToolCall(
                    id=block.id,
                    name=block.name,
                    args=block.input,
                ))

        return LLMResponse(
            content=content_text or None,
            tool_calls=tool_calls,
            model=self.model_name,
            raw_response=res,
        )


def get_llm_client(provider: Optional[str] = None) -> LLMClient:
    """Factory creating the appropriate LLM client based on configuration."""
    selected = (provider or agentic_settings.LLM_PROVIDER or "gemini").lower()

    if selected == "mock":
        return MockLLMClient()
    elif selected == "openai":
        return OpenAIClient()
    elif selected == "anthropic":
        return AnthropicClient()
    elif selected == "gemini":
        return GeminiClient()
    else:
        logger.warning(f"Unknown provider '{selected}', falling back to MockLLMClient")
        return MockLLMClient()
