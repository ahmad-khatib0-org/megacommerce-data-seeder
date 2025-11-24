import random

from faker import Faker

fake = Faker()


def generate_product_title(category_id) -> str:
  """
    Generate realistic product titles for specific categories
    """

  # Category definitions with realistic components
  categories = {
      # Women's Clothing
      'womens_clothing': {
          'brands': [
              'Zara', 'H&M', 'Forever 21', 'Gap', 'Uniqlo', 'Mango', 'Anthropologie', 'Reformation',
              'Aritzia', 'Free People'
          ],
          'items': [
              'Dress', 'Blouse', 'Skirt', 'Jeans', 'T-Shirt', 'Sweater', 'Jacket', 'Cardigan',
              'Pants', 'Shorts', 'Jumpsuit', 'Romper'
          ],
          'materials': [
              'Cotton', 'Linen', 'Silk', 'Wool', 'Denim', 'Polyester', 'Rayon', 'Cashmere',
              'Velvet', 'Satin'
          ],
          'styles': [
              'A-Line', 'Bodycon', 'Off-Shoulder', 'Wrap', 'Maxi', 'Midi', 'Mini', 'Bohemian',
              'Classic', 'Modern', 'Vintage'
          ],
          'colors': [
              'Black', 'White', 'Navy', 'Ivory', 'Burgundy', 'Emerald', 'Dusty Pink', 'Cream',
              'Charcoal', 'Olive Green'
          ],
          'patterns':
          ['Floral', 'Striped', 'Plaid', 'Polka Dot', 'Solid', 'Printed', 'Embroidered', 'Lace'],
          'formats': [
              "{brand} {style} {material} {item}", "{color} {pattern} {item}",
              "{brand} {item} - {style}", "{material} {style} {item}", "{color} {brand} {item}",
              "{style} {item} with {pattern} detail", "{brand} {color} {material} {item}"
          ]
      },

      # Men's Clothing
      'mens_clothing': {
          'brands': [
              'Nike', 'Adidas', 'Uniqlo', 'Levi\'s', 'Tommy Hilfiger', 'Calvin Klein',
              'Ralph Lauren', 'H&M', 'Zara', 'Under Armour'
          ],
          'items': [
              'T-Shirt', 'Dress Shirt', 'Jeans', 'Chinos', 'Sweater', 'Hoodie', 'Jacket', 'Blazer',
              'Shorts', 'Sweatpants', 'Polo Shirt'
          ],
          'materials': [
              'Cotton', 'Denim', 'Wool', 'Linen', 'Polyester', 'Cashmere', 'Flannel', 'Corduroy',
              'Canvas'
          ],
          'styles': [
              'Slim Fit', 'Regular Fit', 'Relaxed Fit', 'Classic', 'Modern', 'Athletic', 'Tailored',
              'Casual', 'Business'
          ],
          'colors': [
              'Black', 'White', 'Navy', 'Grey', 'Khaki', 'Olive', 'Burgundy', 'Charcoal',
              'Royal Blue', 'Beige'
          ],
          'patterns': ['Solid', 'Striped', 'Plaid', 'Checked', 'Patterned', 'Textured', 'Camo'],
          'formats': [
              "{brand} {style} {item}", "{material} {color} {item}", "{brand} {item} - {style} Fit",
              "{style} {material} {item}", "{color} {pattern} {item} by {brand}",
              "{brand} Classic {item}", "{style} {item} in {color}"
          ]
      },

      # Footwear
      'footwear': {
          'brands': [
              'Nike', 'Adidas', 'Converse', 'Vans', 'Clarks', 'Dr. Martens', 'Steve Madden',
              'Skechers', 'New Balance', 'Puma'
          ],
          'items': [
              'Sneakers', 'Running Shoes', 'Boots', 'Sandals', 'Loafers', 'Oxfords', 'Slip-ons',
              'High Tops', 'Athletic Shoes', 'Casual Shoes'
          ],
          'materials':
          ['Leather', 'Suede', 'Canvas', 'Mesh', 'Rubber', 'Synthetic', 'Nubuck', 'Textile'],
          'styles': [
              'Casual', 'Athletic', 'Formal', 'Comfort', 'Fashion', 'Outdoor', 'Lifestyle',
              'Performance'
          ],
          'colors': [
              'Black', 'White', 'Brown', 'Navy', 'Grey', 'Red', 'Blue', 'Green', 'Beige',
              'Multi-color'
          ],
          'features': [
              'Air Cushion', 'Memory Foam', 'Waterproof', 'Slip-Resistant', 'Lightweight',
              'Breathable', 'Arch Support'
          ],
          'formats': [
              "{brand} {style} {items}", "{material} {color} {items}",
              "{brand} {items} with {features}", "{style} {items} - {brand}",
              "{color} {material} {items}", "{brand} {features} {items}",
              "{style} {items} in {color}"
          ]
      },

      # Accessories
      'accessories': {
          'brands': [
              'Fossil', 'Michael Kors', 'Kate Spade', 'Coach', 'Ray-Ban', 'Oakley', 'Dagne Dover',
              'Herschel', 'Tumi', 'Longchamp'
          ],
          'items': [
              'Handbag', 'Backpack', 'Wallet', 'Sunglasses', 'Watch', 'Belt', 'Scarf', 'Hat',
              'Gloves', 'Tie', 'Bag'
          ],
          'materials': [
              'Leather', 'Canvas', 'Suede', 'Nylon', 'Polyester', 'Stainless Steel', 'Acetate',
              'Wool', 'Cashmere'
          ],
          'styles':
          ['Classic', 'Modern', 'Vintage', 'Sporty', 'Luxury', 'Casual', 'Designer', 'Minimalist'],
          'colors': [
              'Black', 'Brown', 'Navy', 'Cognac', 'Tan', 'Burgundy', 'Olive', 'Grey', 'Camel',
              'Multi'
          ],
          'features': [
              'Adjustable', 'Water-resistant', 'Multi-compartment', 'RFID Protection', 'Padded',
              'Foldable'
          ],
          'formats': [
              "{brand} {material} {item}", "{style} {color} {item}", "{brand} {item} - {style}",
              "{material} {item} with {features}", "{color} {brand} {item}",
              "{style} {item} in {color}", "{brand} {features} {item}"
          ]
      },

      # Jewelry
      'jewelry': {
          'brands': [
              'Pandora', 'Swarovski', 'Tiffany & Co.', 'Kay Jewelers', 'Zales', 'James Avery',
              'Alex and Ani', 'Kendra Scott', 'David Yurman'
          ],
          'items': [
              'Necklace', 'Bracelet', 'Earrings', 'Ring', 'Pendant', 'Charm', 'Anklet', 'Brooch',
              'Cufflinks'
          ],
          'materials': [
              'Sterling Silver', 'Gold', 'Rose Gold', 'Platinum', 'Stainless Steel', 'Pearl',
              'Crystal', 'Diamond', 'Gemstone'
          ],
          'styles': [
              'Classic', 'Modern', 'Vintage', 'Minimalist', 'Statement', 'Bohemian', 'Luxury',
              'Personalized'
          ],
          'colors':
          ['Silver', 'Gold', 'Rose Gold', 'White Gold', 'Multi-tone', 'Platinum', 'Black'],
          'features':
          ['Engravable', 'Adjustable', 'Birthstone', 'Personalized', 'Stackable', 'Layered'],
          'formats': [
              "{brand} {material} {item}", "{style} {material} {item} with {features}",
              "{brand} {item} - {style}", "{material} {color} {item}",
              "{style} {item} featuring {features}", "{brand} {features} {item}",
              "{material} {style} {item}"
          ]
      }
  }

  # Get category data or return default if not found
  category = categories.get(category_id)
  if not category:
    return f"Product for {category_id}"

  # Choose a random format and fill in the components
  format_template = random.choice(category['formats'])

  # Handle different item key names (some categories use 'items', others use 'item')
  items_key = 'items' if 'items' in category else 'item'

  # Generate the title by replacing placeholders
  title = format_template.format(
      brand=random.choice(category['brands']),
      item=random.choice(category[items_key]),
      material=random.choice(category['materials']),
      style=random.choice(category['styles']),
      color=random.choice(category['colors']),
      pattern=random.choice(category.get('patterns', [''])),
      features=random.choice(category.get('features', [''])),
      items=random.choice(category[items_key])  # alias for items_key
  )

  # Clean up any double spaces and trim
  title = ' '.join(title.split())
  return title[:250]  # Ensure it doesn't exceed 250 characters


# Usage examples
# if __name__ == "__main__":
#   categories = ['womens_clothing', 'mens_clothing', 'footwear', 'accessories', 'jewelry']
#
#   for category in categories:
#     print(f"\n{category.replace('_', ' ').title()}:")
#     for _ in range(5):
#       title = generate_category_title(category)
#       print(f"  - {title}")
