import json
from random import choice
from typing import Any, Dict

from faker import Faker
from orders.v1.order_line_items_pb2 import OrderLineItem
from products.v1.product_pb2 import ProductOffer
from psycopg2.extensions import connection, cursor
from ulid import ULID

from general_utils.general import get_time_miliseconds
from models.config import Config
from seeders.orders import create_successful_payment, get_products, get_user_ids

fake = Faker()


def seed_orders(con: connection, cfg: Config):

  with con.cursor() as cur:
    user_ids = get_user_ids(cur, cfg)
    products = get_products(cur)

    product_idx = 0
    for user_id in user_ids:
      for _ in range(cfg.seeding.number_of_customers_have_orders):
        if (product_idx + 1) >= len(products):
          product_idx = 0
        else:
          product_idx += 1

        order_id = str(ULID())
        insert_idempotency_key(cur, user_id, order_id, 'IN_PROGRESS')
        reservation_id = str(ULID())
        reservation_token = f"res_{str(ULID())}"
        insert_inventory_reservation(cur, reservation_id, reservation_token, order_id)

        now_ms = get_time_miliseconds()
        offer = products[product_idx].offer
        product_id = products[product_idx].id
        product_title = products[product_idx].title

        items = get_order_line_items(cur, offer, product_id, product_title, order_id, now_ms)
        order_line_items: list[OrderLineItem] = items['items']
        subtotal_cents = items['subtotal_cents']
        total_discount_cents = items['total_discount_cents']
        total_tax_cents = items['total_tax_cents']
        total_shipping_cents = items['total_shipping_cents']

        total_cents = subtotal_cents - total_discount_cents + total_tax_cents + total_shipping_cents
        insert_order(cur, order_id, user_id, total_cents, subtotal_cents, total_shipping_cents,
                     total_tax_cents, total_discount_cents, total_cents)
        for item in order_line_items:
          insert_order_line_item(cur, order_id, item.product_id, item.variant_id, item.sku,
                                 item.title, item.quantity, item.unit_price_cents,
                                 item.list_price_cents, item.sale_price_cents, item.discount_cents,
                                 item.tax_cents, item.total_cents, item.shipping_cents)
        event_payload = json.dumps({
            'reservation_token': reservation_token,
            'subtotal_cents': subtotal_cents,
            'total_cents': total_cents,
        })
        insert_order_event(cur, order_id, 'CREATED', event_payload)
        update_order_payment_succeeded(cur, 'CAPTURED', 'CONFIRMED', order_id)
        update_order_idempotency_key(cur, 'CONFIRMED', reservation_token)
        event_payload = json.dumps({
            'provider': 'stripe',
        })
        insert_order_event(cur, order_id, 'PAYMENT_CAPTURED', event_payload)


def insert_idempotency_key(
    cur: cursor,
    user_id: str,
    order_id: str,
    status: str,
):
  cur.execute(
      """INSERT INTO order_idempotency_keys (
          id,
          idempotency_key,
          user_id,
          order_id,
          status,
          created_at,
          updated_at,
          expires_at
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
      [
          str(ULID()),
          'idem_' + str(ULID()),
          user_id,
          order_id,
          status,
          get_time_miliseconds(),
          None,
          get_time_miliseconds() + (60 * 1000)  # 1 minute
      ])


def update_order_idempotency_key(cur: cursor, status: str, reservation_token: str):
  stmt = """
    UPDATE order_idempotency_keys SET
      status = %s, 
      updated_at = %s 
    WHERE idempotency_key = %s
  """
  cur.execute(stmt, [status, get_time_miliseconds(), reservation_token])


def insert_inventory_reservation(cur: cursor, id: str, token: str, order_id: str):
  cur.execute(
      """INSERT INTO inventory_reservations (id, reservation_token, order_id, status, expires_at, created_at, updated_at)
    VALUES (%s, %s, %s, %s, %s, %s, %s)""", [
          id, token, order_id, 'RESERVED',
          get_time_miliseconds() + (60 * 1000),
          get_time_miliseconds(), None
      ])


def insert_order(cur: cursor, id: str, user_id: str, payment_amount: int, subtotal_cents: int,
                 shipping_cents: int, tax_cents: int, discount_cents: int, total_cents: int):

  currency = fake.currency_code()
  payment = create_successful_payment(payment_amount, currency)
  cur.execute(
      """INSERT INTO orders (
              id, 
              user_id, 
              currency_code,
              subtotal_cents,
              shipping_cents,
              tax_cents,
              discount_cents,
              total_cents,
              payment_provider,
              payment_transaction_id,
              payment_status,
              payment_provider_response,
              payment_fee_cents,
              inventory_reservation_status,
              product_source,
              shipping_address,
              billing_address,
              metadata,
              status,
              created_at,
              updated_at,
              deleted_at
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


def update_order_payment_succeeded(cur: cursor, payment_status: str, status: str, order_id: str):
  stmt = 'UPDATE orders SET payment_status = %s, status = %s, updated_at = %s WHERE id = %s'
  cur.execute(stmt, [payment_status, status, get_time_miliseconds(), order_id])


def insert_order_line_item(cur: cursor, order_id: str, product_id: str, variant_id: str, sku: str,
                           title: str, quantity: int, unit_price_cents: int,
                           list_price_cents: int | None, sale_price_cents: int | None,
                           discount_cents: int, tax_cents: int, total_cents: int,
                           shipping_cents: int):
  cur.execute(
      """INSERT INTO order_line_items (
          id,
          order_id,
          product_id,
          variant_id,
          sku,
          title,
          attributes,
          quantity,
          unit_price_cents,
          list_price_cents,
          sale_price_cents,
          discount_cents,
          tax_cents,
          total_cents,
          applied_offer_ids,
          product_snapshot,
          status,
          shipping_cents,
          created_at,
          updated_at
         ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
      [
          str(ULID()), order_id, product_id, variant_id, sku, title,
          json.dumps({}), quantity, unit_price_cents, list_price_cents, sale_price_cents,
          discount_cents, tax_cents, total_cents, [], None, 'CREATED', shipping_cents,
          get_time_miliseconds(), None
      ])


def insert_order_event(cur: cursor, order_id: str, event_type: str, event_payload: str):
  cur.execute(
      """INSERT INTO order_events (id, order_id, event_type, event_payload, created_at)
    VALUES (%s, %s, %s, %s, %s)""",
      [str(ULID()), order_id, event_type, event_payload,
       get_time_miliseconds()])


def get_order_line_items(cur: cursor, offer: ProductOffer, product_id: str, product_title,
                         order_id: str, now_ms: int) -> Dict[str, Any]:
  items = []
  subtotal_cents = 0
  total_discount_cents = 0
  total_tax_cents = 0
  total_shipping_cents = 0

  for (variant_id, variant) in offer.offer.items():
    try:
      price_cents_db = int(float(variant.price) * 100)
      list_price_db = int(float(variant.list_price) * 100) if variant.list_price else None
      sale_price_db = int(float(variant.sale_price) * 100) if variant.sale_price else None

      inventory_item = get_inventory_item(cur, product_id, variant_id)
      if inventory_item is None:
        continue

      quantity = int(inventory_item['quantity_available'] * 0.20)
      if quantity > 6:
        quantity = fake.random_int(min=1, max=5)
      if int(inventory_item['quantity_available']) < quantity:
        continue  # without this reserves more items than available

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

      items.append(
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
                        created_at=now_ms))

    except Exception as err:
      raise err

  return {
      'items': items,
      'subtotal_cents': subtotal_cents,
      'total_discount_cents': total_discount_cents,
      'total_tax_cents': total_tax_cents,
      'total_shipping_cents': total_shipping_cents
  }


def get_inventory_item(cur: cursor, product_id: str, variant_id: str):
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
