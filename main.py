from db import DatabasePool
from generla_utils import fatal
from load import load
from seed_users import seed_uesrs


def main():
  print("megacommerce data seeder")
  config = load()

  conn = DatabasePool.get_conn()
  try:
    seed_uesrs(conn, config)

    conn.commit()
  except Exception as e:
    conn.rollback()
    fatal("error running database seeding transaction", e)


if __name__ == "__main__":
  main()
