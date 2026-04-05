"""GLM 5.1 tool definitions for Code Autopsy"""
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List the file tree of the cloned repository. Returns file paths and sizes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path_prefix": {"type": "string", "description": "Optional path prefix to filter files"},
                    "extension": {"type": "string", "description": "Optional file extension filter (e.g. '.py', '.js')"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a specific file in the repository.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path relative to repo root"},
                    "lines": {"type": "integer", "description": "Max lines to read (default 200)"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "git_log",
            "description": "Get commit history with stats. Shows commit hashes, authors, dates, messages.",
            "parameters": {
                "type": "object",
                "properties": {
                    "count": {"type": "integer", "description": "Number of commits to retrieve (default 50)"},
                    "author": {"type": "string", "description": "Filter by author"},
                    "after": {"type": "string", "description": "Only commits after this date (YYYY-MM-DD)"},
                    "before": {"type": "string", "description": "Only commits before this date (YYYY-MM-DD)"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "git_blame",
            "description": "Get git blame for a specific file to see who wrote what.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to blame"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "git_diff",
            "description": "Get the diff for a specific commit.",
            "parameters": {
                "type": "object",
                "properties": {
                    "commit": {"type": "string", "description": "Commit hash"}
                },
                "required": ["commit"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_issues",
            "description": "List GitHub issues for the repository (open and closed).",
            "parameters": {
                "type": "object",
                "properties": {
                    "state": {"type": "string", "enum": ["open", "closed", "all"], "description": "Issue state filter (default 'all')"},
                    "count": {"type": "integer", "description": "Number of issues to retrieve (default 30)"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_pull_requests",
            "description": "List GitHub pull requests for the repository.",
            "parameters": {
                "type": "object",
                "properties": {
                    "state": {"type": "string", "enum": ["open", "closed", "all"], "description": "PR state filter (default 'all')"},
                    "count": {"type": "integer", "description": "Number of PRs to retrieve (default 20)"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_contributors",
            "description": "Get contributor statistics for the repository.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_complexity",
            "description": "Analyze code complexity for key files. Returns line counts, file sizes, and structure analysis.",
            "parameters": {
                "type": "object",
                "properties": {
                    "paths": {"type": "array", "items": {"type": "string"}, "description": "List of file paths to analyze"}
                },
                "required": ["paths"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_code",
            "description": "Search for a pattern in the repository codebase.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Search pattern (regex supported)"},
                    "file_type": {"type": "string", "description": "File type filter (e.g. 'py', 'js', 'ts')"}
                },
                "required": ["pattern"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_commit_frequency",
            "description": "Get commit frequency over time (weekly buckets). Shows project activity patterns.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    }
]

TOOL_MAP = {t["function"]["name"]: t for t in TOOLS}
