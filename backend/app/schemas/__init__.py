import importlib.util
from pathlib import Path

module_path = Path(__file__).resolve().parents[1] / "schemas.py"
spec = importlib.util.spec_from_file_location("backend.app.schemas_module", module_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

for name in dir(module):
    if not name.startswith("_"):
        globals()[name] = getattr(module, name)

__all__ = [name for name in globals() if not name.startswith("_")]
