import string
import random
from django.utils.text import slugify

def generate_order_number():
    """Generate a unique order number"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))

def generate_sku(name, vendor_id):
    """Generate SKU based on product name and vendor"""
    base = slugify(name)[:10].upper().replace('-', '')
    suffix = ''.join(random.choices(string.digits, k=4))
    return f"{vendor_id:03d}-{base}-{suffix}"

def calculate_shipping_cost(total_weight, distance=None):
    """Calculate shipping cost based on weight and distance"""
    base_cost = 5.00
    weight_cost = total_weight * 0.5
    return base_cost + weight_cost