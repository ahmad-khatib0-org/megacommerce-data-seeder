from db import DatabasePool
from generla_utils import fatal
from load import load
from seed_inventory import seed_inventory
from seed_products import seed_products
from seed_users import seed_users


def main():
  print("megacommerce data seeder")
  config = load()

  conn = DatabasePool.get_conn()
  try:
    seed_users(conn, config)
    seed_products(conn, config)
    seed_inventory(conn)

    conn.commit()
  except Exception as e:
    conn.rollback()
    fatal("error running database seeding transaction", e)


if __name__ == "__main__":
  main()
