"""GitHub tools — read, write, list files, and push commits to any repo."""

import os
import base64
from typing import Type
from pydantic import BaseModel, Field
from crewai.tools import BaseTool
from github import Github, GithubException


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------

def _get_repo(repo_name: str):
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise EnvironmentError("GITHUB_TOKEN environment variable is not set.")
    return Github(token).get_repo(repo_name)


# ---------------------------------------------------------------------------
# ReadFile
# ---------------------------------------------------------------------------

class ReadFileInput(BaseModel):
    repo_name: str = Field(..., description="owner/repo, e.g. zacmclaurin/IronRoad")
    file_path: str = Field(..., description="Path to the file inside the repo")
    branch: str = Field("main", description="Branch name")


class GitHubReadFileTool(BaseTool):
    name: str = "github_read_file"
    description: str = "Read the contents of a file from a GitHub repository."
    args_schema: Type[BaseModel] = ReadFileInput

    def _run(self, repo_name: str, file_path: str, branch: str = "main") -> str:
        try:
            repo = _get_repo(repo_name)
            content_file = repo.get_contents(file_path, ref=branch)
            return base64.b64decode(content_file.content).decode("utf-8")
        except GithubException as e:
            return f"GitHub error: {e.status} {e.data}"
        except Exception as e:
            return f"Error reading file: {e}"


# ---------------------------------------------------------------------------
# WriteFile
# ---------------------------------------------------------------------------

class WriteFileInput(BaseModel):
    repo_name: str = Field(..., description="owner/repo")
    file_path: str = Field(..., description="Path to the file inside the repo")
    content: str = Field(..., description="Full file content to write")
    commit_message: str = Field(..., description="Git commit message")
    branch: str = Field("main", description="Branch name")


class GitHubWriteFileTool(BaseTool):
    name: str = "github_write_file"
    description: str = "Create or update a single file in a GitHub repo and commit it."
    args_schema: Type[BaseModel] = WriteFileInput

    def _run(
        self,
        repo_name: str,
        file_path: str,
        content: str,
        commit_message: str,
        branch: str = "main",
    ) -> str:
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


# ---------------------------------------------------------------------------
# ListFiles
# ---------------------------------------------------------------------------

class ListFilesInput(BaseModel):
    repo_name: str = Field(..., description="owner/repo")
    directory: str = Field("", description="Directory path (empty string = repo root)")
    branch: str = Field("main", description="Branch name")


class GitHubListFilesTool(BaseTool):
    name: str = "github_list_files"
    description: str = "List files and directories at a path in a GitHub repo."
    args_schema: Type[BaseModel] = ListFilesInput

    def _run(self, repo_name: str, directory: str = "", branch: str = "main") -> str:
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


# ---------------------------------------------------------------------------
# PushCommit
# ---------------------------------------------------------------------------

class PushCommitInput(BaseModel):
    repo_name: str = Field(..., description="owner/repo")
    files: dict = Field(..., description="Map of file_path -> file_content strings")
    commit_message: str = Field(..., description="Git commit message")
    branch: str = Field("main", description="Branch name")


class GitHubPushCommitTool(BaseTool):
    name: str = "github_push_commit"
    description: str = (
        "Push multiple file changes as a single atomic commit to a GitHub repo "
        "using the Git Data API."
    )
    args_schema: Type[BaseModel] = PushCommitInput

    def _run(
        self,
        repo_name: str,
        files: dict,
        commit_message: str,
        branch: str = "main",
    ) -> str:
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
            new_commit = repo.create_git_commit(
                commit_message, new_tree, [repo.get_git_commit(base_sha)]
            )
            ref.edit(new_commit.sha)
            return f"Pushed {len(files)} file(s) to {branch} — commit {new_commit.sha}"
        except GithubException as e:
            return f"GitHub error: {e.status} {e.data}"
        except Exception as e:
            return f"Error pushing commit: {e}"


# ---------------------------------------------------------------------------
# Standalone helper used by the /github endpoint
# ---------------------------------------------------------------------------

def github_write_file(
    repo_name: str,
    file_path: str,
    content: str | None = None,
    changes: list[dict] | None = None,
    commit_message: str = "Update file",
    branch: str = "main",
) -> str:
    """
    Write or patch a file on GitHub.

    Pass `content` to create or fully replace a file.
    Pass `changes` (list of {search, replace} dicts) to apply targeted patches
    to an existing file — reads the current content, applies each replacement
    in order, then writes back.
    """
    try:
        token = os.environ.get("GITHUB_TOKEN")
        if not token:
            return "Error: GITHUB_TOKEN environment variable is not set."
        repo = Github(token).get_repo(repo_name)
    except GithubException as e:
        return f"GitHub error: {e.status} {e.data}"
    except Exception as e:
        return f"Error connecting to GitHub: {e}"

    if changes is not None:
        try:
            existing_file = repo.get_contents(file_path, ref=branch)
            text = base64.b64decode(existing_file.content).decode("utf-8")
            sha = existing_file.sha
        except GithubException as e:
            return f"GitHub error reading {file_path}: {e.status} {e.data}"
        except Exception as e:
            return f"Error reading {file_path}: {e}"

        patched = text
        for i, change in enumerate(changes):
            search_str = change.get("search", "")
            replace_str = change.get("replace", "")
            if not search_str:
                return f"Error: change {i + 1} has an empty search string."
            if search_str not in patched:
                return f"Error: search string for change {i + 1} not found in {file_path}."
            patched = patched.replace(search_str, replace_str, 1)

        try:
            result = repo.update_file(file_path, commit_message, patched, sha, branch=branch)
            return f"Patched {len(changes)} change(s) in {file_path} — commit {result['commit'].sha}"
        except GithubException as e:
            return f"GitHub error writing {file_path}: {e.status} {e.data}"
        except Exception as e:
            return f"Error writing {file_path}: {e}"

    if content is not None:
        try:
            try:
                existing = repo.get_contents(file_path, ref=branch)
                result = repo.update_file(file_path, commit_message, content, existing.sha, branch=branch)
                action = "Updated"
            except GithubException as e:
                if e.status != 404:
                    raise
                result = repo.create_file(file_path, commit_message, content, branch=branch)
                action = "Created"
            return f"{action} {file_path} — commit {result['commit'].sha}"
        except GithubException as e:
            return f"GitHub error: {e.status} {e.data}"
        except Exception as e:
            return f"Error writing file: {e}"

    return "Error: either 'content' or 'changes' must be provided."


# ---------------------------------------------------------------------------
# Exported list for use in agents
# ---------------------------------------------------------------------------

GITHUB_TOOLS = [
    GitHubReadFileTool(),
    GitHubWriteFileTool(),
    GitHubListFilesTool(),
    GitHubPushCommitTool(),
]
