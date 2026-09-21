import pytest

from app.agent.policies.workspace_policy import WorkspacePathError
from app.agent.tools.base import PermissionLevel, ToolError
from app.agent.tools.workspace.create_dir import CreateDirInput, CreateDirTool
from app.agent.tools.workspace.delete_file import DeleteFileInput, DeleteFileTool
from app.agent.tools.workspace.generate_report import GenerateReportInput, GenerateReportTool
from app.agent.tools.workspace.list_dir import ListDirInput, ListDirTool
from app.agent.tools.workspace.move_file import MoveFileInput, MoveFileTool
from app.agent.tools.workspace.read_file import ReadFileInput, ReadFileTool
from app.agent.tools.workspace.search import SearchInput, SearchTool
from app.agent.tools.workspace.write_file import WriteFileInput, WriteFileTool

# --- list_dir ---


@pytest.mark.asyncio
async def test_list_dir_lists_files_and_dirs(workspace_root, run_ctx):
    (workspace_root / "a.txt").write_text("hi")
    (workspace_root / "sub").mkdir()
    out = await ListDirTool().run(ListDirInput(path="."), run_ctx)
    names = {e.name: e.is_dir for e in out.entries}
    assert names == {"a.txt": False, "sub": True}


@pytest.mark.asyncio
async def test_list_dir_rejects_missing_dir(workspace_root, run_ctx):
    with pytest.raises(ToolError):
        await ListDirTool().run(ListDirInput(path="nope"), run_ctx)


def test_list_dir_is_auto_approved():
    decision = ListDirTool().evaluate_permission({}, {})
    assert decision.requires_approval is False


# --- read_file ---


@pytest.mark.asyncio
async def test_read_file_returns_content(workspace_root, run_ctx):
    (workspace_root / "note.txt").write_text("hello world")
    out = await ReadFileTool().run(ReadFileInput(path="note.txt"), run_ctx)
    assert out.content == "hello world"
    assert out.truncated is False
    assert out.size_bytes == len(b"hello world")


@pytest.mark.asyncio
async def test_read_file_rejects_missing_file(workspace_root, run_ctx):
    with pytest.raises(ToolError):
        await ReadFileTool().run(ReadFileInput(path="missing.txt"), run_ctx)


@pytest.mark.asyncio
async def test_read_file_rejects_directory(workspace_root, run_ctx):
    (workspace_root / "sub").mkdir()
    with pytest.raises(ToolError):
        await ReadFileTool().run(ReadFileInput(path="sub"), run_ctx)


# --- write_file ---


@pytest.mark.asyncio
async def test_write_file_creates_file_atomically(workspace_root, run_ctx):
    out = await WriteFileTool().run(WriteFileInput(path="a.txt", content="hi"), run_ctx)
    assert out.bytes_written == 2
    assert (workspace_root / "a.txt").read_text() == "hi"
    assert not (workspace_root / "a.txt.tmp").exists()


@pytest.mark.asyncio
async def test_write_file_refuses_overwrite_without_flag(workspace_root, run_ctx):
    (workspace_root / "a.txt").write_text("original")
    with pytest.raises(ToolError):
        await WriteFileTool().run(WriteFileInput(path="a.txt", content="new"), run_ctx)
    assert (workspace_root / "a.txt").read_text() == "original"


@pytest.mark.asyncio
async def test_write_file_overwrites_with_flag(workspace_root, run_ctx):
    (workspace_root / "a.txt").write_text("original")
    await WriteFileTool().run(
        WriteFileInput(path="a.txt", content="new", overwrite=True), run_ctx
    )
    assert (workspace_root / "a.txt").read_text() == "new"


def test_write_file_requires_approval_by_default():
    decision = WriteFileTool().evaluate_permission({}, {})
    assert decision.requires_approval is True
    assert WriteFileTool.default_permission == PermissionLevel.REQUIRES_APPROVAL


# --- create_dir ---


@pytest.mark.asyncio
async def test_create_dir_creates_nested_dirs(workspace_root, run_ctx):
    out = await CreateDirTool().run(CreateDirInput(path="a/b/c"), run_ctx)
    assert out.created is True
    assert (workspace_root / "a" / "b" / "c").is_dir()


@pytest.mark.asyncio
async def test_create_dir_is_idempotent(workspace_root, run_ctx):
    (workspace_root / "a").mkdir()
    out = await CreateDirTool().run(CreateDirInput(path="a"), run_ctx)
    assert out.created is False


@pytest.mark.asyncio
async def test_create_dir_rejects_when_path_is_a_file(workspace_root, run_ctx):
    (workspace_root / "a").write_text("i am a file")
    with pytest.raises(ToolError):
        await CreateDirTool().run(CreateDirInput(path="a"), run_ctx)


# --- move_file ---


@pytest.mark.asyncio
async def test_move_file_renames_within_same_dir(workspace_root, run_ctx):
    (workspace_root / "old.txt").write_text("content")
    out = await MoveFileTool().run(MoveFileInput(source="old.txt", destination="new.txt"), run_ctx)
    assert out.destination == "new.txt"
    assert not (workspace_root / "old.txt").exists()
    assert (workspace_root / "new.txt").read_text() == "content"


@pytest.mark.asyncio
async def test_move_file_moves_across_dirs_creating_parents(workspace_root, run_ctx):
    (workspace_root / "old.txt").write_text("content")
    await MoveFileTool().run(
        MoveFileInput(source="old.txt", destination="archive/2026/old.txt"), run_ctx
    )
    assert (workspace_root / "archive" / "2026" / "old.txt").read_text() == "content"


@pytest.mark.asyncio
async def test_move_file_refuses_overwrite_without_flag(workspace_root, run_ctx):
    (workspace_root / "old.txt").write_text("a")
    (workspace_root / "new.txt").write_text("b")
    with pytest.raises(ToolError):
        await MoveFileTool().run(MoveFileInput(source="old.txt", destination="new.txt"), run_ctx)


@pytest.mark.asyncio
async def test_move_file_rejects_missing_source(workspace_root, run_ctx):
    with pytest.raises(ToolError):
        await MoveFileTool().run(MoveFileInput(source="missing.txt", destination="x.txt"), run_ctx)


# --- delete_file ---


@pytest.mark.asyncio
async def test_delete_file_removes_file(workspace_root, run_ctx):
    (workspace_root / "a.txt").write_text("x")
    out = await DeleteFileTool().run(DeleteFileInput(path="a.txt"), run_ctx)
    assert out.was_directory is False
    assert not (workspace_root / "a.txt").exists()


@pytest.mark.asyncio
async def test_delete_file_removes_directory_recursively(workspace_root, run_ctx):
    (workspace_root / "sub" / "nested").mkdir(parents=True)
    (workspace_root / "sub" / "nested" / "f.txt").write_text("x")
    out = await DeleteFileTool().run(DeleteFileInput(path="sub"), run_ctx)
    assert out.was_directory is True
    assert not (workspace_root / "sub").exists()


@pytest.mark.asyncio
async def test_delete_file_refuses_to_delete_workspace_root(workspace_root, run_ctx):
    with pytest.raises(ToolError):
        await DeleteFileTool().run(DeleteFileInput(path="."), run_ctx)
    assert workspace_root.exists()


@pytest.mark.asyncio
async def test_delete_file_rejects_missing_path(workspace_root, run_ctx):
    with pytest.raises(ToolError):
        await DeleteFileTool().run(DeleteFileInput(path="missing.txt"), run_ctx)


def test_delete_file_requires_approval_by_default():
    decision = DeleteFileTool().evaluate_permission({}, {})
    assert decision.requires_approval is True


# --- search ---


@pytest.mark.asyncio
async def test_search_matches_filename(workspace_root, run_ctx):
    (workspace_root / "report_final.md").write_text("nothing relevant")
    (workspace_root / "other.md").write_text("nothing relevant either")
    out = await SearchTool().run(SearchInput(query="report_final"), run_ctx)
    assert [m.path for m in out.matches] == ["report_final.md"]
    assert out.matches[0].match_type == "name"


@pytest.mark.asyncio
async def test_search_matches_content_with_snippet(workspace_root, run_ctx):
    (workspace_root / "notes.txt").write_text("the quick brown fox jumps over the lazy dog")
    out = await SearchTool().run(SearchInput(query="brown fox"), run_ctx)
    assert len(out.matches) == 1
    assert out.matches[0].match_type == "content"
    assert "brown fox" in out.matches[0].snippet


@pytest.mark.asyncio
async def test_search_content_disabled_only_matches_names(workspace_root, run_ctx):
    (workspace_root / "notes.txt").write_text("mentions unique_needle here")
    out = await SearchTool().run(SearchInput(query="unique_needle", search_content=False), run_ctx)
    assert out.matches == []


@pytest.mark.asyncio
async def test_search_respects_max_results(workspace_root, run_ctx):
    for i in range(5):
        (workspace_root / f"match_{i}.txt").write_text("x")
    out = await SearchTool().run(SearchInput(query="match_", max_results=2), run_ctx)
    assert len(out.matches) == 2
    assert out.truncated is True


# --- generate_report ---


@pytest.mark.asyncio
async def test_generate_report_writes_markdown_into_reports_dir(workspace_root, run_ctx):
    out = await GenerateReportTool().run(
        GenerateReportInput(title="Job Search Summary", content="Found 3 matches."), run_ctx
    )
    assert out.path == "reports/job-search-summary.md"
    written = (workspace_root / out.path).read_text()
    assert written.startswith("# Job Search Summary\n")
    assert "Found 3 matches." in written


@pytest.mark.asyncio
async def test_generate_report_refuses_overwrite_without_flag(workspace_root, run_ctx):
    tool = GenerateReportTool()
    await tool.run(GenerateReportInput(title="Report", content="v1"), run_ctx)
    with pytest.raises(ToolError):
        await tool.run(GenerateReportInput(title="Report", content="v2"), run_ctx)


def test_generate_report_is_auto_approved():
    decision = GenerateReportTool().evaluate_permission({}, {})
    assert decision.requires_approval is False


# --- shared path traversal protection ---


@pytest.mark.asyncio
@pytest.mark.parametrize("bad_path", ["../escape.txt", "/etc/passwd", "a/../../escape.txt"])
async def test_write_file_rejects_path_escape(workspace_root, run_ctx, bad_path):
    with pytest.raises(WorkspacePathError):
        await WriteFileTool().run(WriteFileInput(path=bad_path, content="x"), run_ctx)


@pytest.mark.asyncio
async def test_read_file_rejects_symlink_escape(tmp_path, workspace_root, run_ctx):
    outside = tmp_path / "outside.txt"
    outside.write_text("secret")
    (workspace_root / "link.txt").symlink_to(outside)
    with pytest.raises(WorkspacePathError):
        await ReadFileTool().run(ReadFileInput(path="link.txt"), run_ctx)
