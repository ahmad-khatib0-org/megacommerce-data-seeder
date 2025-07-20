from enum import Enum
import random

from faker import Faker
from psycopg2.extensions import connection
from ulid import ULID

from generla_utils import password_hash, time_in_milies
from models.config import Config


class UserType(str, Enum):
  SUPPLIER = "supplier"
  CUSTOMER = "customer"


class RoleId(str, Enum):
  SYSTEM_ADMIN = "system_admin"
  SYSTEM_USER = "system_user"
  SUPPLIER_ADMIN = "supplier_admin"
  SUPPLIER_VENDOR_MANAGER = "supplier_vendor_manager"
  SUPPLIER_MODERATOR = "supplier_moderator"
  CUSTOMER = "customer"


stmt = """
    INSERT INTO users(
      id, username, first_name, last_name, email, user_type, membership, 
      is_email_verified, password, roles, created_at
    )
    VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
  """


def seed_uesrs(conn: connection, cfg: Config):
  insert_users(conn, cfg.seeding.number_of_suppliers, UserType.SUPPLIER)
  insert_users(conn, cfg.seeding.number_of_customers, UserType.CUSTOMER)


def insert_users(conn: connection, count: int, user_type: UserType):
  fake = Faker()
  suppliers = [
      RoleId.SUPPLIER_ADMIN.value, RoleId.SUPPLIER_MODERATOR.value,
      RoleId.SUPPLIER_VENDOR_MANAGER.value
  ]

  password, err = password_hash("1234$rRN")
  if err:
    raise RuntimeError("failed to hash a password, insert_users", err)

  with conn.cursor() as cur:
    for _ in range(count):
      roles = random.choice(
          suppliers) if user_type == UserType.SUPPLIER else UserType.CUSTOMER.value
      try:
        args = (
            str(ULID()),
            fake.user_name(),
            fake.first_name(),
            fake.last_name(),
            fake.email(),
            user_type.value,
            "free",
            True,
            password,
            roles,
            time_in_milies(),
        )
        cur.execute(stmt, args)
      except Exception as e:
        raise RuntimeError("failed to insert a user in db", e)
