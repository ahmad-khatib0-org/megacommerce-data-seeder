from datetime import datetime
import random

from ulid import ULID


def generate_random_upc():
  """Generate a valid UPC-A code (12 digits)"""
  # Generate first 11 digits randomly
  digits = [random.randint(0, 9) for _ in range(11)]

  # Calculate checksum (UPC uses GTIN checksum)
  total = 0
  for i, digit in enumerate(digits):
    multiplier = 3 if i % 2 == 0 else 1
    total += digit * multiplier

  checksum = (10 - (total % 10)) % 10
  digits.append(checksum)

  # Convert to string
  return ''.join(str(d) for d in digits)


def generate_random_ean():
  """Generate a valid EAN-13 code (13 digits)"""
  # Generate first 12 digits randomly
  digits = [random.randint(0, 9) for _ in range(12)]

  # Calculate checksum (EAN-13 uses GTIN checksum)
  total = 0
  for i, digit in enumerate(digits):
    multiplier = 1 if i % 2 == 0 else 3
    total += digit * multiplier

  checksum = (10 - (total % 10)) % 10
  digits.append(checksum)

  return ''.join(str(d) for d in digits)


def generate_random_gtin(length=8):
  """Generate a valid GTIN code (8-14 digits)"""
  if length < 8 or length > 14:
    length = random.randint(8, 14)

  # Generate first (length-1) digits randomly
  digits = [random.randint(0, 9) for _ in range(length - 1)]

  # Calculate checksum (from right to left)
  total = 0
  for i, digit in enumerate(reversed(digits)):
    multiplier = 3 if i % 2 == 0 else 1
    total += digit * multiplier

  checksum = (10 - (total % 10)) % 10
  digits.append(checksum)

  return ''.join(str(d) for d in digits)


def generate_product_id_info():
  """Main flow: randomly decide if product has ID, then generate appropriate ID"""
  # Randomly decide if product has ID (70% chance)
  has_product_id = random.random() < 0.7

  if not has_product_id:
    return False, None, None

  # Choose product ID type - UPC is most common for fashion
  id_types = ["UPC", "EAN", "GTIN"]
  weights = [0.7, 0.2, 0.1]  # Bias towards UPC for fashion
  chosen_type = random.choices(id_types, weights=weights)[0]

  # Generate appropriate ID
  if chosen_type == "UPC":
    product_id = generate_random_upc()
  elif chosen_type == "EAN":
    product_id = generate_random_ean()
  else:  # GTIN
    product_id = generate_random_gtin()

  return True, product_id, chosen_type


# Fashion-specific version with higher probability of having product IDs
def generate_fashion_product_id_info():
  """Version biased for fashion products (higher chance of UPC)"""
  # 85% chance for fashion items to have product IDs
  has_product_id = random.random() < 0.85

  if not has_product_id:
    return False, None, None

  # Strong bias towards UPC for fashion (85% UPC, 15% EAN)
  chosen_type = random.choices(["UPC", "EAN"], weights=[0.85, 0.15])[0]

  if chosen_type == "UPC":
    product_id = generate_random_upc()
  else:
    product_id = generate_random_ean()

  return True, product_id, chosen_type


fashion_bullet_points = [
    "Made from premium 100% organic cotton for superior comfort and breathability",
    "Machine washable for easy care and maintenance",
    "Available in multiple sizes from XS to XXL for perfect fit",
    "Features stretch technology for enhanced mobility and flexibility",
    "Designed with moisture-wicking fabric to keep you dry and comfortable",
    "Classic tailored fit that flatters all body types",
    "Reinforced stitching for exceptional durability and long-lasting wear",
    "Breathable fabric ideal for year-round comfort",
    "Tagless design prevents irritation and enhances comfort",
    "Wrinkle-resistant material maintains sharp appearance all day",
    "Eco-friendly production using sustainable materials and processes",
    "Adjustable waistband for customizable comfort and perfect fit",
    "Multiple color options to match your personal style",
    "Quick-dry technology perfect for active lifestyles",
    "UV protection (UPF 50+) for sun safety during outdoor activities",
    "Anti-odor treatment prevents bacterial growth and keeps clothes fresh",
    "Four-way stretch fabric moves with your body in all directions",
    "Soft brushed interior for ultimate comfort against skin",
    "Fade-resistant colors maintain vibrant appearance after multiple washes",
    "Generous pocket space with secure closures for valuables",
    "Designed with ventilation panels in key sweat areas",
    "Professional appearance suitable for business casual environments",
    "Lightweight fabric perfect for layering or standalone wear",
    "Ribbed cuffs and hem for secure fit and modern look",
    "Ethically manufactured in certified facilities",
    "Colorfast material prevents bleeding in wash",
    "Slim fit design creates modern, streamlined silhouette",
    "Preshrunk fabric maintains size and shape after washing",
    "Reinforced knees and elbows in strategic wear areas",
    "Butter-soft texture feels luxurious against skin", "Easy care - tumble dry low or hang dry",
    "Versatile style transitions seamlessly from day to night",
    "Breathable mesh lining enhances airflow and comfort",
    "Stain-resistant treatment for worry-free wear", "Classic design that never goes out of style"
]


def get_random_bullet_points(min_points=3, max_points=11):
  num_points = random.randint(min_points, max_points)
  selected_points = random.sample(fashion_bullet_points, num_points)
  return selected_points


def generate_bullet_points_list():
  """Generate bullet points list as array of objects matching ProductBulletPoint schema"""
  bullet_texts = get_random_bullet_points()
  current_time = int(datetime.now().timestamp() * 1000)  # milliseconds

  bullet_points_list = [
      {
          "id": str(str(ULID())),
          "text": bullet_text,
          "created_at": current_time,
          "updated_at": None  # optional field
      } for bullet_text in bullet_texts
  ]

  return bullet_points_list
