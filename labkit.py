"""Shared helpers for the labs. You never need to edit this file."""

import importlib.util
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))

_COLOR = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None


def _c(code, text):
    return f"\033[{code}m{text}\033[0m" if _COLOR else text


def bold(t): return _c("1", t)
def red(t): return _c("31", t)
def green(t): return _c("32", t)
def yellow(t): return _c("33", t)
def dim(t): return _c("2", t)


def header(title):
    print()
    print(bold(title))
    print(dim("-" * len(title)))


def load_impl(lab_dir, name="app"):
    """Import the code under test: your app.py by default.

    LAB_IMPL=solution loads solution/app.py; LAB_IMPL=<directory> loads <directory>/app.py.
    """
    if lab_dir not in sys.path:
        sys.path.insert(0, lab_dir)
    impl = os.environ.get("LAB_IMPL", "")
    if impl == "solution":
        folder = os.path.join(lab_dir, "solution")
    elif impl and os.path.isdir(impl):
        folder = impl
    else:
        folder = lab_dir
    spec = importlib.util.spec_from_file_location(name, os.path.join(folder, name + ".py"))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def percentile(values, p):
    if not values:
        return float("nan")
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round(p / 100 * len(ordered)) - 1))
    return ordered[index]


def ms(seconds):
    return f"{seconds * 1000:.1f}ms"


def table(headers, rows):
    cells = [[str(c) for c in row] for row in rows]
    widths = [max(len(h), *(len(r[i]) for r in cells)) if cells else len(h) for i, h in enumerate(headers)]
    print("  ".join(bold(h.ljust(w)) for h, w in zip(headers, widths)))
    for row in cells:
        print("  ".join(c.ljust(w) for c, w in zip(row, widths)))


class Checker:
    """Collects pass/fail expectations and exits non-zero if any failed."""

    def __init__(self, title):
        self.failures = 0
        header(f"CHECK: {title}")

    def expect(self, condition, label, detail=""):
        mark = green("PASS") if condition else red("FAIL")
        print(f"  [{mark}] {label}" + (dim(f"  ({detail})") if detail else ""))
        if not condition:
            self.failures += 1
        return condition

    def done(self):
        print()
        if self.failures:
            print(red(bold(f"{self.failures} expectation(s) failed.")) +
                  " Read the failures, form a hypothesis, and investigate.")
            sys.exit(1)
        print(green(bold("All expectations passed.")) +
              " Now read solution/NOTES.md to see what a senior engineer would add.")
        sys.exit(0)
