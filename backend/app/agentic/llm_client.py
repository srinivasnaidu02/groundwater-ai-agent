"""Multi-provider LLM Client supporting native function calling and offline mocks."""
from __future__ import annotations

import asyncio
import json
import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from backend.app.agentic.config import agentic_settings

logger = logging.getLogger(__name__)


@dataclass
class ToolCall:
    """Standardized tool invocation payload."""
    id: str
    name: str
    arguments: Dict[str, Any] = field(default_factory=dict)

    @property
    def args(self) -> Dict[str, Any]:
        return self.arguments


@dataclass
class LLMResponse:
    """Standardized response from any LLM provider."""
    content: Optional[str] = None
    tool_calls: Optional[List[ToolCall]] = None


class LLMClient(ABC):
    """Abstract base class for all LLM providers supporting function-calling."""

    @abstractmethod
    async def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> LLMResponse:
        """Execute chat completion with optional native function calling."""
        pass


class MockLLMClient(LLMClient):
    """Deterministic, offline LLM client for automated testing and fallback simulation."""

    def __init__(self, predefined_responses: Optional[List[LLMResponse]] = None):
        self.predefined_responses: List[LLMResponse] = predefined_responses or []
        self.call_history: List[Dict[str, Any]] = []

    def set_responses(self, responses: List[LLMResponse]):
        self.predefined_responses = list(responses)

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> LLMResponse:
        self.call_history.append({"messages": messages, "tools": tools})

        if self.predefined_responses:
            return self.predefined_responses.pop(0)

        # Default intelligent script based on message content
        user_msg = ""
        for m in reversed(messages):
            if m.get("role") in ["user", "human"]:
                user_msg = str(m.get("content", ""))
                break

        # Check if query asks about Punjab over-exploitation
        if tools and "punjab" in user_msg.lower() and ("over-exploited" in user_msg.lower() or "why" in user_msg.lower()):
            return LLMResponse(
                content="Analyzing Punjab groundwater extraction stage, overexploited units, and temporal trend.",
                tool_calls=[
                    ToolCall(id="call_1", name="get_stage_of_extraction", arguments={"state": "Punjab", "assessment_year": "2025"}),
                    ToolCall(id="call_2", name="get_overexploited_units", arguments={"state": "Punjab", "assessment_year": "2025"}),
                    ToolCall(id="call_3", name="compare_assessment_years", arguments={"state": "Punjab", "parameter": "extraction", "year1": "2020", "year2": "2026"}),
                ]
            )

        # Dynamic multi-location or multi-year comparison check
        if tools and ("compare" in user_msg.lower() or "versus" in user_msg.lower() or "between" in user_msg.lower() or " vs " in user_msg.lower()):
            try:
                from backend.app.agentic.query_parser import parse_query
                p = parse_query(user_msg)
                if p.intent == "compare_years" and len(p.years) >= 2:
                    loc = p.locations[0] if p.locations else None
                    st = loc.state if loc else "Maharashtra"
                    dist = loc.district if loc else None
                    param = "stage" if "stage" in user_msg.lower() else ("recharge" if "recharge" in user_msg.lower() else "extraction")
                    return LLMResponse(
                        content=f"Comparing assessment years {p.years[0]} and {p.years[1]} for {st}.",
                        tool_calls=[
                            ToolCall(
                                id="call_1",
                                name="compare_assessment_years",
                                arguments={"state": st, "district": dist, "parameter": param, "year1": p.years[0], "year2": p.years[1]},
                            )
                        ],
                    )
                if len(p.locations) >= 2:
                    tool_calls = []
                    idx = 1
                    y = p.years[0] if p.years else "2025"
                    for loc in p.locations:
                        for m in p.metrics:
                            t_name = "get_groundwater_extraction" if m == "extraction" else (
                                "get_groundwater_recharge" if m == "recharge" else (
                                    "get_stage_of_extraction" if m == "stage_of_extraction" else (
                                        "get_extractable_groundwater" if m == "extractable_resource" else "get_stage_of_extraction"
                                    )
                                )
                            )
                            t_args = {"state": loc.state, "assessment_year": y}
                            if loc.district:
                                t_args["district"] = loc.district
                            tool_calls.append(ToolCall(id=f"call_{idx}", name=t_name, arguments=t_args))
                            idx += 1
                    return LLMResponse(
                        content=f"Comparing groundwater parameters across {', '.join(l.canonical_str() for l in p.locations)}.",
                        tool_calls=tool_calls,
                    )
            except Exception:
                pass

        # Synthesis JSON generation
        if "Evidence Ledger:" in user_msg or "evidence" in user_msg.lower():
            import re
            try:
                ledger_match = re.search(r"Evidence Ledger:\s*(\[.*?\])", user_msg, re.DOTALL)
                if ledger_match:
                    evidence_items = json.loads(ledger_match.group(1))
                    from backend.app.agentic.synthesizer import build_template_answer
                    ans_dict = build_template_answer(user_msg[:100], evidence_items)
                    return LLMResponse(content=json.dumps(ans_dict), tool_calls=None)
            except Exception:
                pass
        primary_val = 101.75
        secondary_val = 13.24
        # Parse from evidence if available in user message
        if "Evidence Ledger:" in user_msg or "evidence" in user_msg.lower():
            import re
            nums = re.findall(r"\b\d+(?:\.\d+)?\b", user_msg)
            float_nums = [float(n) for n in nums if float(n) not in [2020.0, 2022.0, 2025.0, 2026.0]]
            if float_nums:
                primary_val = float_nums[0]
                if len(float_nums) > 1:
                    secondary_val = float_nums[1]

        default_json = json.dumps({
            "summary": f"In Punjab, groundwater extraction stage reached {primary_val:.2f}% with 5 overexploited districts.",
            "numeric_breakdown": [
                {
                    "parameter": "Stage of Extraction",
                    "label": "Stage of Extraction",
                    "value": primary_val,
                    "unit": "%",
                    "year": "2025",
                    "location": "Punjab"
                },
                {
                    "parameter": "Extraction Change",
                    "label": "Extraction Change",
                    "value": secondary_val,
                    "unit": "%",
                    "year": "2020-2026",
                    "location": "Punjab"
                }
            ],
            "trend_analysis": f"Extraction showed an upward trajectory of {secondary_val:.2f}% between 2020 and 2026.",
            "interpretation": "[General Hydrogeological Context - Not from CGWB Data] High extraction is driven by intense agricultural irrigation and tubewell pumping.",
            "policy_recommendations": [
                "[AI Suggestion - Not CGWB Guidance] Expand micro-irrigation systems across over-exploited blocks.",
                "[AI Suggestion - Not CGWB Guidance] Promote crop diversification to lower water consumption."
            ],
            "limitations": [
                "2026 data represents a benchmark projection model."
            ]
        })

        return LLMResponse(content=default_json, tool_calls=None)


class GeminiClient(LLMClient):
    """Google Gemini native function calling client."""

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        self.api_key = api_key or agentic_settings.GEMINI_API_KEY
        self.model_name = model_name or agentic_settings.LLM_MODEL or "gemini-2.5-flash"
        self._genai = None

    def _get_sdk(self):
        if self._genai is None:
            try:
                import google.generativeai as genai
                if self.api_key:
                    genai.configure(api_key=self.api_key)
                self._genai = genai
            except ImportError:
                raise RuntimeError("google-generativeai is not installed. Run `pip install google-generativeai`.")
        return self._genai

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> LLMResponse:
        genai = self._get_sdk()

        for attempt in range(3):
            try:
                def _sync_call():
                    model = genai.GenerativeModel(self.model_name)
                    # Convert OpenAI tool schema to Gemini format if provided
                    gemini_tools = None
                    if tools:
                        gemini_tools = [
                            genai.types.FunctionDeclaration(
                                name=t["function"]["name"],
                                description=t["function"]["description"],
                                parameters=t["function"]["parameters"],
                            )
                            for t in tools if "function" in t
                        ]
                    # Format prompt
                    prompt = "\n".join([f"{m.get('role', 'user').upper()}: {m.get('content', '')}" for m in messages])
                    return model.generate_content(prompt, tools=gemini_tools)

                resp = await asyncio.wait_for(asyncio.to_thread(_sync_call), timeout=15.0)

                # Parse Gemini response
                tool_calls = []
                content = None
                if resp and resp.candidates:
                    candidate = resp.candidates[0]
                    for part in candidate.content.parts:
                        if hasattr(part, "function_call") and part.function_call:
                            fn = part.function_call
                            tool_calls.append(ToolCall(
                                id=f"call_{fn.name}",
                                name=fn.name,
                                arguments=dict(fn.args),
                            ))
                        elif hasattr(part, "text") and part.text:
                            content = (content or "") + part.text

                return LLMResponse(content=content, tool_calls=tool_calls if tool_calls else None)
            except Exception as e:
                logger.warning(f"GeminiClient chat attempt {attempt + 1} failed: {e}")
                if attempt < 2:
                    await asyncio.sleep(1.0 * (2 ** attempt))
                else:
                    raise e
        return LLMResponse(content=None, tool_calls=None)


class OpenAIClient(LLMClient):
    """OpenAI native function calling client."""

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        self.api_key = api_key or agentic_settings.OPENAI_API_KEY
        self.model_name = model_name or "gpt-4o-mini"
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from openai import AsyncOpenAI
                self._client = AsyncOpenAI(api_key=self.api_key)
            except ImportError:
                raise RuntimeError("openai is not installed. Run `pip install openai`.")
        return self._client

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> LLMResponse:
        client = self._get_client()
        clean_msgs = [{"role": m["role"], "content": str(m.get("content", ""))} for m in messages]

        kwargs: Dict[str, Any] = {"model": self.model_name, "messages": clean_msgs}
        if tools:
            kwargs["tools"] = tools

        for attempt in range(3):
            try:
                resp = await asyncio.wait_for(client.chat.completions.create(**kwargs), timeout=15.0)
                msg = resp.choices[0].message
                tool_calls = None
                if msg.tool_calls:
                    tool_calls = [
                        ToolCall(
                            id=tc.id,
                            name=tc.function.name,
                            arguments=json.loads(tc.function.arguments or "{}"),
                        )
                        for tc in msg.tool_calls
                    ]
                return LLMResponse(content=msg.content, tool_calls=tool_calls)
            except Exception as e:
                logger.warning(f"OpenAIClient chat attempt {attempt + 1} failed: {e}")
                if attempt < 2:
                    await asyncio.sleep(1.0 * (2 ** attempt))
                else:
                    raise e
        return LLMResponse(content=None, tool_calls=None)


class AnthropicClient(LLMClient):
    """Anthropic Claude tool use client."""

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        self.api_key = api_key or agentic_settings.ANTHROPIC_API_KEY
        self.model_name = model_name or "claude-3-5-haiku-20241022"
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from anthropic import AsyncAnthropic
                self._client = AsyncAnthropic(api_key=self.api_key)
            except ImportError:
                raise RuntimeError("anthropic is not installed. Run `pip install anthropic`.")
        return self._client

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> LLMResponse:
        client = self._get_client()

        # Format system and messages
        system_prompt = ""
        user_msgs = []
        for m in messages:
            if m.get("role") == "system":
                system_prompt += m.get("content", "") + "\n"
            else:
                user_msgs.append({"role": m["role"], "content": m.get("content", "")})

        anthropic_tools = None
        if tools:
            anthropic_tools = [
                {
                    "name": t["function"]["name"],
                    "description": t["function"]["description"],
                    "input_schema": t["function"]["parameters"],
                }
                for t in tools if "function" in t
            ]

        kwargs: Dict[str, Any] = {
            "model": self.model_name,
            "max_tokens": 1024,
            "messages": user_msgs,
        }
        if system_prompt:
            kwargs["system"] = system_prompt
        if anthropic_tools:
            kwargs["tools"] = anthropic_tools

        for attempt in range(3):
            try:
                resp = await asyncio.wait_for(client.messages.create(**kwargs), timeout=15.0)
                content = None
                tool_calls = []
                for block in resp.content:
                    if block.type == "text":
                        content = (content or "") + block.text
                    elif block.type == "tool_use":
                        tool_calls.append(ToolCall(
                            id=block.id,
                            name=block.name,
                            arguments=block.input,
                        ))
                return LLMResponse(content=content, tool_calls=tool_calls if tool_calls else None)
            except Exception as e:
                logger.warning(f"AnthropicClient chat attempt {attempt + 1} failed: {e}")
                if attempt < 2:
                    await asyncio.sleep(1.0 * (2 ** attempt))
                else:
                    raise e
        return LLMResponse(content=None, tool_calls=None)


def get_llm_client() -> LLMClient:
    """Factory creating the appropriate LLM client based on configuration."""
    provider = (agentic_settings.LLM_PROVIDER or "mock").lower()
    if provider == "gemini":
        return GeminiClient()
    elif provider == "openai":
        return OpenAIClient()
    elif provider == "anthropic":
        return AnthropicClient()
    return MockLLMClient()
