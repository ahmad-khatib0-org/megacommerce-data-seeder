import json

from faker import Faker
from google.protobuf import json_format
from products.v1.product_pb2 import ProductOffer
from psycopg2.extensions import cursor

from models.config import Config

fake = Faker()


class ProductIDAndOffer:
  def __init__(self, id: str, title: str, offer: ProductOffer):
    self.id = id
    self.title = title
    self.offer = offer


def get_user_ids(cur: cursor, cfg: Config) -> list[str]:
  stmt = "SELECT id FROM users WHERE user_type = %s AND roles && %s ORDER BY created_at LIMIT %s"
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


def get_products(cur: cursor) -> list[ProductIDAndOffer]:
  stmt = "SELECT id, offer, title FROM products"
  cur.execute(stmt)

  rows = cur.fetchall()
  products = []
  for row in rows:
    product_id = row[0]
    offer_json = row[1]
    offer = ProductOffer()
    if offer_json:
      json_format.Parse(offer_json, offer)

    products.append(ProductIDAndOffer(id=product_id, title=row[2], offer=offer))

  return products


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
