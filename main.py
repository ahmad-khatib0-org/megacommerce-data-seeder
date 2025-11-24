from db import DatabasePool
from general_utils import fatal
from load import load
from seed_inventory import seed_inventory
from seed_orders import seed_orders
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
    seed_orders(conn, config)

    conn.commit()
  except Exception as e:
    conn.rollback()
    fatal("error running database seeding transaction", e)


if __name__ == "__main__":
  main()
