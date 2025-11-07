from __future__ import annotations

import builtins
import multiprocessing as mp
import os
import resource
import sys
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from types import MappingProxyType
from typing import Any, Dict

from . import nmc_sdk

ALLOWED_MODULES = {
    "nmc_sdk",
    "datetime",
    "json",
    "math",
    "csv",
    "io",
    "typing",
    "textwrap",
    "base64",
}

SAFE_BUILTINS = {
    "abs": builtins.abs,
    "all": builtins.all,
    "any": builtins.any,
    "bool": builtins.bool,
    "dict": builtins.dict,
    "enumerate": builtins.enumerate,
    "float": builtins.float,
    "int": builtins.int,
    "len": builtins.len,
    "list": builtins.list,
    "map": builtins.map,
    "max": builtins.max,
    "min": builtins.min,
    "print": builtins.print,
    "range": builtins.range,
    "round": builtins.round,
    "str": builtins.str,
    "sum": builtins.sum,
    "zip": builtins.zip,
}


def _restricted_import(name: str, globals: dict | None = None, locals: dict | None = None, fromlist=(), level: int = 0):  # noqa: ANN001,ANN201
    root = name.split(".")[0]
    if root not in ALLOWED_MODULES:
        raise ImportError(f"Import of '{name}' not permitted")
    return original_import(name, globals, locals, fromlist, level)


original_import = builtins.__import__


def _child(code: str, env: dict[str, str], queue: mp.Queue, time_limit_s: float, mem_mb: int) -> None:
    try:
        os.environ.clear()
        os.environ.update(env)

        cpu_seconds = max(1, int(time_limit_s))
        mem_bytes = mem_mb * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds))
        resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))

        builtins.__import__ = _restricted_import  # type: ignore[assignment]
        builtins.open = lambda *args, **kwargs: (_ for _ in ()).throw(PermissionError("open not allowed"))  # type: ignore[attr-defined]

        sys.modules["nmc_sdk"] = nmc_sdk
        nmc_sdk.clear_call_log()

        stdout_buf = StringIO()
        stderr_buf = StringIO()
        safe_globals: Dict[str, Any] = {"__builtins__": MappingProxyType(SAFE_BUILTINS)}
        with redirect_stdout(stdout_buf), redirect_stderr(stderr_buf):
            exec(code, safe_globals, {})
        queue.put(
            {
                "status": "ok",
                "stdout": stdout_buf.getvalue(),
                "stderr": stderr_buf.getvalue(),
                "sdk_calls": nmc_sdk.get_call_log(),
            }
        )
    except Exception as exc:  # noqa: BLE001
        queue.put({"status": "error", "error": str(exc), "sdk_calls": nmc_sdk.get_call_log()})
    finally:
        builtins.__import__ = original_import


def run_user_code(code: str, env: dict[str, str], time_limit_s: float, mem_mb: int) -> dict[str, Any]:
    queue: mp.Queue = mp.Queue()
    process = mp.Process(target=_child, args=(code, env, queue, time_limit_s, mem_mb))
    process.start()
    process.join(time_limit_s)
    if process.is_alive():
        process.terminate()
        process.join()
        return {"status": "timeout", "stdout": "", "stderr": "", "sdk_calls": []}
    if not queue.empty():
        return queue.get()
    if process.exitcode != 0:
        return {"status": "error", "stdout": "", "stderr": f"Exit code {process.exitcode}", "sdk_calls": []}
    return {"status": "ok", "stdout": "", "stderr": "", "sdk_calls": []}
