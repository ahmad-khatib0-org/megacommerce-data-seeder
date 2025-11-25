import json
from faker import Faker
from google.protobuf import json_format
from products.v1.product_pb2 import ProductOffer
from psycopg2.extensions import cursor
from models.app import SeedingError
from models.config import Config

fake = Faker()


class ProductIDAndOffer:
  def __init__(self, id: str, title: str, offer: ProductOffer):
    self.id = id
    self.title = title
    self.offer = offer


def get_user_ids(cur: cursor, cfg: Config) -> list[str]:
  """
    Fetches a list of customer IDs from the database.
    Raises SeedingError on database operation failure.
    """
  stmt = "SELECT id FROM users WHERE user_type = %s AND roles && %s ORDER BY created_at LIMIT %s"
  try:
    # Execute the SQL statement
    cur.execute(stmt, (
        'customer',
        ['customer'],
        cfg.seeding.number_of_customers_have_orders,
    ))

    rows = cur.fetchall()
    customer_ids: list[str] = []
    for row in rows:
      customer_ids.append(row[0])

    return customer_ids
  except Exception as e:
    # Catch any exception (like psycopg2.Error) and raise a SeedingError
    message = f"Failed to retrieve user IDs. Database error: {e}"
    raise SeedingError(message) from e


def get_products(cur: cursor) -> list[ProductIDAndOffer]:
  """
    Fetches products and parses their offers from the database.
    Raises SeedingError on database operation or JSON parsing failure.
    """
  stmt = "SELECT id, offer, title FROM products"
  try:
    # Database operation
    cur.execute(stmt)
    rows = cur.fetchall()
    products = []

    for row in rows:
      product_id = row[0]
      offer_data = row[1]  # This is now a Python dict (from jsonb)
      offer = ProductOffer()

      # Data parsing operation
      if offer_data:
        try:
          offer_json_string = json.dumps(offer_data)

          json_format.Parse(offer_json_string, offer)
        except Exception as parse_e:
          # Catch protobuf/json_format parsing errors
          message = f"Failed to parse ProductOffer for product ID {product_id}. Error: {parse_e}"
          raise SeedingError(message) from parse_e

      products.append(ProductIDAndOffer(id=product_id, title=row[2], offer=offer))

    return products
  except SeedingError:
    # Re-raise the SeedingError from inside the loop
    raise
  except Exception as e:
    # Catch any exception (like psycopg2.Error) and raise a SeedingError
    message = f"Failed to retrieve products. Database error: {e}"
    raise SeedingError(message) from e


def create_successful_payment(amount_cents: int, currency: str):
  return {
      'payment_provider':
      'stripe',
      'payment_transaction_id':
      fake.unique.bothify(text='pi_?????????????????????????'),
      'payment_status':
      'CAPTURED',
      'payment_provider_response':
      json.dumps({
          'status': 'succeeded',
          'id': f'pi_{fake.unique.uuid4()}',
          'amount': amount_cents,
          'currency': currency,
          'charges': {
              'data': [{
                  'id': f'ch_{fake.unique.uuid4()}',
                  'status': 'succeeded'
              }]
          }
      }),
      'payment_fee_cents':
      int(amount_cents * 0.029) + 30  # 2.9% + 30 cents
  }


def create_failed_payment(amount_cents: int, currency: str):
  return {
      'payment_provider':
      'stripe',
      'payment_transaction_id':
      fake.unique.bothify(text='pi_?????????????????????????'),
      'payment_status':
      'FAILED',
      'payment_provider_response':
      json.dumps({
          'status': 'failed',
          'id': f'pi_{fake.unique.uuid4()}',
          'amount': amount_cents,
          'currency': currency,
          'error': {
              'type': 'card_error',
              'message': 'Your card was declined.'
          }
      }),
      'payment_fee_cents':
      0  # No fee for failed payments
  }
