"""GLM tool definitions for Code Autopsy — forensic repository analysis."""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List the file tree of the cloned repository. Returns file paths and sizes. Use path_prefix to drill into subdirectories.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path_prefix": {"type": "string", "description": "Optional path prefix to filter files (e.g. 'src/', 'backend/')"},
                    "extension": {"type": "string", "description": "Optional file extension filter (e.g. '.py', '.js', '.ts')"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a specific file in the repository. Use offset to skip lines for large files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path relative to repo root"},
                    "lines": {"type": "integer", "description": "Max lines to read (default 200)"},
                    "offset": {"type": "integer", "description": "Line number to start reading from (default 0)"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "git_log",
            "description": "Get commit history with stats. Shows commit hashes, authors, dates, messages, and changed files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "count": {"type": "integer", "description": "Number of commits to retrieve (default 50)"},
                    "author": {"type": "string", "description": "Filter by author name"},
                    "after": {"type": "string", "description": "Only commits after this date (YYYY-MM-DD)"},
                    "before": {"type": "string", "description": "Only commits before this date (YYYY-MM-DD)"},
                    "path": {"type": "string", "description": "Only commits that touched this file/directory"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "git_blame",
            "description": "Get git blame for a specific file — shows who wrote each line and when.",
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
            "description": "Get the full diff for a specific commit — see exactly what changed.",
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
            "description": "List GitHub issues — reveals community frustration, unresolved bugs, feature creep.",
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
            "description": "List GitHub pull requests — reveals contributor churn, rejected contributions, review patterns.",
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
            "description": "Get contributor statistics — commit counts per author. Reveals bus factor and contributor drop-off.",
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
            "description": "Deep complexity analysis of files — line counts, function counts, nesting depth, code smells (TODOs, HACKs, long functions).",
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
            "description": "Search for a regex pattern across the codebase — find TODOs, deprecated APIs, security issues, dead code.",
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
            "description": "Get commit frequency by month — reveals project momentum, activity surges, and periods of abandonment.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_dependencies",
            "description": "Analyze project dependencies from package.json, requirements.txt, pyproject.toml, Cargo.toml, go.mod, Gemfile. Shows dependency count, pinning strategy, and known issues.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_tests",
            "description": "Analyze test infrastructure — checks for test files, test frameworks, coverage config, test-to-source ratio.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_file_history",
            "description": "Get the change history of a specific file — how many times it was modified, by whom, and when. Reveals hotspot files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to check history for"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_repo_health",
            "description": "Get overall repository health metrics — total commits, active period, last commit date, file count, total lines of code, languages breakdown, bus factor.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_commit_messages",
            "description": "Analyze commit message quality and sentiment — detects rushed commits, frustration, panic patterns, conventional commit usage.",
            "parameters": {
                "type": "object",
                "properties": {
                    "count": {"type": "integer", "description": "Number of recent commits to analyze (default 50)"}
                },
                "required": []
            }
        }
    }
]

TOOL_MAP = {t["function"]["name"]: t for t in TOOLS}
