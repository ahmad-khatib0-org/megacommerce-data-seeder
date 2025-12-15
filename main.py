from general_utils.db import DatabasePool
from general_utils.general import fatal
from seeders.load import load
from seeders.seed_hero_products import seed_hero_products
from seeders.seed_inventory import seed_inventory
from seeders.seed_orders import seed_orders
from seeders.seed_payment_methods import seed_payment_methods
from seeders.seed_products import seed_products
from seeders.seed_users import seed_users


def main():
  print("megacommerce data seeder")

  config = load()
  conn = None

  try:
    conn = DatabasePool.get_conn()
    conn.autocommit = False

    # seed_users(conn, config)
    # seed_products(conn, config)
    # seed_inventory(conn)
    # seed_orders(conn, config)
    # seed_hero_products(conn)
    seed_payment_methods(conn, config)

    # All operations successful, commit the transaction
    conn.commit()
    print("Successfully committed all seeding changes.")

  except Exception as e:
    if conn:
      conn.rollback()
    fatal("error running database seeding transaction", e)

  finally:
    if conn:
      DatabasePool.release_conn(conn)


if __name__ == "__main__":
  main()
