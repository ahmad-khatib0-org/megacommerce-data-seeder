from urllib.parse import urlparse

import yaml

from general_utils.db import DatabasePool
from models.config import Config


def load() -> Config:
  with open("config.yaml", "r") as f:
    data = yaml.safe_load(f)
  config = Config(**data)

  try:
    parsed = urlparse(config.db.dsn)
  except Exception as e:
    raise RuntimeError("failed to parse db connection DSN", e)

  print(parsed)
  try:
    DatabasePool.initialize(host=parsed.hostname,
                            port=parsed.port,
                            dbname=parsed.path.lstrip("/"),
                            user=parsed.username,
                            password=parsed.password,
                            sslmode="disable")
    print('connected')
  except Exception as e:
    raise RuntimeError("failed to initialize database connection ", e)

  return config
