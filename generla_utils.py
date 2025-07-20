import sys
from time import time
from typing import Any

import bcrypt


def password_hash(password: str) -> tuple[str, Exception | None]:
  try:
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    return hashed.decode('utf-8'), None
  except Exception as e:
    return "", e


def fatal(*args: Any, **kwargs: Any) -> None:
  """Prints an error message and exits with status code 1"""
  print(*args, file=sys.stderr, **kwargs)
  sys.exit(1)


def time_in_milies() -> float:
  return time() * 1000
