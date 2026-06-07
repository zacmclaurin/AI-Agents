"""File read/write tools in Anthropic tool-use format."""

from pathlib import Path

FILE_TOOLS = [
    {
        "name": "read_file",
        "description": "Read the contents of a file at the given path.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Absolute or relative file path"}
            },
            "required": ["path"],
        },
    },
    {
        "name": "write_file",
        "description": "Write content to a file, creating it if it does not exist.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path to write to"},
                "content": {"type": "string", "description": "Content to write"},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "list_files",
        "description": "List files in a directory.",
        "input_schema": {
            "type": "object",
            "properties": {
                "directory": {"type": "string", "description": "Directory path to list"}
            },
            "required": ["directory"],
        },
    },
]


def handle_tool_call(name: str, inputs: dict) -> str:
    """Execute a file tool call and return a string result."""
    if name == "read_file":
        path = Path(inputs["path"])
        if not path.exists():
            return f"Error: {path} does not exist"
        return path.read_text(encoding="utf-8")

    if name == "write_file":
        path = Path(inputs["path"])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(inputs["content"], encoding="utf-8")
        return f"Wrote {len(inputs['content'])} characters to {path}"

    if name == "list_files":
        directory = Path(inputs["directory"])
        if not directory.is_dir():
            return f"Error: {directory} is not a directory"
        files = [str(p) for p in sorted(directory.iterdir())]
        return "\n".join(files) if files else "(empty)"

    return f"Unknown tool: {name}"
