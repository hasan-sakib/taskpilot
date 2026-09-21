import asyncio
import json

import ollama
from pydantic import ValidationError

from app.agent.llm.base import (
    LLMProvider,
    LLMProviderError,
    PlanRequest,
    PlanResponse,
    ReportRequest,
)
from app.agent.llm.prompt_safety import wrap_untrusted_content
from app.core.config import get_settings

PLAN_SYSTEM_PROMPT = (
    "You are TaskPilot's planning engine. Given a user goal and a list of available tools, "
    'produce a JSON object with a single key "tasks": an array of task objects. Each task '
    'object has: "description" (string), "tool_name" (must be exactly one of the listed '
    'tool names), "tool_args" (object matching that tool\'s input schema), and "depends_on" '
    "(array of 0-based indices into this same tasks array, for tasks that must complete "
    "first). Use only the listed tool names -- never invent one. "
    "Every value in tool_args MUST be a concrete, literal value you can supply right now "
    "(a real URL, a real file path, real text) -- there is no way for a task to reference "
    "another task's output or result at plan time, so never write a placeholder like "
    "'result_from_task0' or '<url from search>' as an argument value; tools do not "
    "understand these and the task will simply fail. Your plan must fully accomplish the "
    "goal using only tools whose arguments you can already specify -- do not plan a task "
    "whose arguments depend on information only a prior task's result will reveal (e.g. "
    "opening one specific URL a search will find), even if that means leaving the goal "
    "incomplete; a plan that stops short of the goal will be reported as a success as "
    "long as every planned task succeeds, so this is not a safe way to hand off later "
    "work. Prefer tools whose own output is self-contained for the goal at hand -- for "
    "example, web_research.search already returns a title, url, and snippet for each "
    "result, which is usually enough to write a useful summary or note directly, without "
    "ever needing to open a specific result's URL. "
    "Respond with JSON only, no commentary, no markdown fences."
)


class OllamaProvider(LLMProvider):
    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout_seconds: int | None = None,
    ) -> None:
        settings = get_settings()
        self._client = ollama.AsyncClient(host=base_url or settings.ollama_base_url)
        self._model = model or settings.ollama_model
        self._timeout = timeout_seconds or settings.llm_request_timeout_seconds

    async def generate_plan(self, request: PlanRequest) -> PlanResponse:
        tool_lines = "\n".join(
            f"- {t.name}: {t.description} (input schema: {json.dumps(t.input_schema)})"
            for t in request.available_tools
        )
        user_prompt = f"Goal: {request.goal}\n\nAvailable tools:\n{tool_lines}"
        if request.prior_errors:
            joined = "\n".join(f"- {e}" for e in request.prior_errors)
            # Mostly system-generated (validation/provider errors), but a tool's error
            # message could in principle echo back external content -- wrap on general
            # principle, same as prior_results_summary below.
            user_prompt += "\n\n" + wrap_untrusted_content(
                "reasons the previous plan was rejected", joined
            )
        if request.prior_results_summary:
            user_prompt += "\n\n" + wrap_untrusted_content(
                "progress so far", request.prior_results_summary
            )

        try:
            response = await asyncio.wait_for(
                self._client.chat(
                    model=self._model,
                    messages=[
                        {"role": "system", "content": PLAN_SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    format="json",
                    options={"temperature": 0},
                ),
                timeout=self._timeout,
            )
            content = response["message"]["content"]
            return PlanResponse.model_validate(json.loads(content))
        except TimeoutError as exc:
            raise LLMProviderError(f"Ollama request timed out after {self._timeout}s") from exc
        except (json.JSONDecodeError, ValidationError) as exc:
            raise LLMProviderError(f"Ollama returned an unparsable plan: {exc}") from exc
        except LLMProviderError:
            raise
        except Exception as exc:  # ollama client raises its own error types on connection issues
            raise LLMProviderError(f"Ollama request failed: {exc}") from exc

    async def generate_report(self, request: ReportRequest) -> str:
        summary_lines = "\n".join(f"- {s}" for s in request.task_summaries)
        status = "succeeded" if request.overall_success else "did not fully succeed"
        prompt = (
            f"Goal: {request.goal}\n\n"
            + wrap_untrusted_content("task outcomes", summary_lines)
            + f"\n\nOverall status: {status}\n\n"
            "Write a concise final report (plain text, a few short paragraphs) summarizing "
            "what was accomplished, referencing the task outcomes above."
        )
        return await self._chat(prompt, temperature=0.2)

    async def complete_text(self, prompt: str) -> str:
        return await self._chat(prompt, temperature=0.2)

    async def _chat(self, prompt: str, *, temperature: float) -> str:
        try:
            response = await asyncio.wait_for(
                self._client.chat(
                    model=self._model,
                    messages=[{"role": "user", "content": prompt}],
                    options={"temperature": temperature},
                ),
                timeout=self._timeout,
            )
            return response["message"]["content"]
        except TimeoutError as exc:
            raise LLMProviderError(f"Ollama request timed out after {self._timeout}s") from exc
        except Exception as exc:
            raise LLMProviderError(f"Ollama request failed: {exc}") from exc
