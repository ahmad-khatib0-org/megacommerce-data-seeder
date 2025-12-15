from faker import Faker
from psycopg2 import Error as Psycopg2Error
from psycopg2.extensions import connection, cursor
from ulid import ULID

from general_utils.general import time_in_milies
from models.app import SeedingError
from models.config import Config
from seeders.orders import get_user_ids

fake = Faker()


def seed_payment_methods(conn: connection, cfg: Config):
  """
  Seeds payment methods for users by creating card payment records.
  Each customer gets between 1-3 payment methods with one marked as default.
  """
  with conn.cursor() as cur:
    try:
      user_ids = get_user_ids(cur, cfg)
      if not user_ids:
        print(f"⚠️ Skipping seed_payment_methods: No users found.")
        return
    except Exception as e:
      print(f"❌ FATAL ERROR: Could not fetch users. Error: {e}")
      return

    payment_types = ['card', 'paypal', 'apple', 'google']
    cards_data = [
        {
            'last_four': '4242',
            'expiry': '12/25'
        },
        {
            'last_four': '5555',
            'expiry': '08/26'
        },
        {
            'last_four': '3782',
            'expiry': '11/24'
        },
        {
            'last_four': '6011',
            'expiry': '03/27'
        },
    ]

    for user_id in user_ids:
      try:
        # Generate 1-3 payment methods per user
        num_methods = fake.random_int(min=1, max=3)
        is_first = True

        for i in range(num_methods):
          payment_type = payment_types[i % len(payment_types)]

          if payment_type == 'card':
            card_data = cards_data[i % len(cards_data)]
            name = f"Card ending in {card_data['last_four']}"
            last_four = card_data['last_four']
            expiry_date = card_data['expiry']
            # Mock token (in production, this would be a tokenized/encrypted value from payment processor)
            token = f"tok_card_{fake.random_int(100000, 999999)}"
          elif payment_type == 'paypal':
            name = f"{fake.first_name()}'s PayPal"
            last_four = None
            expiry_date = None
            token = f"tok_paypal_{fake.random_int(100000, 999999)}"
          elif payment_type == 'apple':
            name = "Apple Pay"
            last_four = None
            expiry_date = None
            token = f"tok_apple_{fake.random_int(100000, 999999)}"
          else:  # google
            name = "Google Pay"
            last_four = None
            expiry_date = None
            token = f"tok_google_{fake.random_int(100000, 999999)}"

          insert_payment_method(cur, str(ULID()), user_id, payment_type, name, last_four,
                                expiry_date, token, is_first)
          is_first = False

      except Exception as e:
        print(f"❌ ERROR processing payment methods for User ID {user_id}. Details: {e}")
        continue

    print(f"✅ Successfully seeded payment methods for {len(user_ids)} users")


def insert_payment_method(
    cur: cursor,
    id: str,
    user_id: str,
    type_: str,
    name: str,
    last_four: str | None,
    expiry_date: str | None,
    token: str,
    is_default: bool,
):
  stmt = """
    INSERT INTO payment_methods (
      id, user_id, type, name, last_four, expiry_date, token, is_default, created_at
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
  """
  try:
    cur.execute(
        stmt,
        [id, user_id, type_, name, last_four, expiry_date, token, is_default,
         time_in_milies()])
  except Psycopg2Error as e:
    raise SeedingError(
        f"DB INSERT failed for payment_methods. User ID: {user_id}, Type: {type_}, Error: {e}"
    ) from e
