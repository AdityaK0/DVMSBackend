"""
Poster generation service using Pillow.
Generates event posters with festival templates, vendor info, and product images.
"""
from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO
import os
from django.conf import settings
from django.core.files.base import ContentFile
import cloudinary.uploader
import logging

logger = logging.getLogger(__name__)


def load_image_from_url(url):
    """Load an image from URL"""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return Image.open(BytesIO(response.content))
    except Exception as e:
        logger.error(f"Error loading image from URL {url}: {str(e)}")
        return None


def get_default_font(size=40):
    """Get a default font, fallback to default if not available"""
    try:
        # Try to use a system font
        font_paths = [
            '/System/Library/Fonts/Helvetica.ttc',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
            'arial.ttf',
        ]
        for path in font_paths:
            if os.path.exists(path):
                return ImageFont.truetype(path, size)
    except Exception:
        pass
    
    # Fallback to default font
    try:
        return ImageFont.load_default()
    except Exception:
        return None


def generate_poster(
    event_title,
    vendor_name,
    vendor_logo_url,
    product_images,
    festival_template,
    custom_message="",
    width=1200,
    height=1600
):
    """
    Generate an event poster using Pillow.
    
    Args:
        event_title: Title of the event
        vendor_name: Name of the vendor
        vendor_logo_url: URL of vendor logo
        product_images: List of product image URLs
        festival_template: Festival template dict with colors
        custom_message: Custom message to display
        width: Poster width in pixels
        height: Poster height in pixels
    
    Returns:
        PIL Image object
    """
    # Create base image with background color
    bg_color = festival_template.get('preset_colors', {}).get('primary', '#F97316')
    img = Image.new('RGB', (width, height), color=bg_color)
    draw = ImageDraw.Draw(img)
    
    # Get fonts
    title_font = get_default_font(60)
    vendor_font = get_default_font(40)
    message_font = get_default_font(35)
    product_font = get_default_font(30)
    
    # Colors from template
    colors = festival_template.get('preset_colors', {})
    primary_color = colors.get('primary', '#F97316')
    secondary_color = colors.get('secondary', '#FFA500')
    text_color = '#FFFFFF'
    
    y_offset = 50
    
    # 1. Vendor Logo (top center)
    if vendor_logo_url:
        logo_img = load_image_from_url(vendor_logo_url)
        if logo_img:
            # Resize logo to fit
            logo_size = 150
            logo_img = logo_img.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
            # Paste logo at top center
            logo_x = (width - logo_size) // 2
            img.paste(logo_img, (logo_x, y_offset), logo_img if logo_img.mode == 'RGBA' else None)
            y_offset += logo_size + 30
    
    # 2. Event Title
    if title_font:
        title_bbox = draw.textbbox((0, 0), event_title, font=title_font)
        title_width = title_bbox[2] - title_bbox[0]
        title_x = (width - title_width) // 2
        draw.text((title_x, y_offset), event_title, fill=text_color, font=title_font)
        y_offset += 100
    
    # 3. Vendor Name
    if vendor_font:
        vendor_bbox = draw.textbbox((0, 0), vendor_name, font=vendor_font)
        vendor_width = vendor_bbox[2] - vendor_bbox[0]
        vendor_x = (width - vendor_width) // 2
        draw.text((vendor_x, y_offset), vendor_name, fill=text_color, font=vendor_font)
        y_offset += 80
    
    # 4. Custom Message
    if custom_message and message_font:
        # Wrap text if too long
        words = custom_message.split()
        lines = []
        current_line = []
        max_width = width - 100
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            bbox = draw.textbbox((0, 0), test_line, font=message_font)
            if bbox[2] - bbox[0] <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
        if current_line:
            lines.append(' '.join(current_line))
        
        for line in lines[:3]:  # Max 3 lines
            line_bbox = draw.textbbox((0, 0), line, font=message_font)
            line_width = line_bbox[2] - line_bbox[0]
            line_x = (width - line_width) // 2
            draw.text((line_x, y_offset), line, fill=text_color, font=message_font)
            y_offset += 50
    
    y_offset += 30
    
    # 5. Product Images (grid layout)
    if product_images:
        num_products = min(len(product_images), 4)  # Max 4 products
        products_per_row = 2
        product_size = (width - 100) // products_per_row - 20
        
        for i, product_url in enumerate(product_images[:num_products]):
            if y_offset + product_size > height - 100:
                break
            
            row = i // products_per_row
            col = i % products_per_row
            
            product_img = load_image_from_url(product_url)
            if product_img:
                # Resize and center crop
                product_img.thumbnail((product_size, product_size), Image.Resampling.LANCZOS)
                
                x = 50 + col * (product_size + 20)
                y = y_offset + row * (product_size + 20)
                
                # Create a white background for product image
                bg = Image.new('RGB', (product_size, product_size), 'white')
                # Center the product image
                paste_x = (product_size - product_img.width) // 2
                paste_y = (product_size - product_img.height) // 2
                bg.paste(product_img, (paste_x, paste_y))
                
                img.paste(bg, (x, y))
        
        y_offset += (num_products // products_per_row + 1) * (product_size + 20)
    
    # 6. Hashtags (bottom)
    hashtags = festival_template.get('hashtags', [])
    if hashtags and product_font:
        hashtag_text = ' '.join(hashtags[:3])  # Max 3 hashtags
        hashtag_bbox = draw.textbbox((0, 0), hashtag_text, font=product_font)
        hashtag_width = hashtag_bbox[2] - hashtag_bbox[0]
        hashtag_x = (width - hashtag_width) // 2
        hashtag_y = height - 80
        draw.text((hashtag_x, hashtag_y), hashtag_text, fill=text_color, font=product_font)
    
    return img


def upload_poster_to_cloudinary(poster_image, event_id):
    """
    Upload poster image to Cloudinary.
    
    Args:
        poster_image: PIL Image object
        event_id: Event ID for naming
    
    Returns:
        URL of uploaded image
    """
    try:
        # Convert PIL Image to bytes
        buffer = BytesIO()
        poster_image.save(buffer, format='PNG')
        buffer.seek(0)
        
        # Upload to Cloudinary
        upload_result = cloudinary.uploader.upload(
            buffer,
            folder='events/posters',
            public_id=f'event_{event_id}_poster',
            resource_type='image',
            format='png'
        )
        
        return upload_result.get('secure_url') or upload_result.get('url')
    except Exception as e:
        logger.error(f"Error uploading poster to Cloudinary: {str(e)}")
        raise


def build_and_upload_poster(event, festival_template, selected_product_ids):
    """
    Build poster for an event and upload it.
    
    Args:
        event: Event instance
        festival_template: Festival template dict
        selected_product_ids: List of product IDs to include
    
    Returns:
        URL of uploaded poster
    """
    from apps.products.models import Product
    
    # Get vendor info
    vendor = event.vendor
    vendor_name = vendor.business_name
    vendor_logo_url = vendor.logo or ""
    
    # Get product images
    products = Product.objects.filter(
        id__in=selected_product_ids,
        vendor=vendor
    )[:4]  # Max 4 products
    
    product_images = []
    for product in products:
        if product.primary_image:
            product_images.append(product.primary_image)
        elif product.image_urls:
            product_images.append(product.image_urls[0])
    
    # Generate poster
    poster_image = generate_poster(
        event_title=event.name,
        vendor_name=vendor_name,
        vendor_logo_url=vendor_logo_url,
        product_images=product_images,
        festival_template=festival_template,
        custom_message=event.custom_message or ""
    )
    
    # Upload to Cloudinary
    poster_url = upload_poster_to_cloudinary(poster_image, event.id)
    
    return poster_url

