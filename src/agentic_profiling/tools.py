import ast
import re
import subprocess
import sys
import tempfile
import time

import requests
import sympy

WIKI_API = "https://en.wikipedia.org/w/api.php"
USER_AGENT = "agentic-profiling/0.1 (research project; https://github.com/Carlos28042003/agent-profilling)"
MAX_OBS_CHARS = 1500
INTRO_CHARS = 1000
SENTENCE_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(])")


def _wiki_get(params: dict, retries: int = 5) -> dict:
    for attempt in range(retries):
        try:
            r = requests.get(WIKI_API, params={**params, "format": "json"},
                             headers={"User-Agent": USER_AGENT}, timeout=15)
            r.raise_for_status()
            return r.json()
        except requests.RequestException:
            if attempt == retries - 1:
                raise
            time.sleep(2 ** (attempt + 1))
    raise AssertionError("unreachable")


class WikiSession:

    def __init__(self) -> None:
        self.title: str | None = None
        self.sentences: list[str] = []
        self.keyword: str | None = None
        self.hits: list[str] = []
        self.cursor = 0

    def search(self, query: str) -> str:
        hits = _wiki_get({"action": "query", "list": "search", "srsearch": query, "srlimit": 5})
        titles = [h["title"] for h in hits.get("query", {}).get("search", [])]
        if not titles:
            return f"No Wikipedia results for {query!r}. Try a shorter query, e.g. just a name."

        pages = _wiki_get({"action": "query", "prop": "extracts", "explaintext": 1,
                           "redirects": 1, "titles": titles[0]})["query"]["pages"]
        text = next(iter(pages.values())).get("extract", "").strip()
        body = re.sub(r"\n+=+[^=\n]+=+\n+", "\n", text)
        self.title = titles[0]
        self.sentences = [s.strip() for s in SENTENCE_RE.split(body.replace("\n", " ")) if s.strip()]
        self.keyword, self.hits, self.cursor = None, [], 0

        intro = text.split("\n\n\n==")[0].replace("\n", " ")
        if len(intro) > INTRO_CHARS:
            intro = intro[:INTRO_CHARS].rsplit(" ", 1)[0] + " ..."
        out = f"[{titles[0]}] {intro}"
        if len(titles) > 1:
            out += "\nOther pages: " + ", ".join(titles[1:])
        return out[:MAX_OBS_CHARS]

    def lookup(self, keyword: str) -> str:
        if not self.title:
            return "Error: no page open. Use search first."
        keyword = keyword.strip().strip("\"'")
        if keyword.lower() != (self.keyword or "").lower():
            self.keyword = keyword
            self.hits = [s for s in self.sentences if keyword.lower() in s.lower()]
            self.cursor = 0
        if not self.hits:
            return f"No sentence in [{self.title}] contains {keyword!r}."
        if self.cursor >= len(self.hits):
            return f"No more results for {keyword!r} in [{self.title}]."
        self.cursor += 1
        return f"(Result {self.cursor}/{len(self.hits)} in [{self.title}]) {self.hits[self.cursor - 1]}"[:MAX_OBS_CHARS]


_CALC_NODES = (
    ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant, ast.Call, ast.Name, ast.Load,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow, ast.USub, ast.UAdd,
)
_CALC_FUNCS = {"sqrt", "log", "exp", "sin", "cos", "tan", "pi", "E", "Abs", "floor", "ceiling"}


def calculator(expression: str) -> str:
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


def make_tools() -> dict:
    wiki = WikiSession()
    return {
        "search": (wiki.search, ("search: input is a search query (best: a name or title); returns the "
                                 "introduction of the best Wikipedia page and the titles of other matches.")),
        "lookup": (wiki.lookup, ("lookup: input is a keyword; returns the next sentence of the current "
                                 "Wikipedia page that contains it (e.g. lookup born).")),
        "calculator": (calculator, "calculator: input is an arithmetic expression, e.g. 3 * (4 + 5) / 2."),
        "python": (python_exec, "python: input is Python code; returns what it prints. Always print() the result."),
    }
