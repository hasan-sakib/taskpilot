from app.agent.llm.base import LLMProvider, PlanRequest, PlanResponse, ReportRequest


class ScriptedTestProvider(LLMProvider):
    """Deterministic LLM stand-in for tests and demos -- no network, no model required.

    Construct with a fixed sequence of plans; each call to generate_plan() returns the
    next scripted plan (e.g. the initial plan, then a replanned one). Once the script is
    exhausted, the last plan repeats -- so a test doesn't have to over-provision replanning
    loops it isn't asserting on.
    """

    def __init__(
        self,
        plans: list[PlanResponse] | None = None,
        report: str = "Test run completed.",
        completion: str = "Test completion.",
    ) -> None:
        self._plans = list(plans) if plans else [PlanResponse(tasks=[])]
        self._plan_index = 0
        self._report = report
        self._completion = completion
        self.plan_requests: list[PlanRequest] = []
        self.report_requests: list[ReportRequest] = []
        self.completion_prompts: list[str] = []

    async def generate_plan(self, request: PlanRequest) -> PlanResponse:
        self.plan_requests.append(request)
        plan = self._plans[min(self._plan_index, len(self._plans) - 1)]
        self._plan_index += 1
        return plan

    async def generate_report(self, request: ReportRequest) -> str:
        self.report_requests.append(request)
        return self._report

    async def complete_text(self, prompt: str) -> str:
        self.completion_prompts.append(prompt)
        return self._completion
