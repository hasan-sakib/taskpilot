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
    from app.agent.tools.workspace.list_dir import ListDirTool
    from app.agent.tools.workspace.write_file import WriteFileTool

    registry = ToolRegistry()
    registry.register(ListDirTool())
    registry.register(WriteFileTool())
    return registry
