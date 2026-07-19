"""Shared helper for invoking the polyglot subprocess engines."""
import subprocess, logging
from pathlib import Path

logger = logging.getLogger("winter.proc")
SAFE_ENV = {"LANG": "C.UTF-8", "LC_ALL": "C.UTF-8", "GUILE_AUTO_COMPILE": "0"}

def run(cmd: list, timeout: float = 5.0) -> dict:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=SAFE_ENV)
        if r.returncode != 0:
            logger.warning("subprocess %s exited %s: %s", cmd[0], r.returncode, r.stderr[:200])
        return {"ok": r.returncode == 0, "lines": _parse(r.stdout), "raw": r.stdout, "error": r.stderr}
    except FileNotFoundError:
        return {"ok": False, "lines": {}, "raw": "", "error": f"not found: {cmd[0]}"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "lines": {}, "raw": "", "error": "timeout"}
    except Exception as e:
        return {"ok": False, "lines": {}, "raw": "", "error": str(e)}

def _parse(text: str) -> dict:
    out = {}
    for line in text.splitlines():
        if ": " in line:
            k, _, v = line.partition(": ")
            k = k.strip()
            if k and (k.isupper() or "_" in k or "-" in k):
                out[k] = v.strip()
    return out
