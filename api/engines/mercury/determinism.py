"""
Winter AI -- Mercury-style Determinism Layer.

HONEST NOTE: Mercury's real compiler (mmc) has no maintained apt/deb package
for modern Ubuntu/Debian. Building from source takes 30-60+ min -- impractical
for a Render Docker build. This module is an openly documented Python
re-implementation of Mercury's determinism categories rather than a fake.
See BUILD_REAL_MERCURY.md for an optional from-source path.
"""
from enum import Enum


class Determinism(str, Enum):
    DET = "det"          # exactly one solution
    SEMIDET = "semidet"  # zero or one solution
    MULTI = "multi"      # one or more solutions
    NONDET = "nondet"    # zero or more solutions
    FAILURE = "failure"  # never succeeds


def classify(matches: list) -> dict:
    n = len(matches)
    if n == 0:   mode = Determinism.FAILURE
    elif n == 1: mode = Determinism.DET
    else:        mode = Determinism.NONDET
    return {
        "engine": "Mercury-style (Python re-implementation)",
        "determinism": mode.value,
        "solution_count": n,
        "trace": f":- pred respond(Query::in, Answer::out) is {mode.value}.  % {n} solution(s)",
    }
