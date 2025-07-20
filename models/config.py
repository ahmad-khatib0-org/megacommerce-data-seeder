from pydantic import BaseModel


class ConfigDB(BaseModel):
  dsn: str


class ConfigSeeding(BaseModel):
  number_of_suppliers: int
  number_of_customers: int
  number_of_products_per_supplier: int
  number_of_suppliers_have_products: int


class Config(BaseModel):
  db: ConfigDB
  seeding: ConfigSeeding
