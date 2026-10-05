#!/usr/bin/env python3
"""MYENGINEER: hands-on systems engineering labs.

    python3 lab.py                    list labs and your progress
    python3 lab.py run 01 [args]      run lab 01 and watch the symptoms
    python3 lab.py check 01           acceptance test for your fix
    python3 lab.py hint 01            reveal the next hint (one at a time)
    python3 lab.py journal 01         create journal/01.md for your investigation notes
    python3 lab.py notes 01           what a senior engineer sees (after you pass)
    python3 lab.py reset 01           restore lab 01's app.py to the original broken version

    python3 lab.py drill [N]          system design drills (paper first!)
    python3 lab.py review N           the reviewer's questions for drill N
    python3 lab.py estimate           back-of-envelope estimation practice

    python3 lab.py selftest           verify every lab: broken code fails, reference solution passes
"""

import datetime
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

from labkit import ROOT, bold, dim, green, header, red, yellow

LABS = [
    ("01", "01-slow-dashboard", "The Slow Dashboard", "indexes, query plans, N+1, planner statistics"),
    ("02", "02-flash-sale", "The Flash Sale", "race conditions, lost updates, transactions, locks"),
    ("03", "03-read-replicas", "Read Replicas", "replication lag, read-your-writes, LSNs, failover"),
    ("04", "04-cache-stampede", "The Cache Stampede", "TTL, thundering herd, single-flight, jitter"),
    ("05", "05-double-charge", "The Double Charge", "timeouts, retries, idempotency, backoff"),
    ("06", "06-sharding", "Sharding", "partitioning, consistent hashing, resharding, hot keys"),
    ("07", "07-overload", "Overload", "queueing, Little's law, load shedding, deadlines"),
]
PROGRESS = os.path.join(ROOT, ".progress.json")


def load_progress():
    try:
        with open(PROGRESS) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {"passed": {}, "hints": {}}


def save_progress(progress):
    with open(PROGRESS, "w") as f:
        json.dump(progress, f, indent=2)


def find_lab(lab_id):
    lab_id = lab_id.zfill(2)
    for lab in LABS:
        if lab[0] == lab_id:
            return lab
    sys.exit(red(f"No lab {lab_id}. Run `python3 lab.py` to list labs."))


def lab_path(lab, *parts):
    return os.path.join(ROOT, "labs", lab[1], *parts)


def run_script(lab, script, args=(), env=None):
    return subprocess.call([sys.executable, lab_path(lab, script), *args], cwd=ROOT,
                           env=dict(os.environ, **(env or {})))


def confirm(question):
    try:
        return input(f"{question} [y/N] ").strip().lower() in ("y", "yes")
    except EOFError:
        return False


def cmd_list(_args):
    progress = load_progress()
    header("Labs: break it, investigate, fix it, then read what a senior would add")
    for lab_id, _, title, concepts in LABS:
        mark = green("✔ passed") if lab_id in progress["passed"] else dim("·")
        print(f"  {bold(lab_id)}  {title:<22} {dim(concepts):<60}  {mark}")
    done = len(progress["passed"])
    print(f"\n  {done}/{len(LABS)} passed.  Start: {bold('python3 lab.py run 01')}  and read labs/01-*/README.md")
    print(dim("  Design drills: python3 lab.py drill    Estimation practice: python3 lab.py estimate"))


def cmd_run(args):
    lab = find_lab(args[0])
    sys.exit(run_script(lab, "run.py", args[1:]))


def cmd_check(args):
    lab = find_lab(args[0])
    code = run_script(lab, "check.py")
    if code == 0 and os.environ.get("LAB_IMPL") != "solution":
        progress = load_progress()
        if lab[0] not in progress["passed"]:
            progress["passed"][lab[0]] = datetime.date.today().isoformat()
            save_progress(progress)
            print(green(f"Lab {lab[0]} marked as passed.") + f" Next: {bold(f'python3 lab.py notes {lab[0]}')}")
    sys.exit(code)


def cmd_hint(args):
    lab = find_lab(args[0])
    with open(lab_path(lab, "hints.md")) as f:
        hints = [h.strip() for h in re.split(r"^## Hint \d+\s*$", f.read(), flags=re.M) if h.strip()]
    progress = load_progress()
    shown = progress["hints"].get(lab[0], 0)
    if "--all" in args:
        upto = len(hints)
    elif shown >= len(hints):
        upto = len(hints)
        print(yellow("No more hints. Reread them all below, then check your journal for an untested assumption."))
    else:
        upto = shown + 1
    for i in range(upto):
        print(bold(f"\nHint {i + 1}/{len(hints)}"))
        print(hints[i])
    progress["hints"][lab[0]] = max(shown, upto)
    save_progress(progress)
    if upto < len(hints):
        print(dim(f"\nTry with this first. `python3 lab.py hint {lab[0]}` again for the next one."))


def cmd_journal(args):
    lab = find_lab(args[0])
    path = os.path.join(ROOT, "journal", f"{lab[0]}.md")
    if os.path.exists(path):
        print(f"Already exists: {path}")
        return
    with open(os.path.join(ROOT, "journal", "TEMPLATE.md")) as f:
        template = f.read()
    with open(path, "w") as f:
        f.write(template.replace("{{LAB}}", f"Lab {lab[0]}: {lab[2]}").replace(
            "{{DATE}}", datetime.date.today().isoformat()))
    print(f"Created {path}. Fill it in as you go, *before* fixing.")


def cmd_notes(args):
    lab = find_lab(args[0])
    if lab[0] not in load_progress()["passed"] and "--force" not in args:
        print(yellow(f"You haven't passed lab {lab[0]} yet. The notes contain the solution."))
        if not confirm("Read them anyway?"):
            return
    with open(lab_path(lab, "solution", "NOTES.md")) as f:
        print(f.read())
    print(dim(f"Reference code: labs/{lab[1]}/solution/app.py"))


def cmd_reset(args):
    lab = find_lab(args[0])
    rel = os.path.join("labs", lab[1], "app.py")
    if not confirm(f"Overwrite {rel} with the original broken version? Your changes will be lost."):
        return
    code = subprocess.call(["git", "checkout", "HEAD", "--", rel], cwd=ROOT)
    print(green("Restored.") if code == 0 else red("git checkout failed; is this a git clone?"))


def _drills():
    return sorted(glob.glob(os.path.join(ROOT, "design", "drills", "*.md")))


def cmd_drill(args):
    drills = _drills()
    if not args:
        header("System design drills (45 minutes, paper or whiteboard, no AI)")
        for i, path in enumerate(drills, 1):
            with open(path) as f:
                title = f.readline().lstrip("# ").strip()
            print(f"  {bold(str(i))}  {title}")
        print(dim("\n  python3 lab.py drill N   then, when you're done:   python3 lab.py review N"))
        print(dim("  Method: design/README.md"))
        return
    with open(drills[int(args[0]) - 1]) as f:
        print(f.read().split("<!-- REVIEW -->")[0])
    print(dim(f"When you've designed it on paper: python3 lab.py review {args[0]}"))


def cmd_review(args):
    with open(_drills()[int(args[0]) - 1]) as f:
        parts = f.read().split("<!-- REVIEW -->")
    print(parts[1] if len(parts) > 1 else "No review section.")


def cmd_estimate(_args):
    subprocess.call([sys.executable, os.path.join(ROOT, "design", "estimate.py")], cwd=ROOT)


def cmd_selftest(_args):
    """For maintainers: the original broken app.py (from git) must fail, the reference solution must pass."""
    failures = 0
    scratch = tempfile.mkdtemp(prefix="myengineer-selftest-")
    for lab in LABS:
        original = os.path.join(scratch, lab[0])
        os.makedirs(original)
        shown = subprocess.run(["git", "show", f"HEAD:labs/{lab[1]}/app.py"], cwd=ROOT, capture_output=True)
        if shown.returncode == 0:
            with open(os.path.join(original, "app.py"), "wb") as f:
                f.write(shown.stdout)
        else:
            print(yellow(f"  (no git history; testing your current labs/{lab[1]}/app.py as 'broken')"))
            shutil.copy(lab_path(lab, "app.py"), original)
        broken = subprocess.run([sys.executable, lab_path(lab, "check.py")], cwd=ROOT, capture_output=True,
                                env=dict(os.environ, LAB_IMPL=original, NO_COLOR="1"))
        solved = subprocess.run([sys.executable, lab_path(lab, "check.py")], cwd=ROOT, capture_output=True,
                                text=True, env=dict(os.environ, LAB_IMPL="solution", NO_COLOR="1"))
        ok = broken.returncode != 0 and solved.returncode == 0
        failures += not ok
        print(f"  {lab[0]} {lab[2]:<22} broken fails: {broken.returncode != 0}   solution passes: "
              f"{solved.returncode == 0}   {green('OK') if ok else red('PROBLEM')}")
        if solved.returncode != 0:
            print(dim(solved.stdout[-1500:]))
    shutil.rmtree(scratch, ignore_errors=True)
    sys.exit(1 if failures else 0)


COMMANDS = {"list": cmd_list, "run": cmd_run, "check": cmd_check, "hint": cmd_hint, "journal": cmd_journal,
            "notes": cmd_notes, "reset": cmd_reset, "drill": cmd_drill, "review": cmd_review,
            "estimate": cmd_estimate, "selftest": cmd_selftest}
NEEDS_LAB = {"run", "check", "hint", "journal", "notes", "reset", "review"}

if __name__ == "__main__":
    if sys.version_info < (3, 9):
        sys.exit("Python 3.9+ required.")
    argv = sys.argv[1:] or ["list"]
    if argv[0] in ("-h", "--help", "help"):
        print(__doc__)
    elif argv[0] not in COMMANDS:
        print(__doc__)
        sys.exit(1)
    elif argv[0] in NEEDS_LAB and len(argv) < 2:
        sys.exit(f"Usage: python3 lab.py {argv[0]} <number>")
    else:
        COMMANDS[argv[0]](argv[1:])
