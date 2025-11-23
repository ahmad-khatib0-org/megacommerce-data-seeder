import json

from faker import Faker
from products.v1.product_pb2 import ProductOffer
from psycopg2.extensions import connection
from ulid import ULID

from generla_utils import get_time_miliseconds

fake = Faker()


def seed_inventory(conn: connection):
  with conn.cursor() as cur:
    cur.execute('SELECT id, offer FROM products')
    for row in cur:
      product_id = row[0]
      offer_json = row[1]

      offer = ProductOffer()
      if offer_json:
        offer.ParseFromString(json.dumps(offer_json).encode('utf-8'))

      for variant_id, variant_data in offer.offer.items():
        sku = variant_data.sku or fake.unique.bothify(text='SKU-#####')
        # quantity_total = fake.random_int(min=10, max=1000)
        # quantity_reserved = fake.random_int(min=0, max=quantity_total // 2)
        quantity_total = variant_data.quantity
        quantity_reserved = 0
        quantity_available = quantity_total - quantity_reserved

        cur.execute(
            """INSERT INTO inventory_items (
                  id,
                  product_id,
                  variant_id,
                  sku,
                  quantity_available,
                  quantity_reserved,
                  quantity_total,
                  location_id,
                  metadata,
                  created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""", [
                fake.unique.bothify(text=f"inv_{str(ULID())}"), product_id, variant_id, sku,
                quantity_available, quantity_reserved, quantity_total, None,
                json.dumps({
                    'source': 'seed',
                    'auto_generated': True
                }),
                int(get_time_miliseconds())
            ])
