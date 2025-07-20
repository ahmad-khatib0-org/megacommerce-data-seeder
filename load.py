import yaml
from urllib.parse import urlparse

from models.config import Config
from db import DatabasePool


def load() -> Config:
  with open("config.yaml", "r") as f:
    data = yaml.safe_load(f)
  config = Config(**data)

  try:
    parsed = urlparse(config.db.dsn)
  except Exception as e:
    raise RuntimeError("failed to parse db connection DSN", e)

  try:
    DatabasePool.initialize(
        host=parsed.hostname,
        dbname=parsed.path.lstrip("/"),
        user=parsed.username,
        password=parsed.password,
    )
  except Exception as e:
    raise RuntimeError("failed to initialize database connection ", e)

  return config
