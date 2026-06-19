from __future__ import annotations


def set_search_path(cur) -> None:
    cur.execute("SET search_path TO insight,public;")


def table_columns(cur, table_name: str) -> set[str]:
    set_search_path(cur)
    cur.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema='insight' AND table_name=%s
        ORDER BY ordinal_position
        """,
        (table_name,),
    )
    return {row[0] for row in cur.fetchall()}
