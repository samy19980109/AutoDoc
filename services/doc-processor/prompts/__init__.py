"""Prompt templates for AI-powered code analysis and documentation generation."""

# ---------------------------------------------------------------------------
# Code Analysis
# ---------------------------------------------------------------------------

CODE_ANALYSIS_SYSTEM = (
    "You are a senior software architect performing structured code analysis. "
    "Your output MUST be valid JSON.  Do not include markdown fences or commentary "
    "outside the JSON object."
)

CODE_ANALYSIS_PROMPT = """\
Analyze the following source files and produce a JSON object with these keys:

{{
  "summary": "A concise paragraph describing the overall purpose of this codebase.",
  "functions": [
    {{
      "name": "function_name",
      "file": "relative/path.py",
      "signature": "def function_name(args) -> return_type",
      "description": "What this function does.",
      "params": [{{"name": "arg", "type": "str", "description": "..."}}],
      "returns": "Description of the return value."
    }}
  ],
  "classes": [
    {{
      "name": "ClassName",
      "file": "relative/path.py",
      "description": "What this class represents.",
      "methods": ["method_a", "method_b"]
    }}
  ],
  "api_endpoints": [
    {{
      "method": "GET",
      "path": "/api/v1/resource",
      "file": "relative/path.py",
      "description": "What this endpoint does.",
      "request_body": "optional schema description",
      "response": "response description"
    }}
  ],
  "dependencies": [
    {{
      "name": "package_name",
      "purpose": "Why this dependency is used."
    }}
  ],
  "architecture_patterns": [
    "Pattern description, e.g. 'Repository pattern for data access'"
  ]
}}

--- SOURCE FILES ---
{file_contents}
--- END SOURCE FILES ---
"""

# ---------------------------------------------------------------------------
# API Reference
# ---------------------------------------------------------------------------

API_REFERENCE_SYSTEM = (
    "You are a technical writer creating comprehensive API reference documentation. "
    "Output well-structured HTML suitable for Confluence.  Use <h2>, <h3>, <table>, "
    "<code>, and <pre> tags.  Do not wrap output in markdown fences."
)

API_REFERENCE_PROMPT = """\
Using the structured code analysis below, generate an API Reference document in HTML.

Include the following sections:
1. **Overview** -- brief summary of the API surface.
2. **Endpoints** -- for each endpoint list method, path, description, request/response
   schemas in an HTML table.
3. **Functions & Methods** -- public functions with signatures and descriptions.
4. **Data Models** -- classes and their fields.

Analysis:
{analysis_json}

{existing_context}
"""

# ---------------------------------------------------------------------------
# Architecture
# ---------------------------------------------------------------------------

ARCHITECTURE_SYSTEM = (
    "You are a senior architect documenting system design. "
    "Output well-structured HTML suitable for Confluence.  Use <h2>, <h3>, <ul>, "
    "<code>, and <pre> tags.  Do not wrap output in markdown fences."
)

ARCHITECTURE_PROMPT = """\
Using the structured code analysis below, generate an Architecture Overview document
in HTML.

Include:
1. **System Overview** -- high-level purpose and components.
2. **Architecture Patterns** -- patterns identified (e.g. microservices, event-driven).
3. **Component Diagram** -- describe the components and their relationships in prose
   (or an ASCII diagram inside a <pre> tag).
4. **Dependencies** -- external services and libraries with purpose.
5. **Data Flow** -- how data moves through the system.

Analysis:
{analysis_json}

{existing_context}
"""

# ---------------------------------------------------------------------------
# Walkthrough
# ---------------------------------------------------------------------------

WALKTHROUGH_SYSTEM = (
    "You are a developer advocate writing a friendly yet thorough code walkthrough. "
    "Output well-structured HTML suitable for Confluence.  Use <h2>, <h3>, <p>, "
    "<code>, and <pre> tags.  Do not wrap output in markdown fences."
)

WALKTHROUGH_PROMPT = """\
Using the structured code analysis below, generate a Developer Walkthrough document
in HTML.

Include:
1. **Getting Started** -- prerequisites and setup.
2. **Project Structure** -- explain the directory layout.
3. **Key Concepts** -- important abstractions and patterns.
4. **Code Walkthrough** -- step-by-step explanation of core flows with code snippets.
5. **Common Tasks** -- how to add features, run tests, etc.

Analysis:
{analysis_json}

{existing_context}
"""
