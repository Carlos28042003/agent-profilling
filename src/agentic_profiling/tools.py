"""The agent's three tools: Wikipedia search, calculator and Python execution."""

import ast
import html
import re
import subprocess
import sys
import tempfile

import requests
import sympy

WIKI_API = "https://en.wikipedia.org/w/api.php"
USER_AGENT = "agentic-profiling/0.1 (research project; https://github.com/)"
MAX_OBS_CHARS = 1500


def wikipedia_search(query: str) -> str:
    """Search Wikipedia: summary of the best match + snippets of the next results."""
    headers = {"User-Agent": USER_AGENT}
    search = requests.get(
        WIKI_API,
        params={"action": "query", "list": "search", "srsearch": query,
                "srlimit": 5, "srprop": "snippet", "format": "json"},
        headers=headers, timeout=15,
    ).json()
    hits = search.get("query", {}).get("search", [])
    if not hits:
        return f"No Wikipedia results for {query!r}."

    pages = requests.get(
        WIKI_API,
        params={"action": "query", "prop": "extracts", "exintro": 1, "explaintext": 1,
                "redirects": 1, "titles": hits[0]["title"], "format": "json"},
        headers=headers, timeout=15,
    ).json()["query"]["pages"]
    extract = next(iter(pages.values())).get("extract", "").strip()

    out = f"[{hits[0]['title']}] {extract[:900]}"
    for h in hits[1:4]:
        snippet = html.unescape(re.sub(r"<[^>]+>", "", h["snippet"]))
        out += f"\n[{h['title']}] ...{snippet}..."
    return out[:MAX_OBS_CHARS]


_CALC_NODES = (
    ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant, ast.Call, ast.Name, ast.Load,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow, ast.USub, ast.UAdd,
)
_CALC_FUNCS = {"sqrt", "log", "exp", "sin", "cos", "tan", "pi", "E", "Abs", "floor", "ceiling"}


def calculator(expression: str) -> str:
    """Evaluate an arithmetic expression. The AST is validated before it reaches SymPy."""
    expression = expression.strip().strip("`").replace("^", "**")
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as e:
        return f"Error: invalid expression ({e.msg})."
    for node in ast.walk(tree):
        if not isinstance(node, _CALC_NODES):
            return f"Error: {type(node).__name__} is not allowed in calculator."
        if isinstance(node, ast.Name) and node.id not in _CALC_FUNCS:
            return f"Error: unknown name {node.id!r}."
    try:
        value = sympy.sympify(expression)
        return str(value.evalf(15) if not value.is_Integer else value)
    except Exception as e:  # noqa: BLE001 — the error goes back to the agent as an observation
        return f"Error: {e}"


def python_exec(code: str, timeout: float = 10.0) -> str:
    """Run Python code in an isolated subprocess (-I) in a temporary directory, with a timeout.

    Note: this limits accidental damage but is NOT a security sandbox.
    For untrusted code (SWE-bench), run it inside a container.
    """
    code = code.strip().removeprefix("```python").removeprefix("```").removesuffix("```").strip("`")
    with tempfile.TemporaryDirectory() as tmp:
        try:
            proc = subprocess.run(
                [sys.executable, "-I", "-X", "utf8", "-c", code],
                check=False, cwd=tmp, capture_output=True, text=True, encoding="utf-8", errors="replace",
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return f"Error: execution timed out after {timeout}s."
    out = proc.stdout
    if proc.returncode != 0:
        out += proc.stderr
    out = out.strip() or "(no output — use print() to show results)"
    return out[:MAX_OBS_CHARS]


TOOLS = {
    "search": (wikipedia_search, "search: input is a search query; returns the summary of the best Wikipedia match."),
    "calculator": (calculator, "calculator: input is an arithmetic expression, e.g. 3 * (4 + 5) / 2."),
    "python": (python_exec, "python: input is Python code; returns what it prints. Always print() the result."),
}
