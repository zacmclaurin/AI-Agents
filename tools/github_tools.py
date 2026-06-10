"""GitHub tools — read, write, list files, and push commits to any repo."""

import os
import base64
from github import Github, GithubException

# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------

def _get_repo(repo_name: str):
    """Return a PyGithub Repository object.

    repo_name format: "owner/repo"  e.g. "zacmclaurin/IronRoad"
    Reads GITHUB_TOKEN from the environment.
    """
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise EnvironmentError("GITHUB_TOKEN environment variable is not set.")
    g = Github(token)
    return g.get_repo(repo_name)


# ---------------------------------------------------------------------------
# Tool functions
# ---------------------------------------------------------------------------

def github_read_file(repo_name: str, file_path: str, branch: str = "main") -> str:
    """Read the contents of a file from a GitHub repo.

    Args:
        repo_name: "owner/repo"
        file_path: path inside the repo, e.g. "src/App.tsx"
        branch: branch name (default "main")

    Returns:
        Decoded file contents as a string, or an error message.
    """
    try:
        repo = _get_repo(repo_name)
        content_file = repo.get_contents(file_path, ref=branch)
        return base64.b64decode(content_file.content).decode("utf-8")
    except GithubException as e:
        return f"GitHub error: {e.status} {e.data}"
    except Exception as e:
        return f"Error reading file: {e}"


def github_write_file(
    repo_name: str,
    file_path: str,
    content: str,
    commit_message: str,
    branch: str = "main",
) -> str:
    """Create or update a file in a GitHub repo and commit it.

    Args:
        repo_name: "owner/repo"
        file_path: path inside the repo, e.g. "src/utils/helpers.ts"
        content: full file content as a string
        commit_message: the git commit message
        branch: branch name (default "main")

    Returns:
        Success message with commit SHA, or an error message.
    """
    try:
        repo = _get_repo(repo_name)
        try:
            existing = repo.get_contents(file_path, ref=branch)
            result = repo.update_file(
                path=file_path,
                message=commit_message,
                content=content,
                sha=existing.sha,
                branch=branch,
            )
            action = "Updated"
        except GithubException as e:
            if e.status != 404:
                raise
            result = repo.create_file(
                path=file_path,
                message=commit_message,
                content=content,
                branch=branch,
            )
            action = "Created"

        sha = result["commit"].sha
        return f"{action} {file_path} — commit {sha}"
    except GithubException as e:
        return f"GitHub error: {e.status} {e.data}"
    except Exception as e:
        return f"Error writing file: {e}"


def github_list_files(
    repo_name: str,
    directory: str = "",
    branch: str = "main",
) -> str:
    """List files and directories at a given path in a GitHub repo.

    Args:
        repo_name: "owner/repo"
        directory: path to list (empty string = repo root)
        branch: branch name (default "main")

    Returns:
        Newline-separated list of paths, or an error message.
    """
    try:
        repo = _get_repo(repo_name)
        contents = repo.get_contents(directory or "", ref=branch)
        if not isinstance(contents, list):
            contents = [contents]
        lines = [
            f"[{'dir ' if c.type == 'dir' else 'file'}] {c.path}"
            for c in sorted(contents, key=lambda c: (c.type != "dir", c.path))
        ]
        return "\n".join(lines) if lines else "(empty)"
    except GithubException as e:
        return f"GitHub error: {e.status} {e.data}"
    except Exception as e:
        return f"Error listing files: {e}"


def github_push_commit(
    repo_name: str,
    files: dict[str, str],
    commit_message: str,
    branch: str = "main",
) -> str:
    """Push multiple file changes as a single commit using the Git Data API.

    Args:
        repo_name: "owner/repo"
        files: dict mapping file_path -> new_content (strings)
        commit_message: the git commit message
        branch: branch name (default "main")

    Returns:
        Success message with commit SHA, or an error message.
    """
    try:
        repo = _get_repo(repo_name)
        ref = repo.get_git_ref(f"heads/{branch}")
        base_sha = ref.object.sha
        base_tree = repo.get_git_commit(base_sha).tree

        blobs = []
        for path, content in files.items():
            blob = repo.create_git_blob(content, "utf-8")
            blobs.append({
                "path": path,
                "mode": "100644",
                "type": "blob",
                "sha": blob.sha,
            })

        new_tree = repo.create_git_tree(blobs, base_tree)
        new_commit = repo.create_git_commit(commit_message, new_tree, [repo.get_git_commit(base_sha)])
        ref.edit(new_commit.sha)

        return f"Pushed {len(files)} file(s) to {branch} — commit {new_commit.sha}"
    except GithubException as e:
        return f"GitHub error: {e.status} {e.data}"
    except Exception as e:
        return f"Error pushing commit: {e}"


# ---------------------------------------------------------------------------
# CrewAI tool definitions (passed to Agent as tools=[])
# ---------------------------------------------------------------------------

GITHUB_TOOLS = [
    {
        "name": "github_read_file",
        "description": "Read the contents of a file from a GitHub repository.",
        "input_schema": {
            "type": "object",
            "properties": {
                "repo_name": {"type": "string", "description": "owner/repo, e.g. zacmclaurin/IronRoad"},
                "file_path": {"type": "string", "description": "Path to the file inside the repo"},
                "branch":    {"type": "string", "description": "Branch name (default: main)"},
            },
            "required": ["repo_name", "file_path"],
        },
    },
    {
        "name": "github_write_file",
        "description": "Create or update a single file in a GitHub repo and commit it.",
        "input_schema": {
            "type": "object",
            "properties": {
                "repo_name":      {"type": "string", "description": "owner/repo"},
                "file_path":      {"type": "string", "description": "Path to the file inside the repo"},
                "content":        {"type": "string", "description": "Full file content"},
                "commit_message": {"type": "string", "description": "Git commit message"},
                "branch":         {"type": "string", "description": "Branch name (default: main)"},
            },
            "required": ["repo_name", "file_path", "content", "commit_message"],
        },
    },
    {
        "name": "github_list_files",
        "description": "List files and directories at a path in a GitHub repo.",
        "input_schema": {
            "type": "object",
            "properties": {
                "repo_name": {"type": "string", "description": "owner/repo"},
                "directory": {"type": "string", "description": "Directory path (empty = root)"},
                "branch":    {"type": "string", "description": "Branch name (default: main)"},
            },
            "required": ["repo_name"],
        },
    },
    {
        "name": "github_push_commit",
        "description": "Push multiple file changes as a single atomic commit to a GitHub repo.",
        "input_schema": {
            "type": "object",
            "properties": {
                "repo_name":      {"type": "string", "description": "owner/repo"},
                "files":          {
                    "type": "object",
                    "description": "Map of file_path -> file_content strings",
                    "additionalProperties": {"type": "string"},
                },
                "commit_message": {"type": "string", "description": "Git commit message"},
                "branch":         {"type": "string", "description": "Branch name (default: main)"},
            },
            "required": ["repo_name", "files", "commit_message"],
        },
    },
]


TOOL_HANDLERS = {
    "github_read_file":  lambda i: github_read_file(**i),
    "github_write_file": lambda i: github_write_file(**i),
    "github_list_files": lambda i: github_list_files(**i),
    "github_push_commit": lambda i: github_push_commit(**i),
}


def handle_github_tool(name: str, inputs: dict) -> str:
    handler = TOOL_HANDLERS.get(name)
    if not handler:
        return f"Unknown GitHub tool: {name}"
    return handler(inputs)
