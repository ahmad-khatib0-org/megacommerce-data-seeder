import random

from google.protobuf import json_format
from products.v1.hero_products_pb2 import (
    CategorySlider,
    HeroProductData,
    HeroProductListItem,
    WelcomeDealsSlider,
)
from psycopg2 import Error as Psycopg2Error
from psycopg2 import Error as Psycopg2Error
from psycopg2.extensions import connection
from psycopg2.extensions import connection
from ulid import ULID
from ulid import ULID

from general_utils.general import get_time_miliseconds
from general_utils.general import get_time_miliseconds
from models.app import SeedingError
from models.app import SeedingError
from seeders.orders import ProductIDAndOffer, get_products


def seed_hero_products(con: connection):
  stmt = """
    INSERT INTO hero_products(id, products_data, created_at) VALUES(%s, %s, %s)
    """

  try:
    with con.cursor() as cur:
      # Create sample hero products data
      hero_product_data = HeroProductData()

      products = get_products(cur)
      sale_products: list[ProductIDAndOffer] = []
      for pro in products:
        if len(sale_products) > 20:
          break
        for (_, variant) in pro.offer.offer.items():
          if variant.sale_price:
            sale_products.append(pro)

      # Build Category Slider
      category_slider = CategorySlider()
      category_slider.title = "Fashion Party"
      category_slider.subtitle = "Shop the latest trends"
      category_slider.button_text = "View All"

      # Add products to category slider
      products_idx = 0
      for _ in range(4):
        (variant_id, variant) = random.choice(list(sale_products[products_idx].offer.offer.items()))
        product = HeroProductListItem()
        product.id = str(ULID())
        product.variant_id = variant_id
        category_slider.products.append(product)
        products_idx += 1

      welcome_deals = WelcomeDealsSlider()
      welcome_deals.title = "Welcome Deals"
      welcome_deals.subtitle = "Special offers for new customers"
      welcome_deals.button_text = "Shop Now"

      for _ in range(4):
        (variant_id, variant) = random.choice(list(sale_products[products_idx].offer.offer.items()))
        product = HeroProductListItem()
        product.id = str(ULID())
        product.variant_id = variant_id

        welcome_deals.products.append(product)
        products_idx += 1

      hero_product_data.category_slider.CopyFrom(category_slider)
      hero_product_data.welcome_deals_slider.CopyFrom(welcome_deals)

      data_json = json_format.MessageToJson(hero_product_data)
      cur.execute(stmt, [str(ULID()), data_json, get_time_miliseconds()])
    con.commit()

  except Psycopg2Error as e:
    con.rollback()
    raise SeedingError(f"Inserting failed in the hero_products table, err: {e}") from e
  except Exception as e:
    con.rollback()
    raise SeedingError(f"Unexpected error while inserting hero_product: {e}") from e
