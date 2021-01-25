# -*- coding: utf-8 -*-
"""
Simple convenience wrapper for SQLite. Example usage:

db.init(":memory:", ["CREATE TABLE test (id INTEGER PRIMARY KEY, val TEXT)"])
for i in range(5): db.insert("test", [("val", "venividivici")])
db.insert("test", val=None)
db.fetchone("test", val=None, limit=[0, 3])
db.update("test", values=[("val", "arrivederci")], val=None)
db.update("test", values=[("val", "ciao")], where=[("val", ("IS NOT", None))])
db.fetch("test", order=["val", ("id", "DESC")], limit=[0, 4])
db.fetch("test", id=("IN", [1, 2, 3]))
db.delete("test", val="something")
db.execute("DROP TABLE test")

@author      Erki Suurjaak
@created     05.03.2014
@modified    25.01.2021
"""
import os
import re
import sqlite3


def fetch(table, cols="*", where=(), group="", order=(), limit=(), **kwargs):
    """Convenience wrapper for database SELECT and fetch all."""
    return select(table, cols, where, group, order, limit, **kwargs).fetchall()


def fetchone(table, cols="*", where=(), group="", order=(), limit=(), **kwargs):
    """Convenience wrapper for database SELECT and fetch one."""
    return select(table, cols, where, group, order, limit, **kwargs).fetchone()


def insert(table, values=(), **kwargs):
    """Convenience wrapper for database INSERT."""
    values = list(values.items() if isinstance(values, dict) else values)
    values += kwargs.items()
    sql, args = makeSQL("INSERT", table, values=values)
    return execute(sql, args).lastrowid


def select(table, cols="*", where=(), group="", order=(), limit=(), **kwargs):
    """Convenience wrapper for database SELECT."""
    where = list(where.items() if isinstance(where, dict) else where)
    where += kwargs.items()
    sql, args = makeSQL("SELECT", table, cols, where, group, order, limit)
    return execute(sql, args)


def update(table, values, where=(), **kwargs):
    """Convenience wrapper for database UPDATE."""
    where = list(where.items() if isinstance(where, dict) else where)
    where += kwargs.items()
    sql, args = makeSQL("UPDATE", table, values=values, where=where)
    return execute(sql, args).rowcount


def delete(table, where=(), **kwargs):
    """Convenience wrapper for database DELETE."""
    where = list(where.items() if isinstance(where, dict) else where)
    where += kwargs.items()
    sql, args = makeSQL("DELETE", table, where=where)
    return execute(sql, args).rowcount


def execute(sql, args=None):
    """Executes the SQL and returns sqlite3.Cursor."""
    return get_cursor().execute(sql, args or {})


def get_cursor():
    """Returns a cursor to the default database."""
    config = get_config()
    return make_cursor(config["path"], config["statements"])


def make_cursor(path, init_statements=(), _connectioncache={}):
    """Returns a cursor to the database, making new connection if not cached."""
    connection = _connectioncache.get(path)
    if not connection:
        is_new = not os.path.exists(path) or not os.path.getsize(path)
        try: is_new and os.makedirs(os.path.dirname(path))
        except OSError: pass
        connection = sqlite3.connect(path, isolation_level=None,
            check_same_thread=False, detect_types=sqlite3.PARSE_DECLTYPES)
        for x in init_statements or (): connection.execute(x)
        try: is_new and ":memory:" not in path.lower() and os.chmod(path, 0707)
        except OSError: pass
        connection.row_factory = lambda cur, row: dict(sqlite3.Row(cur, row))
        _connectioncache[path] = connection
    return connection.cursor()


def makeSQL(action, table, cols="*", where=(), group="", order=(), limit=(), values=()):
    """Returns (SQL statement string, parameter dict)."""
    cols   =    cols if isinstance(cols,  basestring) else ", ".join(cols)
    group  =   group if isinstance(group, basestring) else ", ".join(group)
    order  = [order] if isinstance(order, basestring) else order
    limit  = [limit] if isinstance(limit, (basestring, int)) else limit
    values = values if not isinstance(values, dict) else values.items()
    sql = "SELECT %s FROM %s" % (cols, table) if "SELECT" == action else ""
    sql = "DELETE FROM %s"    % (table)       if "DELETE" == action else sql
    sql = "INSERT INTO %s"    % (table)       if "INSERT" == action else sql
    sql = "UPDATE %s"         % (table)       if "UPDATE" == action else sql
    args = {}
    if "INSERT" == action:
        args.update(values)
        cols, vals = (", ".join(x + k for k, v in values) for x in ("", ":"))
        sql += " (%s) VALUES (%s)" % (cols, vals)
    if "UPDATE" == action:
        sql += " SET "
        for i, (col, val) in enumerate(values):
            sql += (", " if i else "") + "%s = :%sU%s" % (col, col, i)
            args["%sU%s" % (col, i)] = val
    if where:
        sql += " WHERE "
        for i, (col, val) in enumerate(where):
            key = "%sW%s" % (re.sub("\\W", "_", col), i)
            dbval = val[1] if isinstance(val, (list, tuple)) else val
            op = "IS" if dbval == val else val[0]

            if op in ("IN", "NOT IN"):
                keys = ["%s_%s" % (col, j) for j in range(len(val[1]))]
                args.update(zip(keys, val[1]))
                sql += (" AND " if i else "") + "%s %s (%s)" % (
                        col, op, ", ".join(":" + x for x in keys))
            else:
                args[key] = dbval
                op = "=" if dbval is not None and "IS" == op else op
                sql += (" AND " if i else "") + "%s %s :%s" % (col, op, key)
    if group:
        sql += " GROUP BY " + group
    if order:
        sql += " ORDER BY "
        for i, col in enumerate(order):
            name = col[0] if isinstance(col, (list, tuple)) else col
            direction = "" if name == col else " " + col[1]
            sql += (", " if i else "") + name + direction
    if limit:
        sql += " LIMIT %s" % (", ".join(map(str, limit)))
    return sql, args


def get_config(config={}): return config


def init(path, init_statements=None):
    config = get_config()
    config.update(path=path, statements=init_statements)
    make_cursor(config["path"], config["statements"])


def close():
    try: get_cursor().connection.close()
    except Exception: pass
