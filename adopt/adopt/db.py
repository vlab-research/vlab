# TODO: deprecate this in favor of using InferenceData abstraction
# and getting this data from an API + connector plugin
import re

import psycopg


def _connect(cnf):
    return psycopg.connect(cnf)


def query(cnf, q, vals=(), as_dict=False):
    with _connect(cnf) as conn:
        with conn.cursor() as cur:
            cur.execute(q, vals)

            if as_dict:
                column_names = [desc[0] for desc in cur.description]
                for record in cur:
                    yield dict(zip(column_names, record))
            else:
                for record in cur:
                    yield record


def execute(cnf, q, vals=()):
    with _connect(cnf) as conn:
        with conn.cursor() as cur:
            cur.execute(q, vals)


parens = re.compile(r"\((.+)\)")


def manyify(q, vals):
    cols = re.search(parens, q)[1]
    cols = [c.strip() for c in cols.split(",")]

    placeholders = "(" + ", ".join(["%s" for _ in cols]) + ")"
    placeholders = ", ".join([placeholders for _ in vals])

    vals = [y for x in vals for y in x]
    q = q + " values " + placeholders + " "
    return q, vals


def execute_many(cnf, q, vals_list):
    with _connect(cnf) as conn:
        with conn.cursor() as cur:
            for vals in vals_list:
                cur.execute(q, vals)


def copy(cnf, table, vals):
    print(table)
    with _connect(cnf) as conn:
        with conn.cursor() as cur:
            with cur.copy(f"COPY {table} FROM STDIN") as copy:
                for record in vals:
                    copy.write_row(record)
