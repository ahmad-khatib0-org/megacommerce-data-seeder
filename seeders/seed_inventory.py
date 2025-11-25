import json

from faker import Faker
from google.protobuf import json_format  # <-- Essential Protobuf import for parsing JSON
from products.v1.product_pb2 import ProductOffer  # <-- Essential Protobuf class import
from psycopg2.extensions import connection
from psycopg2 import Error as Psycopg2Error
from ulid import ULID

from general_utils.general import get_time_miliseconds
from models.app import SeedingError

fake = Faker()


def seed_inventory(conn: connection):
  """
    Seeds inventory items based on product variants defined in the 'products' table,
    using consistent error handling.
    """
  products_data = []

  ## 1. Fetch Product/Offer Data
  # Fetch all data first to free the cursor for subsequent INSERT statements.
  try:
    with conn.cursor() as cur:
      cur.execute('SELECT id, offer FROM products')
      # Fetch all rows into a list
      products_data = cur.fetchall()

      if not products_data:
        print("⚠️ Skipping seed_inventory: No products found to create inventory.")
        return

  except Psycopg2Error as e:
    raise SeedingError(f"DB SELECT failed while fetching products for inventory. Error: {e}") from e
  except Exception as e:
    raise SeedingError(f"Unexpected error while fetching products for inventory: {e}") from e

  ## 2. Process Products and Insert Inventory Items
  for product_row in products_data:
    product_id = product_row[0]
    offer_json_raw = product_row[1]

    try:
      inventory_ulid = str(ULID())

      offer = ProductOffer()

      # --- Data Parsing Risk: Parse JSON from DB into Protobuf Message ---
      if offer_json_raw:
        # json.dumps converts the psycopg2 JSON/dict object into a string for parsing
        json_format.Parse(json.dumps(offer_json_raw), offer)

      # Iterate over variants in the parsed offer
      for variant_id, variant_data in offer.offer.items():

        sku = variant_data.sku or fake.unique.bothify(text='SKU-#####')

        try:
          quantity_total = int(variant_data.quantity)
        except (ValueError, TypeError):
          quantity_total = 100
          print(
              f"⚠️ Warning: Invalid quantity for Product {product_id}, Variant {variant_id}. Defaulting to {quantity_total}."
          )

        quantity_reserved = 0
        quantity_available = quantity_total - quantity_reserved

        # --- DB Insertion ---
        # Use a new cursor or the same one, but ensure it's not being iterated over
        with conn.cursor() as cur:
          cur.execute(
              """INSERT INTO inventory_items (
                            id, product_id, variant_id, sku, quantity_available, 
                            quantity_reserved, quantity_total, location_id, metadata, created_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""", [
                  str(ULID()), product_id, variant_id, sku, quantity_available, quantity_reserved,
                  quantity_total, None,
                  json.dumps({
                      'source': 'seed',
                      'auto_generated': True
                  }),
                  get_time_miliseconds()
              ])

    except Psycopg2Error as e:
      # Specific error for DB insertion failure
      print(
          f"❌ DB INSERT failed for inventory_items (ID: {inventory_ulid}, Product: {product_id}). Error: {e}"
      )
      continue  # Log error and move to next product
    except Exception as e:
      # Catch errors during JSON/Protobuf parsing, or data calculation
      print(f"❌ DATA PROCESSING failed for Product {product_id}. Error: {e}")
      continue  # Log error and move to next product

  print(f" Successfully seeded inventory for {len(products_data)} products.")
