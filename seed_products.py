from psycopg2.extensions import connection
from psycopg2.extras import Json, RealDictCursor
from ulid import ULID
from faker import Faker
import random

from generla_utils import time_in_milies
from models.config import Config


def seed_products(conn: connection, cfg: Config):
  fake = Faker()
  with conn.cursor(cursor_factory=RealDictCursor) as cur:
    stmt = 'SELECT id FROM users LIMIT %s'
    cur.execute(stmt, (cfg.seeding.number_of_suppliers_have_products, ))
    rows_ids = cur.fetchall()

    cur.execute('SELECT id FROM tags')
    rows_tags = cur.fetchall()
    tags: list[int] = [row['id'] for row in rows_tags]

    stmt = '''
      INSERT INTO products(
        id, user_id, sku, status, title, description, slug, 
        price, currency_code, tags, ar_enabled, created_at
      ) VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    '''

    bools: list[bool] = [True, False]
    for row in rows_ids:
      user_id = row['id']
      for _ in range(cfg.seeding.number_of_products_per_supplier):
        title = fake.catch_phrase()[:250]
        slug = title.replace(" ", "-").lower()
        cur.execute(
            stmt,
            (
                str(ULID()),
                user_id,
                fake.bothify(text='???-########').upper(),
                'pending',
                title,
                fake.text(max_nb_chars=500),
                slug,
                fake.random_number(3),
                fake.currency_code(),
                Json([{
                    'id': random.choice(tags)
                }, {
                    'id': random.choice(tags)
                }]),
                random.choice(bools),
                time_in_milies(),
            ),
        )
