from pydantic import BaseModel


class ConfigDB(BaseModel):
  dsn: str


class ConfigSeeding(BaseModel):
  number_of_suppliers: int
  number_of_customers: int
  number_of_products_per_supplier: int
  number_of_suppliers_have_products: int
  number_of_customers_have_orders: int


class ConfigMinio(BaseModel):
  amazon_s3_endpoint: str
  amazon_s3_bucket: str
  amazon_s3_access_key_id: str
  amazon_s3_secret_access_key: str


class Config(BaseModel):
  db: ConfigDB
  seeding: ConfigSeeding
  minio: ConfigMinio
