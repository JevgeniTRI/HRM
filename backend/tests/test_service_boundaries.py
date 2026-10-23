"""Keep domain operations independent of the HTTP framework as the project grows."""

import ast
from pathlib import Path


def test_services_do_not_import_http_frameworks():
    directory = Path(__file__).resolve().parents[1] / "app" / "services"
    violations = []
    for path in directory.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            names = []
            if isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            elif isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            if any(name.split(".")[0] in {"fastapi", "starlette"} for name in names):
                violations.append(f"{path.name}:{node.lineno}")
    assert not violations, f"HTTP dependencies in services: {violations}"
