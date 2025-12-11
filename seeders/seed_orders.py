import json
import time
from random import choice, randint
from typing import Any, Dict

from faker import Faker
from orders.v1.order_line_items_pb2 import OrderLineItem
from products.v1.product_pb2 import ProductOffer
from psycopg2 import Error as Psycopg2Error
from psycopg2.extensions import connection, cursor
from ulid import ULID

from general_utils.general import get_time_miliseconds
from models.app import SeedingError
from models.config import Config
from seeders.orders import create_successful_payment, get_products, get_user_ids

fake = Faker()


def seed_orders(con: connection, cfg: Config):
  """
    Seeds orders by creating all related records for each customer, with robust error handling.
    """
  with con.cursor() as cur:
    try:
      user_ids = get_user_ids(cur, cfg)
      products = get_products(cur)
      if not user_ids or not products:
        print(f"⚠️ Skipping seed_orders: Found {len(user_ids)} users and {len(products)} products.")
        return
    except Exception as e:
      print(f"❌ FATAL ERROR: Could not fetch initial data (users/products). Error: {e}")
      return

    product_idx = 0
    for user_id in user_ids:
      order_id = str(ULID())
      try:
        # Logic to cycle through products
        if (product_idx + 1) >= len(products):
          product_idx = 0
        else:
          product_idx += 1

        # Gather key data
        now_ms = get_time_miliseconds()
        offer = products[product_idx].offer
        product_id = products[product_idx].id
        product_title = products[product_idx].title

        # --- Step 1: Insert Idempotency Key ---
        idempotency_key = 'idem_' + str(ULID())
        insert_idempotency_key(cur, user_id, 'IN_PROGRESS', idempotency_key)

        # --- Step 2: Get Line Items
        items = get_order_line_items(cur, offer, product_id, product_title, order_id, now_ms)
        order_line_items: list[Dict[str, Any]] = items['items']
        subtotal_cents = items['subtotal_cents']
        total_discount_cents = items['total_discount_cents']
        total_tax_cents = items['total_tax_cents']
        total_shipping_cents = items['total_shipping_cents']
        total_cents = subtotal_cents - total_discount_cents + total_tax_cents + total_shipping_cents

        # --- Step 3: Insert Order ---
        insert_order(cur, order_id, user_id, total_cents, subtotal_cents, total_shipping_cents,
                     total_tax_cents, total_discount_cents, total_cents)

        # --- Step 4: Insert Inventory Reservation ---
        reservation_id = str(ULID())
        reservation_token = f"res_{str(ULID())}"
        insert_inventory_reservation(cur, reservation_id, reservation_token, order_id)

        # --- Step 5: Insert Order Line Items ---
        for order_line_item in order_line_items:
          inventory_id = order_line_item['inventory_item_id']
          item: OrderLineItem = order_line_item['order_line_item']
          insert_order_line_item(cur, item.id, order_id, item.product_id, item.variant_id, item.sku,
                                 item.title, item.quantity, item.unit_price_cents,
                                 item.list_price_cents, item.sale_price_cents, item.discount_cents,
                                 item.tax_cents, item.total_cents, item.shipping_cents)
          insert_inventory_reservation_item(cur, reservation_id, inventory_id, item.quantity)

        # --- Step 6: Insert Order Events (CREATED) ---
        event_payload = json.dumps({
            'reservation_token': reservation_token,
            'subtotal_cents': subtotal_cents,
            'total_cents': total_cents,
        })
        insert_order_event(cur, order_id, 'CREATED', event_payload)

        # --- Step 7: Update Order Status/Payment ---
        update_order_payment_succeeded(cur, 'CAPTURED', 'CONFIRMED', order_id)

        # --- Step 8: Update Idempotency Key Status ---
        update_order_idempotency_key(cur, order_id, 'CONFIRMED', idempotency_key)

        # --- Step 9: Insert Order Events (PAYMENT_CAPTURED) ---
        event_payload = json.dumps({
            'provider': 'stripe',
        })
        insert_order_event(cur, order_id, 'PAYMENT_CAPTURED', event_payload)

      except Exception as e:
        # Log the error and move to the next iteration
        print(f"❌ ERROR processing Order ID {order_id} for User ID {user_id}. Details: {e}")
        # If this is inside a larger transaction (which is typical for seeding),
        # the transaction will eventually fail unless you explicitly handle savepoints/rollbacks.
        continue


def insert_idempotency_key(
    cur: cursor,
    user_id: str,
    status: str,
    idempotency_key: str,
):
  try:
    cur.execute(
        """INSERT INTO order_idempotency_keys (
                id, idempotency_key, user_id, order_id, status, created_at, updated_at, expires_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""", [
            str(ULID()), idempotency_key, user_id, None, status,
            get_time_miliseconds(), None,
            get_time_miliseconds() + (60 * 1000)
        ])
  except Psycopg2Error as e:
    raise SeedingError(f"DB INSERT failed for order_idempotency_keys. Error: {e}") from e


def update_order_idempotency_key(cur: cursor, order_id: str, status: str, idempotency_key: str):
  stmt = """
        UPDATE order_idempotency_keys SET order_id = %s, status = %s, updated_at = %s WHERE idempotency_key = %s
    """
  try:
    cur.execute(stmt, [order_id, status, get_time_miliseconds(), idempotency_key])
  except Psycopg2Error as e:
    raise SeedingError(
        f"DB UPDATE failed for order_idempotency_keys. Token: {idempotency_key}, Error: {e}") from e


def insert_inventory_reservation(cur: cursor, id: str, token: str, order_id: str):
  try:
    cur.execute(
        """INSERT INTO inventory_reservations (id, reservation_token, order_id, status, expires_at, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)""", [
            id, token, order_id, 'RESERVED',
            get_time_miliseconds() + (60 * 1000),
            get_time_miliseconds(), None
        ])
  except Psycopg2Error as e:
    raise SeedingError(
        f"DB INSERT failed for inventory_reservations. Order ID: {order_id}, Error: {e}") from e


def insert_order(cur: cursor, id: str, user_id: str, payment_amount: int, subtotal_cents: int,
                 shipping_cents: int, tax_cents: int, discount_cents: int, total_cents: int):

  currency = fake.currency_code()
  try:
    payment = create_successful_payment(payment_amount, currency)
  except Exception as e:
    raise SeedingError(f"Failed to create payment object for Order ID {id}. Error: {e}") from e

  try:
    cur.execute(
        """INSERT INTO orders (
                id, user_id, currency_code, subtotal_cents, shipping_cents, tax_cents, discount_cents,
                total_cents, payment_provider, payment_transaction_id, payment_status, 
                payment_provider_response, payment_fee_cents, inventory_reservation_status, 
                product_source, shipping_address, billing_address, metadata, status, created_at, 
                updated_at, deleted_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        [
            id, user_id, currency, subtotal_cents, shipping_cents, tax_cents, discount_cents,
            total_cents, payment['payment_provider'], payment['payment_transaction_id'],
            payment['payment_status'], payment['payment_provider_response'],
            payment['payment_fee_cents'], 'RESERVED', 'product-service-v1.0.0',
            json.dumps({'address': fake.address()}),
            json.dumps({'address': fake.address()}),
            json.dumps({'source': 'seed_data'}), 'CREATED',
            int(get_time_miliseconds()), None, None
        ])
  except Psycopg2Error as e:
    raise SeedingError(f"DB INSERT failed for orders. Order ID: {id}, Error: {e}") from e


def update_order_payment_succeeded(cur: cursor, payment_status: str, status: str, order_id: str):
  stmt = 'UPDATE orders SET payment_status = %s, status = %s, updated_at = %s WHERE id = %s'
  try:
    cur.execute(stmt, [payment_status, status, get_time_miliseconds(), order_id])
  except Psycopg2Error as e:
    raise SeedingError(
        f"DB UPDATE failed for orders (payment status). Order ID: {order_id}, Error: {e}") from e


def insert_order_line_item(cur: cursor, id: str, order_id: str, product_id: str, variant_id: str,
                           sku: str, title: str, quantity: int, unit_price_cents: int,
                           list_price_cents: int | None, sale_price_cents: int | None,
                           discount_cents: int, tax_cents: int, total_cents: int,
                           shipping_cents: int):
  try:
    cur.execute(
        """INSERT INTO order_line_items (
                id, order_id, product_id, variant_id, sku, title, attributes, quantity, unit_price_cents,
                list_price_cents, sale_price_cents, discount_cents, tax_cents, total_cents, 
                applied_offer_ids, product_snapshot, status, shipping_cents, created_at, updated_at, estimated_delivery_date
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        [
            id, order_id, product_id, variant_id, sku, title,
            json.dumps({}), quantity, unit_price_cents, list_price_cents, sale_price_cents,
            discount_cents, tax_cents, total_cents, [], None, 'CREATED', shipping_cents,
            get_time_miliseconds(), None,
            int(time.time() * 1000) + randint(2 * 24 * 60 * 60 * 1000, 7 * 24 * 60 * 60 * 1000)
        ])
  except Psycopg2Error as e:
    raise SeedingError(
        f"DB INSERT failed for order_line_items. Order ID: {order_id}, Variant: {variant_id}, Error: {e}"
    ) from e


def insert_order_event(cur: cursor, order_id: str, event_type: str, event_payload: str):
  try:
    cur.execute(
        """INSERT INTO order_events (id, order_id, event_type, event_payload, created_at)
            VALUES (%s, %s, %s, %s, %s)""",
        [str(ULID()), order_id, event_type, event_payload,
         get_time_miliseconds()])
  except Psycopg2Error as e:
    raise SeedingError(
        f"DB INSERT failed for order_events. Order ID: {order_id}, Type: {event_type}, Error: {e}"
    ) from e


def get_order_line_items(cur: cursor, offer: ProductOffer, product_id: str, product_title,
                         order_id: str, now_ms: int) -> Dict[str, Any]:
  items: list[Dict[str, Any]] = []
  subtotal_cents = 0
  total_discount_cents = 0
  total_tax_cents = 0
  total_shipping_cents = 0

  for (variant_id, variant) in offer.offer.items():
    try:
      # --- Key data conversion/parsing risk ---
      price_cents_db = int(float(variant.price) * 100)
      list_price_db = int(float(variant.list_price) * 100) if variant.list_price else None
      sale_price_db = int(float(variant.sale_price) * 100) if variant.sale_price else None

      inventory_item = get_inventory_item(cur, product_id, variant_id)
      if inventory_item is None:
        print("Inventory item is not exists, this should not happen")
        continue

      # Check inventory availability before calculating quantity
      quantity_available = int(inventory_item.get('quantity_available', 0))
      quantity = int(quantity_available * 0.20)
      if quantity > 6:
        quantity = fake.random_int(min=1, max=5)

      if quantity_available < quantity or quantity == 0:
        continue

      update_inventory_item(cur, inventory_item['id'], quantity)
      unit_price = sale_price_db if sale_price_db else price_cents_db
      line_subtotal = unit_price * quantity
      discount_cents = int(line_subtotal * 0.05) if choice([True, False]) else 0
      tax_cents = 0
      shipping_cents = 223
      line_total = line_subtotal - discount_cents + tax_cents + shipping_cents

      subtotal_cents += line_subtotal
      total_discount_cents += discount_cents
      total_tax_cents += tax_cents
      total_shipping_cents += shipping_cents

      item: Dict[str, Any] = {
          "inventory_item_id":
          inventory_item['id'],
          "order_line_item":
          OrderLineItem(id=str(ULID()),
                        product_id=product_id,
                        variant_id=variant_id,
                        order_id=order_id,
                        sku=variant.sku,
                        title=product_title,
                        status='CREATED',
                        attributes={
                            'source': 'seed',
                            'auto_generated': "true"
                        },
                        quantity=quantity,
                        unit_price_cents=price_cents_db,
                        list_price_cents=list_price_db,
                        sale_price_cents=sale_price_db,
                        discount_cents=discount_cents,
                        tax_cents=tax_cents,
                        total_cents=line_total,
                        applied_offer_ids=[],
                        product_snapshot=None,
                        shipping_cents=shipping_cents,
                        created_at=now_ms)
      }

      items.append(item)
    except ValueError as e:
      # Catch errors when converting Protobuf string fields (price, etc.) to int/float
      raise SeedingError(
          f"DATA PARSING ERROR in get_order_line_items. Product ID: {product_id}, Variant: {variant_id}, Data: {variant}, Error: {e}"
      ) from e
    except SeedingError:
      # Re-raise any specific errors from nested functions (like get_inventory_item)
      raise
    except Exception as e:
      # Catch all other unexpected errors
      raise SeedingError(
          f"UNEXPECTED ERROR in get_order_line_items. Product ID: {product_id}, Variant: {variant_id}, Error: {e}"
      ) from e

  return {
      'items': items,
      'subtotal_cents': subtotal_cents,
      'total_discount_cents': total_discount_cents,
      'total_tax_cents': total_tax_cents,
      'total_shipping_cents': total_shipping_cents
  }


def get_inventory_item(cur: cursor, product_id: str, variant_id: str):
  try:
    cur.execute(
        """SELECT id, product_id, variant_id, sku, quantity_available, 
                    quantity_reserved, quantity_total, location_id, metadata, 
                    created_at, updated_at 
               FROM inventory_items 
               WHERE product_id = %s AND variant_id = %s""", [product_id, variant_id])

    row = cur.fetchone()
    if not row:
      return None

    return {
        'id': row[0],
        'product_id': row[1],
        'variant_id': row[2],
        'sku': row[3],
        'quantity_available': row[4],
        'quantity_reserved': row[5],
        'quantity_total': row[6],
        'location_id': row[7],
        'metadata': row[8],
        'created_at': row[9],
        'updated_at': row[10]
    }
  except Psycopg2Error as e:
    raise SeedingError(
        f"DB SELECT failed for inventory_items. Product ID: {product_id}, Variant: {variant_id}, Error: {e}"
    ) from e


def update_inventory_item(cur: cursor, id: str, quantity: int):
  stmt = """
    UPDATE inventory_items 
			SET 
					quantity_reserved = quantity_reserved + %s,
					quantity_available = quantity_available - %s,
					updated_at = %s
			WHERE id = %s AND quantity_available >= %s
  """
  try:
    cur.execute(stmt, [quantity, quantity, get_time_miliseconds(), id, quantity])
  except Psycopg2Error as e:
    raise SeedingError(f"DB UPDATE failed for inventory quantity_item. Error: {e}") from e


def insert_inventory_reservation_item(
    cur: cursor,
    reservation_id: str,
    inventory_item_id: str,
    quantity: int,
):
  stmt = """
    INSERT INTO inventory_reservation_items (
			id, 
			reservation_id, 
			inventory_item_id, 
			quantity, 
			created_at
		) VALUES (%s, %s, %s, %s, %s)
  """
  try:
    cur.execute(stmt,
                [str(ULID()), reservation_id, inventory_item_id, quantity,
                 get_time_miliseconds()])
  except Psycopg2Error as e:
    raise SeedingError(f"DB INSERT failed for inventory_reservation_items. Error: {e}") from e
