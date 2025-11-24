import threading

from psycopg2 import pool
from psycopg2.extensions import connection


class DatabasePool:
  _lock = threading.Lock()
  _pool = None
  _initialized = False

  @classmethod
  def initialize(cls, minconn=1, maxconn=10, **db_params):
    with cls._lock:
      if cls._pool is None:
        cls._pool = pool.ThreadedConnectionPool(minconn, maxconn, **db_params)
        cls._initialized = True
      elif not cls._initialized:
        raise RuntimeError("DatabasePool is already initialized.")

  @classmethod
  def get_conn(cls) -> connection:
    if cls._pool is None:
      raise RuntimeError("Database is not initialized")
    return cls._pool.getconn()

  @classmethod
  def release_conn(cls, conn: connection):
    if cls._pool:
      cls._pool.putconn(conn)

  @classmethod
  def close_all(cls):
    if cls._pool:
      cls._pool.closeall()
      cls._initialized = False
