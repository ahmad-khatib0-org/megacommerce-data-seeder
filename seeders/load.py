import os
from urllib.parse import urlparse

import yaml

from general_utils.db import DatabasePool
from models.config import Config


def load() -> Config:
  env = os.getenv('ENV', 'local')

  if env not in ['dev', 'local', 'production']:
    raise ValueError(f"Invalid environment: {env}. Must be one of: 'dev', 'local', 'production'")

  file_name = f"config.{env}.yaml"

  if os.path.exists(file_name):
    config_file = file_name
  else:
    config_file = "config.local.yaml"
    print(
        f"Warning: Environment-specific config '{file_name}' not found, using default '{config_file}'"
    )

  with open(config_file, "r") as f:
    data = yaml.safe_load(f)

  config = Config(**data)

  try:
    parsed = urlparse(config.db.dsn)
  except Exception as e:
    raise RuntimeError("failed to parse db connection DSN", e)

  try:
    DatabasePool.initialize(host=parsed.hostname,
                            port=parsed.port,
                            dbname=parsed.path.lstrip("/"),
                            user=parsed.username,
                            password=parsed.password,
                            sslmode="disable")
    print('connected to database')
  except Exception as e:
    raise RuntimeError("failed to initialize database connection ", e)

  return config
