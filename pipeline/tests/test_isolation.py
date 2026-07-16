import ast
import pathlib

ENGINE_PATH = pathlib.Path(__file__).resolve().parents[1] / "engine.py"
FORBIDDEN_IDENTIFIERS = {"upstream", "machine", "on20", "dist20"}


def _identifiers(tree: ast.AST) -> set[str]:
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
        elif isinstance(node, ast.arg):
            names.add(node.arg)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.alias):
            names.add(node.name)
            if node.asname:
                names.add(node.asname)
    return names


def test_engine_never_references_upstream_feed_symbols():
    source = ENGINE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    found = _identifiers(tree) & FORBIDDEN_IDENTIFIERS
    assert not found, f"engine.py must never reference upstream-only symbols: {found}"


def test_engine_does_not_import_requests():
    source = ENGINE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    assert "requests" not in imported
