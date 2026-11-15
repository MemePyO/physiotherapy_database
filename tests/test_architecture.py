"""Architecture guardrails.

The UI layer must talk to the service layer, never to the ``db`` repository
directly.  This keeps persistence swappable and testable.
"""

import ast
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UI_PATHS = [os.path.join(ROOT, "main.py"), os.path.join(ROOT, "ui"), os.path.join(ROOT, "dialogs")]


def _python_files(paths):
    for path in paths:
        if os.path.isfile(path):
            yield path
        else:
            for folder, _dirs, files in os.walk(path):
                for name in files:
                    if name.endswith(".py"):
                        yield os.path.join(folder, name)


def _imported_modules(tree):
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                yield node.module
            for alias in node.names:
                yield alias.name


def test_ui_does_not_import_db():
    violations = []
    for path in _python_files(UI_PATHS):
        with open(path, encoding="utf-8") as fh:
            tree = ast.parse(fh.read(), filename=path)
        for module in _imported_modules(tree):
            if module == "db" or module.startswith("db."):
                violations.append(os.path.relpath(path, ROOT))
                break
    assert not violations, "UI modules importing db directly: " + ", ".join(sorted(violations))


def test_ui_imports_service_layer():
    """`main.py` should use services now that the layer exists."""
    with open(os.path.join(ROOT, "main.py"), encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    modules = set(_imported_modules(tree))
    assert any(m.startswith("services") for m in modules)
