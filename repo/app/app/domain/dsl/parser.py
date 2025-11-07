from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .validator import validate_dsl


def load_dsl(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text())
    if not isinstance(data, dict):
        raise ValueError("DSL must be a mapping")
    validate_dsl(data)
    return data
