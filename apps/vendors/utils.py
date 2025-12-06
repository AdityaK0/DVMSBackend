"""
Vendor utility functions for handle generation and validation.
"""
from django.utils.text import slugify
from typing import Optional
import re
import random


# ✅ Curated list of short, meaningful words for Indian audience
# These are used as suffixes when handle conflicts occur
# NO NUMBERS - only beautiful, short, memorable words
HANDLE_SUFFIX_WORDS = [
    # Nature / Aesthetic
    "rest", "mist", "breeze", "ember", "shadow", "dusk", "dawn", "zenith",
    "horizon", "solstice", "lunar", "solar", "nova", "comet", "meteor",
    "aurora", "eclipse", "cosmos", "nebula", "galaxy", "stellar", "orbit",
    "terra", "oasis", "ripple", "stream", "valley", "peak", "summit",
    "cinder", "ember", "glimmer", "spark", "radiance", "alpha",

    # Abstract / Modern
    "alpha", "omega", "matrix", "quantum", "vector", "logic", "cipher",
    "signal", "flux", "pulse", "core", "echo", "shift", "motion", "phase",
    "origin", "prime", "element", "spectrum", "aspect", "vertex", "axis",

    # Soft / Minimalist words (Vercel-style)
    "air", "stone", "silk", "cloud", "light", "wave", "leaf", "field",
    "path", "shade", "calm", "pure", "soft", "still", "flow",

    # Rare beautiful words
    "serene", "ethereal", "velvet", "crystal", "willow", "hollow",
    "harbor", "meadow", "canyon", "harvest", "ember", "arcane", "glyph",
    "tempo", "sonic", "rift", "cascade",

    # Strong / Elegant
    "titan", "atlas", "apollo", "zephyr", "onyx", "obsidian", "crimson",
    "raven", "falcon", "tiger", "wolf", "panther", "phoenix", "dragon",
]




def _generate_abbreviation(business_name: str) -> str:
    """
    Generate a 3-character abbreviation from business name.
    
    Algorithm:
    1. Extract first letter of each word (up to 3 words)
    2. If less than 3 chars, take first 3 chars of business name
    
    Examples:
        "Muskan Shopping Center" -> "msc"
        "ABC Electronics" -> "abc"
        "Shop" -> "sho"
    """
    # Remove special characters and split into words
    words = re.findall(r'\w+', business_name.lower())
    
    if not words:
        return business_name[:3].lower()
    
    # Try to get first letter of each word (up to 3)
    abbr = ''.join(word[0] for word in words[:3])
    
    # If we got 3 chars, return it
    if len(abbr) >= 3:
        return abbr[:3]
    
    # Otherwise, pad with first chars of first word
    first_word = words[0]
    while len(abbr) < 3 and len(first_word) > len(abbr):
        abbr += first_word[len(abbr)]
    
    # If still less than 3, just take first 3 chars of business name
    if len(abbr) < 3:
        abbr = business_name[:3].lower()
    
    return abbr


def generate_unique_handle(business_name: str, vendor_model=None, vendor_id=None) -> str:
    """
    Generate a unique, SEO-friendly handle for a vendor WITHOUT ANY NUMBERS.
    
    Algorithm:
    1. Try: slugified business name (e.g., "royal-furniture")
    2. If taken, try: base + random word from list (e.g., "royal-furniture-aurora")
    3. Keep trying random words until all 103 words are tried
    4. If all words taken, try: base + word + abbreviation (e.g., "royal-furniture-aurora-rf")
    5. Last resort: use vendor ID creatively (e.g., "royal-furniture-v7" or "royal-furniture-alpha")
    
    ✅ NO RANDOM INTEGERS - Uses vendor ID only as last resort!
    
    Args:
        business_name: The vendor's business name
        vendor_model: The Vendor model class (passed to avoid circular imports)
        vendor_id: Optional vendor ID for last resort uniqueness
    
    Returns:
        A unique handle string (max 50 characters)
    
    Examples:
        "Royal Furniture" -> "royal-furniture"
        "Royal Furniture" (if exists) -> "royal-furniture-aurora"
        "Royal Furniture" (if aurora taken) -> "royal-furniture-quantum"
        "Royal Furniture" (all words taken) -> "royal-furniture-aurora-rf"
    """
    if vendor_model is None:
        from apps.vendors.models import Vendor
        vendor_model = Vendor
    
    # Generate base slug from business name
    base_slug = slugify(business_name)
    
    # Ensure base slug is not empty
    if not base_slug:
        base_slug = "vendor"
    
    # Truncate to leave room for suffix
    max_base_length = 50
    base_slug = base_slug[:max_base_length]
    
    # Step 1: Try base slug first
    handle = base_slug
    if not vendor_model.objects.filter(handle=handle).exists():
        return handle
    
    # Step 2: Try base + random words from curated list (103 attempts!)
    # Shuffle the list to get different words each time
    word_list = HANDLE_SUFFIX_WORDS.copy()
    random.shuffle(word_list)
    
    # Adjust base length to fit word suffix
    base_for_words = base_slug[:40]  # Leave room for "-" + word (max 10 chars)
    
    for word in word_list:
        handle = f"{base_for_words}-{word}"[:50]
        if not vendor_model.objects.filter(handle=handle).exists():
            return handle
    
    # Step 3: Try base + word + abbreviation (extremely rare - 103 more attempts!)
    abbr = _generate_abbreviation(business_name)
    base_with_word = base_slug[:30]  # Leave room for word + abbr
    
    # Shuffle again for variety
    random.shuffle(word_list)
    
    for word in word_list:
        handle = f"{base_with_word}-{word}-{abbr}"[:50]
        if not vendor_model.objects.filter(handle=handle).exists():
            return handle
    
    # Step 4: Last resort - use vendor ID creatively (NO raw numbers!)
    # Convert vendor ID to word-like format
    if vendor_id:
        # Option 1: Use vendor ID with 'v' prefix (cleaner than raw number)
        handle = f"{base_slug[:45]}-v{vendor_id}"[:50]
        if not vendor_model.objects.filter(handle=handle).exists():
            return handle
        
        # Option 2: Convert ID to Greek letter equivalent
        greek_letters = ['alpha', 'beta', 'gamma', 'delta', 'epsilon', 'zeta', 'eta', 'theta']
        if vendor_id and vendor_id <= len(greek_letters):
            handle = f"{base_slug[:40]}-{greek_letters[vendor_id - 1]}"[:50]
            if not vendor_model.objects.filter(handle=handle).exists():
                return handle
    
    # Step 5: Absolute last resort - timestamp-based word (still no raw numbers!)
    import time
    timestamp_words = ['alpha', 'beta', 'gamma', 'delta', 'omega', 'sigma', 'theta', 'lambda']
    ts_index = int(time.time()) % len(timestamp_words)
    return f"{base_slug[:40]}-{timestamp_words[ts_index]}"[:50]


def validate_handle(handle: str) -> tuple[bool, Optional[str]]:
    """
    Validate a handle for format and length.
    
    Args:
        handle: The handle to validate
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not handle:
        return False, "Handle cannot be empty"
    
    if len(handle) > 50:
        return False, "Handle must be 50 characters or less"
    
    if len(handle) < 3:
        return False, "Handle must be at least 3 characters"
    
    # Check if handle is a valid slug (lowercase alphanumeric and hyphens)
    # ✅ NO NUMBERS CHECK - we allow numbers in slugs, but we don't generate them
    if not re.match(r'^[a-z0-9]+(?:-[a-z0-9]+)*$', handle):
        return False, "Handle can only contain lowercase letters, numbers, and hyphens"
    
    return True, None
