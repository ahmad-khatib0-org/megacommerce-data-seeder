import os
import random
import random
from typing import Any, Dict, List, Tuple

from faker import Faker
from minio import Minio
from psycopg2.extras import Json, RealDictCursor
from ulid import ULID

from general_utils.general import get_time_miliseconds
from models.config import Config
from seeders.product_title import generate_product_title
from seeders.products import (
    generate_bullet_points_list,
    generate_fashion_product_id_info,
)

fake = Faker()

FULFILLMENT_TYPE = ['megacommerce', 'supplier']
STATUS = ['pending', 'published']
OFFERING_CONDITION = ['new', 'used']


class ProductGenerator:
  def __init__(self, cfg: Config):
    self.used_variant_names = set()
    self.minio_client = Minio(cfg.minio.amazon_s3_endpoint,
                              access_key=cfg.minio.amazon_s3_access_key_id,
                              secret_key=cfg.minio.amazon_s3_secret_access_key,
                              secure=False)
    self.minio_bucket: str = cfg.minio.amazon_s3_bucket
    self.ensure_bucket()

  def ensure_bucket(self) -> None:
    """Ensure MinIO bucket exists, create if it doesn't"""
    try:
      # Check if bucket exists
      if not self.minio_client.bucket_exists(self.minio_bucket):
        # Create bucket if it doesn't exist
        self.minio_client.make_bucket(self.minio_bucket)
        print(f"Bucket '{self.minio_bucket}' created successfully")
      else:
        print(f"Bucket '{self.minio_bucket}' already exists")
    except Exception as e:
      print(f"Error ensuring bucket '{self.minio_bucket}': {e}")
      raise

  def generate_any_value(self, attribute_config: Dict) -> Dict:
    """Generate value based on attribute type and validation rules, return in Any proto format"""
    attr_type = attribute_config.get('type', 'input')
    validation = attribute_config.get('validation')

    if attr_type == 'select':
      # For select type, choose from string_array
      options = attribute_config.get('string_array', [])
      if options:
        value = random.choice(options)
        if attribute_config.get('is_multiple', False):
          # For multiple select, choose 1-3 options
          count = random.randint(1, min(3, len(options)))
          value = random.sample(options, count)
          value = ','.join(value)
        return self._serialize_string_value(value)

    elif attr_type == 'boolean':
      value = random.choice([True, False])
      return self._serialize_bool_value(value)

    elif attr_type == 'input':
      # Handle string input with validation
      if validation and 'rule' in validation:
        rule_data = validation['rule']
        if 'Str' in rule_data:
          str_rules = rule_data['Str']['rules']
          min_len, max_len = 3, 100  # defaults
          for rule in str_rules:
            if rule['type'] == 0:  # STRING_RULE_TYPE_MIN
              min_len = int(rule['value'])
            elif rule['type'] == 1:  # STRING_RULE_TYPE_MAX
              max_len = int(rule['value'])

          # Generate text within length constraints
          text = fake.text(max_nb_chars=max_len)
          while len(text) < min_len:
            text += " " + fake.word()
          text = text[:max_len].strip()
          return self._serialize_string_value(text)

        elif 'Numeric' in rule_data:
          numeric_rules = rule_data['Numeric']['rules']
          min_val, max_val = 0, 100  # defaults
          for rule in numeric_rules:
            if rule['type'] in [0, 2]:  # MIN or GT
              min_val = rule['value']
            elif rule['type'] in [1, 3]:  # MAX or LT
              max_val = rule['value']

          # Adjust for exclusive bounds
          if any(rule['type'] in [2, 3] for rule in numeric_rules):  # GT or LT
            value = random.uniform(min_val + 0.1, max_val - 0.1)
          else:
            value = random.uniform(min_val, max_val)

          # Return as string for input type, or could be numeric
          return self._serialize_string_value(f"{value:.2f}")

      # Default string generation
      return self._serialize_string_value(fake.text(max_nb_chars=100).strip())

    # Fallback
    return self._serialize_string_value(fake.word())

  def _serialize_string_value(self, value: str) -> Dict:
    """Serialize string value to Any proto format"""
    return {
        "type_url": "type.googleapis.com/google.protobuf.StringValue",
        "value": [ord(c) for c in value]
    }

  def _serialize_bool_value(self, value: bool) -> Dict:
    """Serialize bool value to Any proto format"""
    return {
        "type_url": "type.googleapis.com/google.protobuf.BoolValue",
        "value": [1] if value else [0]
    }

  def _serialize_int_value(self, value: int) -> Dict:
    """Serialize int value to Any proto format"""
    return {
        "type_url": "type.googleapis.com/google.protobuf.Int32Value",
        "value": list(value.to_bytes(4, 'little'))
    }

  def generate_variant_name(self, subcategory_id: str, variant_data: Dict) -> str:
    """Generate descriptive variant name based on attribute values"""
    # Extract meaningful attributes for naming
    name_parts = []

    # Common attribute patterns for naming
    size_attrs = ['size', 'dimension', 'weight', 'capacity']
    color_attrs = ['color', 'colour', 'finish', 'appearance']
    material_attrs = ['material', 'fabric', 'composition']
    type_attrs = ['type', 'model', 'form']

    # Decode variant data to find values
    for attr_id, any_data in variant_data.items():
      if any_data['type_url'] == "type.googleapis.com/google.protobuf.StringValue":
        value = ''.join(chr(b) for b in any_data['value'])

        if attr_id in size_attrs and len(name_parts) < 2:
          name_parts.append(value[:10].lower())
        elif attr_id in color_attrs and len(name_parts) < 2:
          name_parts.append(value[:10].lower())
        elif attr_id in material_attrs and len(name_parts) < 2:
          name_parts.append(value[:8].lower())
        elif attr_id in type_attrs and len(name_parts) < 2:
          name_parts.append(value[:8].lower())

    # If no good attributes found, generate generic name
    if not name_parts:
      if subcategory_id == 'womens_clothing':
        sizes = ['xs', 's', 'm', 'l', 'xl']
        colors = ['black', 'white', 'red', 'blue', 'green', 'pink']
        name_parts = [random.choice(sizes), random.choice(colors)]
      elif subcategory_id == 'mens_clothing':
        sizes = ['s', 'm', 'l', 'xl', 'xxl']
        colors = ['navy', 'grey', 'black', 'blue', 'green']
        name_parts = [random.choice(sizes), random.choice(colors)]
      elif subcategory_id == 'footwear':
        sizes = ['6', '7', '8', '9', '10', '11']
        colors = ['black', 'brown', 'white', 'blue']
        name_parts = [f"size{sizes[0]}", random.choice(colors)]
      elif subcategory_id == 'accessories':
        styles = ['classic', 'modern', 'vintage', 'sporty']
        colors = ['black', 'brown', 'navy', 'cognac']
        name_parts = [random.choice(styles), random.choice(colors)]
      elif subcategory_id == 'jewelry':
        materials = ['silver', 'gold', 'rose-gold', 'platinum']
        types = ['chain', 'beaded', 'cuff', 'hoop']
        name_parts = [random.choice(materials), random.choice(types)]
      else:
        # Generic fallback
        name_parts = [fake.color_name().lower(), fake.word().lower()]

    variant_name = '-'.join(name_parts[:2])

    # Ensure uniqueness
    base_name = variant_name
    counter = 1
    while variant_name in self.used_variant_names:
      variant_name = f"{base_name}-{counter}"
      counter += 1

    self.used_variant_names.add(variant_name)
    return variant_name

  def generate_product_details(self, subcategory: Dict,
                               has_variants: bool) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Generate product details structure based on subcategory attributes"""
    attributes = subcategory.get('attributes', {})

    # Separate shared and variant attributes
    shared_attrs = {}
    variant_attrs = {}

    for attr_id, attr_config in attributes.items():
      if attr_config.get('include_in_variants', False):
        variant_attrs[attr_id] = attr_config
      else:
        shared_attrs[attr_id] = attr_config

    # Generate shared values
    shared_data = {}
    for attr_id, attr_config in shared_attrs.items():
      shared_data[attr_id] = self.generate_any_value(attr_config)

    # Generate variant data
    details = {}
    subcategory_id = subcategory.get('id', 'unknown')

    variants_ids: list[str] = []
    main_variant_id = ''
    if has_variants:
      # Generate 2 variants
      for _ in range(2):
        variant_id = str(ULID())
        variants_ids.append(variant_id)
        variant_data = {}

        # Generate values for each variant attribute
        for attr_id, attr_config in variant_attrs.items():
          variant_data[attr_id] = self.generate_any_value(attr_config)

        variant_name = self.generate_variant_name(subcategory_id, variant_data)

        details[variant_id] = {"variant_name": variant_name, "variant_data": variant_data}
    else:
      # Generate single variant
      variant_id = str(ULID())
      main_variant_id = variant_id
      variant_data = {}

      for attr_id, attr_config in variant_attrs.items():
        variant_data[attr_id] = self.generate_any_value(attr_config)

      variant_name = self.generate_variant_name(subcategory_id, variant_data)

      details[variant_id] = {"variant_name": variant_name, "variant_data": variant_data}

    return {
        "shared": shared_data,
        "details": details
    }, {
        "main_variant": main_variant_id,
        "variants_ids": variants_ids
    }

  def generate_product_offer(self,
                             has_variants: bool,
                             main_variant_id: str,
                             variant_ids: List[str] = []) -> Dict[str, Any]:
    """Generate product offer data based on variants"""
    def generate_minimum_orders() -> List[Dict[str, Any]]:
      """Generate minimum order tiers"""
      current_time = get_time_miliseconds()
      tiers = [{
          "id": "min_1",
          "price": "79.99",
          "quantity": 10,
          "created_at": current_time,
          "updated_at": None
      }, {
          "id": "min_2",
          "price": "69.99",
          "quantity": 50,
          "created_at": current_time,
          "updated_at": None
      }, {
          "id": "min_3",
          "price": "59.99",
          "quantity": 100,
          "created_at": current_time,
          "updated_at": None
      }]
      return random.sample(tiers, random.randint(1, 3))

    def generate_variant_offer(variant_id: str, is_main: bool = False) -> Dict[str, Any]:
      """Generate offer data for a single variant"""
      base_price = round(random.uniform(29.99, 199.99), 2)
      list_price = round(base_price * random.uniform(1.1, 1.3), 2)
      has_sale = random.random() > 0.6
      has_min_orders = random.random() > 0.85

      current_time = get_time_miliseconds()

      offering_condition = random.choice(OFFERING_CONDITION)
      offer = {
          "sku": f"SKU-{variant_id[:8].upper()}",
          "quantity": random.randint(10, 1000),
          "price": f"{base_price:.2f}",
          "offering_condition": offering_condition,
          "condition_note": "Excellent condition" if offering_condition == 'used' else None,
          "list_price": f"{list_price:.2f}",
          "has_sale_price": has_sale,
          "sale_price": f"{base_price * 0.8:.2f}" if has_sale else None,
          "sale_price_start": str(current_time - 86400000) if has_sale else None,  # 1 day ago
          "sale_price_end":
          str(current_time + 86400000 * 7) if has_sale else None,  # 7 days from now
          "has_minimum_orders": has_min_orders,
          "minimum_orders": generate_minimum_orders() if has_min_orders else []
      }

      # Main variant gets more quantity and better pricing
      if is_main:
        offer["quantity"] = random.randint(500, 2000)
        offer["price"] = f"{base_price * 0.9:.2f}"  # 10% discount for main variant

      return offer

    # Generate the offer map
    offer_map = {}

    if has_variants and variant_ids:
      # Generate offers for all variants
      for _, variant_id in enumerate(variant_ids):
        is_main = (variant_id == main_variant_id)
        offer_map[variant_id] = generate_variant_offer(variant_id, is_main)
    else:
      # Single offer for non-variant product
      offer_map[main_variant_id] = generate_variant_offer(main_variant_id, True)

    return {"offer": offer_map}

  def generate_product_media(self,
                             has_variants: bool,
                             main_variant_id: str,
                             variant_ids: List[str] = [],
                             subcategory_id: str = "") -> Dict[str, Any]:
    """Generate product media structure"""
    def upload_image_to_minio(image_path: str, attachment_id: str) -> Dict[str, Any]:
      """Upload image to MinIO and return media info"""

      try:
        # Determine format from file extension
        file_ext = os.path.splitext(image_path)[1].lower().replace('.', '')
        format_map = {'jpg': 'JPEG', 'jpeg': 'JPEG', 'png': 'PNG', 'gif': 'GIF', 'webp': 'WEBP'}
        format_type = format_map.get(file_ext, 'JPEG')

        # Get file size
        file_size = os.path.getsize(image_path)

        # Upload to MinIO using file path directly
        object_name = f"{attachment_id}.{file_ext}"
        self.minio_client.fput_object(
            bucket_name=self.minio_bucket,
            object_name=object_name,
            file_path=image_path,  # Use fput_object instead of put_object
            content_type=f"image/{format_type.lower()}")

        # Generate URL
        return {"format": format_type, "url": f"{object_name}", "size": file_size}

      except Exception as e:
        print(f"Error uploading image {image_path}: {e}")
        # Fallback to placeholder
        return {
            "format": "JPEG",
            "url": f"https://placeholder.com/{attachment_id}.jpg",
            "size": random.randint(50000, 2000000)
        }

    def get_variant_media() -> Dict[str, Any]:
      """Generate media for a single variant"""
      attachments_path = f"attachments/{subcategory_id}"

      # Get random images from subcategory folder
      if os.path.exists(attachments_path):
        all_images = [
            f for f in os.listdir(attachments_path)
            if f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp'))
        ]
        selected_images = random.sample(all_images, min(random.randint(3, 7), len(all_images)))
      else:
        # Fallback if folder doesn't exist
        selected_images = [f"placeholder_{i}.jpg" for i in range(random.randint(3, 5))]

      # Upload images and create media structure
      images_map = {}
      for img_file in selected_images:
        attachment_id = str(ULID())
        image_path = os.path.join(attachments_path, img_file)

        image_info = upload_image_to_minio(image_path, attachment_id)
        images_map[attachment_id] = image_info

      return {
          "images": images_map,
          "videos": {}  # Empty for now
      }

    def generate_media_structure() -> Dict[str, Any]:
      """Generate the complete media structure"""
      media_map = {}

      if has_variants and variant_ids:
        # Generate media for all variants
        for variant_id in variant_ids:
          variant_media = get_variant_media()
          media_map[variant_id] = variant_media
      else:
        # Single media entry for main variant
        variant_media = get_variant_media()
        media_map[main_variant_id] = variant_media

      return {"media": media_map}

    # Now this returns a Dict, not a coroutine
    return generate_media_structure()

  def generate_product_safety(self, subcategory: Dict) -> Dict:
    """Generate product safety data based on subcategory safety attributes"""
    safety_attrs = subcategory.get('safety', {})
    safety_data = {}

    for safety_id, safety_config in safety_attrs.items():
      safety_data[safety_id] = self.generate_any_value(safety_config)

    return {"safety": safety_data}

  def generate_product_(self):
    pass


def seed_products(conn, cfg: Config):
  """Main function to seed products for suppliers"""
  generator = ProductGenerator(cfg)

  fashion_brands = [
      "Zara", "H&M", "Gucci", "Louis Vuitton", "Chanel", "Nike", "Adidas", "Prada", "Hermès",
      "Dior", "Burberry", "Versace", "Armani", "Calvin Klein", "Ralph Lauren", "Tommy Hilfiger",
      "Balenciaga", "Fendi", "Dolce & Gabbana", "Yves Saint Laurent"
  ]

  with conn.cursor(cursor_factory=RealDictCursor) as cur:
    stmt = "SELECT id FROM users WHERE user_type = 'supplier' AND roles && %s ORDER BY created_at LIMIT %s"
    cur.execute(stmt, (
        ['supplier_admin'],
        cfg.seeding.number_of_suppliers_have_products,
    ))
    rows_ids = cur.fetchall()
    supplier_ids: list[str] = list()
    for row in rows_ids:
      supplier_ids.append(row['id'])

  # Get fashion category with subcategories
  with conn.cursor(cursor_factory=RealDictCursor) as cur:
    cur.execute("SELECT * FROM categories WHERE id = 'fashion'")
    category = cur.fetchone()

  if not category:
    raise ValueError("Fashion category not found")

  subcategories = category.get('subcategories', [])
  if not subcategories:
    raise ValueError("No subcategories found in fashion category")

  # Prepare for sequential subcategory selection
  subcategory_cycle = []
  for supplier_id in supplier_ids:
    # Assign multiple subcategories per supplier in round-robin
    for _ in range(cfg.seeding.number_of_products_per_supplier):
      subcategory_idx = (len(subcategory_cycle)) % len(subcategories)
      subcategory_cycle.append(subcategories[subcategory_idx])

  product_index = 0

  # Generate products for each supplier
  for supplier_id in supplier_ids:
    print(f"Generating products for supplier {supplier_id}")
    for _ in range(cfg.seeding.number_of_products_per_supplier):
      # Get next subcategory in sequence
      subcategory = subcategory_cycle[product_index]
      product_index += 1

      subcategory_id = subcategory.get('id')
      # Randomly decide if product has variants (65% chance)
      has_variants = random.random() < 0.65
      has_brand = random.random() > 0.4
      has_product_id, product_id, product_id_type = generate_fashion_product_id_info()
      description = fake.paragraph()
      fulfillment_type = random.choice(FULFILLMENT_TYPE)
      procesing_time = random.randint(1, 9)

      bullet_points = generate_bullet_points_list()

      # Generate product data
      details, variant_data = generator.generate_product_details(subcategory, has_variants)
      offer = generator.generate_product_offer(has_variants, variant_data['main_variant'],
                                               variant_data['variants_ids'])
      media = generator.generate_product_media(has_variants=True,
                                               main_variant_id=variant_data['main_variant'],
                                               variant_ids=variant_data['variants_ids'],
                                               subcategory_id=subcategory_id)
      safety = generator.generate_product_safety(subcategory)
      status = random.choice(STATUS)

      # Generate other product fields
      title = generate_product_title(subcategory.get('id', 'general'))
      current_time = get_time_miliseconds()

      # Insert product
      args = (
          str(ULID()),  # 1
          supplier_id,  # 2
          title,  # 3
          'fashion',  # 4
          subcategory_id,  # 5
          has_variants,  # 6
          random.choice(fashion_brands) if has_brand else None,  # 7
          has_brand,  # 8
          product_id,  # 9
          has_product_id,  # 10
          product_id_type,  # 11
          description,  # 12
          Json(bullet_points),  # 13
          'USD',  # 14
          fulfillment_type,  # 15
          procesing_time,  # 16
          Json(details),  # 17
          Json(media),  # 18
          Json(offer),  # 19
          Json(safety),  # 20
          Json('[]'),  # 21
          '{"source": "manual_entry"}',  # 22
          False,  # 23
          title.replace(' ', '-'),  # 24
          status,  # 25
          1,  # 26
          1,  # 27
          current_time,  # 28 - created_at
          None if status == 'pending' else current_time,  # 29 - published_at
          None if status == 'pending' else current_time  # 30 - updated_at ← ADD THIS BACK!
      )
      with conn.cursor() as cur:
        cur.execute(
            """
          INSERT INTO products (
              id, user_id, title, category, subcategory, has_variations, brand_name,
              has_brand_name, product_id, has_product_id, product_id_type, description,
              bullet_points, currency_code, fulfillment_type, processing_time, details,
              media, offer, safety, tags, metadata, ar_enabled, slug, status, version,
              schema_version, created_at, published_at, updated_at
          )
          VALUES (
              %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
          )
    """, args)

      print(
          f"  - Created product with {'variants' if has_variants else 'no variants'} for subcategory {subcategory.get('id')}"
      )
