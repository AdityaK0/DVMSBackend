"""
Static festival template data.
No database needed - this is a static dataset.
"""

FESTIVAL_TEMPLATES = [
    {
        "id": "diwali",
        "name": "Diwali Festival",
        "preset_message": "🎉 Celebrate Diwali with amazing deals! Shop now and light up your celebrations with exclusive offers. 🪔✨",
        "preset_colors": {
            "primary": "#F97316",
            "secondary": "#FFA500",
            "accent": "#FFD700"
        },
        "preset_date_range": {
            "start": "2024-11-01",
            "end": "2024-11-15"
        },
        "background": "/static/festivals/diwali.png",
        "hashtags": ["#DiwaliSale", "#FestivalOffers", "#Diwali2024", "#ShopNow"],
        "recommended_products": 4
    },
    {
        "id": "holi",
        "name": "Holi Festival",
        "preset_message": "🌈 Celebrate Holi with vibrant colors and exciting offers! Add more colors to your celebrations. 🎨🎉",
        "preset_colors": {
            "primary": "#FF6B6B",
            "secondary": "#4ECDC4",
            "accent": "#FFE66D"
        },
        "preset_date_range": {
            "start": "2024-03-20",
            "end": "2024-03-30"
        },
        "background": "/static/festivals/holi.png",
        "hashtags": ["#HoliSale", "#ColorfulFestival", "#Holi2024", "#FestivalDeals"],
        "recommended_products": 4
    },
    {
        "id": "dussehra",
        "name": "Dussehra Festival",
        "preset_message": "🎯 Celebrate Dussehra with special offers! Victory of good over evil, and great deals for you! 🏹",
        "preset_colors": {
            "primary": "#8B4513",
            "secondary": "#FF4500",
            "accent": "#FFD700"
        },
        "preset_date_range": {
            "start": "2024-10-10",
            "end": "2024-10-20"
        },
        "background": "/static/festivals/dussehra.png",
        "hashtags": ["#DussehraSale", "#VictoryFestival", "#Dussehra2024", "#SpecialOffers"],
        "recommended_products": 4
    },
    {
        "id": "christmas",
        "name": "Christmas Festival",
        "preset_message": "🎄 Merry Christmas! Spread joy with our special Christmas offers. Perfect gifts for your loved ones! 🎁",
        "preset_colors": {
            "primary": "#DC143C",
            "secondary": "#228B22",
            "accent": "#FFD700"
        },
        "preset_date_range": {
            "start": "2024-12-20",
            "end": "2025-01-05"
        },
        "background": "/static/festivals/christmas.png",
        "hashtags": ["#ChristmasSale", "#MerryChristmas", "#HolidayDeals", "#GiftIdeas"],
        "recommended_products": 4
    },
    {
        "id": "new_year",
        "name": "New Year Festival",
        "preset_message": "🎊 Happy New Year! Start the year with amazing deals and fresh beginnings! 🎉✨",
        "preset_colors": {
            "primary": "#000000",
            "secondary": "#FFD700",
            "accent": "#FFFFFF"
        },
        "preset_date_range": {
            "start": "2024-12-28",
            "end": "2025-01-10"
        },
        "background": "/static/festivals/newyear.png",
        "hashtags": ["#NewYearSale", "#HappyNewYear", "#NewBeginnings", "#NewYear2025"],
        "recommended_products": 4
    },
    {
        "id": "eid",
        "name": "Eid Festival",
        "preset_message": "🌙 Eid Mubarak! Celebrate with special offers and make this Eid memorable! 🕌✨",
        "preset_colors": {
            "primary": "#228B22",
            "secondary": "#FFD700",
            "accent": "#FFFFFF"
        },
        "preset_date_range": {
            "start": "2024-04-10",
            "end": "2024-04-20"
        },
        "background": "/static/festivals/eid.png",
        "hashtags": ["#EidSale", "#EidMubarak", "#FestivalOffers", "#Eid2024"],
        "recommended_products": 4
    },
    {
        "id": "independence_day",
        "name": "Independence Day",
        "preset_message": "🇮🇳 Celebrate Independence Day with pride and special offers! Jai Hind! 🎉",
        "preset_colors": {
            "primary": "#FF9933",
            "secondary": "#FFFFFF",
            "accent": "#138808"
        },
        "preset_date_range": {
            "start": "2024-08-10",
            "end": "2024-08-20"
        },
        "background": "/static/festivals/independence.png",
        "hashtags": ["#IndependenceDay", "#JaiHind", "#PatrioticSale", "#Independence2024"],
        "recommended_products": 4
    },
    {
        "id": "republic_day",
        "name": "Republic Day",
        "preset_message": "🇮🇳 Celebrate Republic Day with special offers! Unity in diversity, deals for everyone! 🎉",
        "preset_colors": {
            "primary": "#FF9933",
            "secondary": "#FFFFFF",
            "accent": "#138808"
        },
        "preset_date_range": {
            "start": "2024-01-20",
            "end": "2024-01-30"
        },
        "background": "/static/festivals/republic.png",
        "hashtags": ["#RepublicDay", "#JaiHind", "#PatrioticSale", "#Republic2024"],
        "recommended_products": 4
    },
    {
        "id": "valentines",
        "name": "Valentine's Day",
        "preset_message": "💕 Valentine's Day Special! Show your love with perfect gifts and amazing deals! ❤️",
        "preset_colors": {
            "primary": "#FF1493",
            "secondary": "#FF69B4",
            "accent": "#FFB6C1"
        },
        "preset_date_range": {
            "start": "2024-02-10",
            "end": "2024-02-20"
        },
        "background": "/static/festivals/valentines.png",
        "hashtags": ["#ValentinesDay", "#Love", "#ValentinesSale", "#GiftIdeas"],
        "recommended_products": 4
    },
    {
        "id": "summer_sale",
        "name": "Summer Sale",
        "preset_message": "☀️ Beat the heat with our Summer Sale! Cool deals for hot days! 🏖️",
        "preset_colors": {
            "primary": "#FFA500",
            "secondary": "#87CEEB",
            "accent": "#FFD700"
        },
        "preset_date_range": {
            "start": "2024-05-01",
            "end": "2024-06-30"
        },
        "background": "/static/festivals/summer.png",
        "hashtags": ["#SummerSale", "#BeatTheHeat", "#SummerDeals", "#Summer2024"],
        "recommended_products": 4
    }
]


def get_festival_template(template_id):
    """Get a festival template by ID"""
    for template in FESTIVAL_TEMPLATES:
        if template["id"] == template_id:
            return template
    return None


def get_all_festival_templates():
    """Get all festival templates"""
    return FESTIVAL_TEMPLATES

