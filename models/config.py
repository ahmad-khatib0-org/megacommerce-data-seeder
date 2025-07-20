from pydantic import BaseModel


class ConfigDB(BaseModel):
  dsn: str


class ConfigSeeding(BaseModel):
  number_of_suppliers: int
  number_of_customers: int


class Config(BaseModel):
  db: ConfigDB
  seeding: ConfigSeeding
