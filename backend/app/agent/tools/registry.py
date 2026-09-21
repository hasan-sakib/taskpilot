from app.agent.tools.base import Tool


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def all(self) -> list[Tool]:
        return list(self._tools.values())


def build_default_registry() -> ToolRegistry:
    from app.agent.tools.browser.click import ClickTool
    from app.agent.tools.browser.close_session import CloseSessionTool
    from app.agent.tools.browser.fill import FillTool
    from app.agent.tools.browser.get_page_content import GetPageContentTool
    from app.agent.tools.browser.navigate import NavigateTool
    from app.agent.tools.browser.screenshot import ScreenshotTool
    from app.agent.tools.browser.select_option import SelectOptionTool
    from app.agent.tools.browser.start_session import StartSessionTool
    from app.agent.tools.python_execution.execute_python import ExecutePythonTool
    from app.agent.tools.task_management.add_dependency import AddDependencyTool
    from app.agent.tools.task_management.cancel_task import CancelTaskTool
    from app.agent.tools.task_management.create_task import CreateTaskTool
    from app.agent.tools.task_management.get_task import GetTaskTool
    from app.agent.tools.task_management.list_tasks import ListTasksTool
    from app.agent.tools.task_management.record_result import RecordResultTool
    from app.agent.tools.task_management.retry_task import RetryTaskTool
    from app.agent.tools.task_management.set_priority_deadline import SetPriorityDeadlineTool
    from app.agent.tools.task_management.update_status import UpdateStatusTool
    from app.agent.tools.web_research.open_url import OpenUrlTool
    from app.agent.tools.web_research.search import WebSearchTool
    from app.agent.tools.web_research.store_research_note import StoreResearchNoteTool
    from app.agent.tools.web_research.summarize import SummarizeTool
    from app.agent.tools.workspace.create_dir import CreateDirTool
    from app.agent.tools.workspace.delete_file import DeleteFileTool
    from app.agent.tools.workspace.generate_report import GenerateReportTool
    from app.agent.tools.workspace.list_dir import ListDirTool
    from app.agent.tools.workspace.move_file import MoveFileTool
    from app.agent.tools.workspace.read_file import ReadFileTool
    from app.agent.tools.workspace.search import SearchTool
    from app.agent.tools.workspace.write_file import WriteFileTool

    registry = ToolRegistry()
    registry.register(ListDirTool())
    registry.register(ReadFileTool())
    registry.register(WriteFileTool())
    registry.register(CreateDirTool())
    registry.register(MoveFileTool())
    registry.register(DeleteFileTool())
    registry.register(SearchTool())
    registry.register(GenerateReportTool())
    registry.register(CreateTaskTool())
    registry.register(ListTasksTool())
    registry.register(GetTaskTool())
    registry.register(UpdateStatusTool())
    registry.register(SetPriorityDeadlineTool())
    registry.register(AddDependencyTool())
    registry.register(RecordResultTool())
    registry.register(RetryTaskTool())
    registry.register(CancelTaskTool())
    registry.register(WebSearchTool())
    registry.register(OpenUrlTool())
    registry.register(SummarizeTool())
    registry.register(StoreResearchNoteTool())
    registry.register(ExecutePythonTool())
    registry.register(StartSessionTool())
    registry.register(NavigateTool())
    registry.register(GetPageContentTool())
    registry.register(ScreenshotTool())
    registry.register(ClickTool())
    registry.register(FillTool())
    registry.register(SelectOptionTool())
    registry.register(CloseSessionTool())
    return registry
