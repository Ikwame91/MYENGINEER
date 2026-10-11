"""A SQL playground on the lab's database: run any query and see its rows, its time, and its plan.

    python3 lab.py play 01

Nothing you do here changes app.py. Indexes you create here are wiped the next time you
run the lab, so experiment freely.
"""

import os
import sqlite3
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)

from labkit import bold, dim, green, red, yellow  # noqa: E402
import data  # noqa: E402

HELP = f"""{bold('Type a SQL statement and press Enter.')} For every SELECT you'll see the rows (first 5),
how long it took, and the PLAN: how SQLite decided to find the rows.

  {bold('Try these, in order:')}
    SELECT * FROM users LIMIT 3;
    SELECT * FROM orders LIMIT 3;
    SELECT * FROM users WHERE name = 'user_04242';
    CREATE INDEX users_name ON users (name);
    SELECT * FROM users WHERE name = 'user_04242';

  {dim('.tables  list tables     .indexes  list indexes you created     .help  this text     .quit  leave')}
"""


def show_plan(conn, sql):
    print(bold("  plan:"))
    for _, parent, _, detail in conn.execute("EXPLAIN QUERY PLAN " + sql):
        line = f"    {'  ' if parent else ''}{detail}"
        if detail.startswith("SCAN"):
            print(red(line) + dim("   <- reads EVERY row of the table"))
        elif "TEMP B-TREE" in detail:
            print(yellow(line) + dim("   <- has to sort the rows itself"))
        elif "USING" in detail and "INDEX" in detail:
            print(green(line) + dim("   <- jumps straight to the rows via an index"))
        else:
            print(line)


def main():
    conn = data.connect()   # fresh: no indexes
    print(HELP)
    buffer = ""
    while True:
        try:
            line = input("sql> " if not buffer else "...> ")
        except (EOFError, KeyboardInterrupt):
            print()
            return
        cmd = line.strip()
        if not buffer and cmd in (".quit", ".exit", "quit", "exit"):
            return
        if not buffer and cmd == ".help":
            print(HELP)
            continue
        if not buffer and cmd == ".tables":
            for (sql,) in conn.execute("SELECT sql FROM sqlite_master WHERE type = 'table'"):
                print(sql)
            continue
        if not buffer and cmd == ".indexes":
            rows = conn.execute("SELECT sql FROM sqlite_master WHERE type = 'index' AND sql IS NOT NULL").fetchall()
            print("\n".join(r[0] for r in rows) if rows else dim("(no indexes yet)"))
            continue
        buffer += line + "\n"
        if not cmd.endswith(";"):
            continue          # keep reading until the statement ends with ;
        sql, buffer = buffer.strip().rstrip(";"), ""
        try:
            start = time.perf_counter()
            cursor = conn.execute(sql)
            rows = cursor.fetchall()
            elapsed = time.perf_counter() - start
            conn.commit()
        except sqlite3.Error as e:
            print(red(f"  error: {e}"))
            continue
        if cursor.description:
            print(dim("  " + " | ".join(c[0] for c in cursor.description)))
            for row in rows[:5]:
                print("  " + " | ".join(str(v) for v in row))
            if len(rows) > 5:
                print(dim(f"  ... {len(rows) - 5:,} more rows"))
        print(bold(f"  took {elapsed * 1000:.2f}ms") + dim(f"  ({len(rows):,} rows)"))
        if sql.lstrip().upper().startswith("SELECT"):
            show_plan(conn, sql)


if __name__ == "__main__":
    main()
