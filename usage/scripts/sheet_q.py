#!/usr/bin/env python3
"""Answer one question about a spreadsheet with SQL; print only the answer.

usage: sheet_q.py <file.csv|.tsv|.json|.parquet> "select ... from t ..." [--limit 50]
The file is table `t`. Uses DuckDB when installed, else sqlite3 (CSV/TSV only).
Tip: first run `sheet_q.py file.csv schema` to see the columns.
"""
import argparse
import csv
import sqlite3
import sys


def duck(path, sql, limit):
    import duckdb  # type: ignore

    con = duckdb.connect()
    con.execute(f"create view t as select * from '{path.replace(chr(39), '')}'")
    if sql.strip().lower() == "schema":
        return con.execute("describe t").fetchall(), ["column", "type", "null", "key", "default", "extra"]
    cur = con.execute(sql)
    return cur.fetchmany(limit), [d[0] for d in cur.description]


def lite(path, sql, limit):
    delim = "\t" if path.endswith(".tsv") else ","
    with open(path, newline="", errors="replace") as f:
        r = csv.reader(f, delimiter=delim)
        head = next(r)
        cols = [h.strip() or f"c{i}" for i, h in enumerate(head)]
        con = sqlite3.connect(":memory:")
        con.execute("create table t (%s)" % ",".join(f'"{c}"' for c in cols))
        con.executemany("insert into t values (%s)" % ",".join("?" * len(cols)),
                        (row[: len(cols)] + [None] * (len(cols) - len(row)) for row in r))
    if sql.strip().lower() == "schema":
        return [(c,) for c in cols], ["column"]
    cur = con.execute(sql)
    return cur.fetchmany(limit), [d[0] for d in cur.description]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("sql")
    ap.add_argument("--limit", type=int, default=50)
    a = ap.parse_args()
    try:
        rows, cols = duck(a.path, a.sql, a.limit)
    except ImportError:
        rows, cols = lite(a.path, a.sql, a.limit)
    w = csv.writer(sys.stdout)
    w.writerow(cols)
    w.writerows(rows)


if __name__ == "__main__":
    main()
