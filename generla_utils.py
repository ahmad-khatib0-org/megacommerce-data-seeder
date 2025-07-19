from time import time
import bcrypt


def password_hash(password: str) -> tuple[str, Exception | None]:
  try:
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    return hashed.decode('utf-8'), None
  except Exception as e:
    return "", e


def time_in_milies() -> float:
  return time() * 1000
