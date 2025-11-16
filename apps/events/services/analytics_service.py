"""
Event analytics service.
Tracks views, clicks, shares, and leads for events.
"""
from apps.events.models import EventAnalytics
from django.utils import timezone
from datetime import date
import logging

logger = logging.getLogger(__name__)


def get_or_create_analytics(event, analytics_date=None):
    """
    Get or create analytics entry for an event on a specific date.
    
    Args:
        event: Event instance
        analytics_date: Date object (defaults to today)
    
    Returns:
        EventAnalytics instance
    """
    if analytics_date is None:
        analytics_date = timezone.now().date()
    
    analytics, created = EventAnalytics.objects.get_or_create(
        event=event,
        date=analytics_date,
        defaults={
            'views': 0,
            'clicks': 0,
            'shares': 0,
            'leads': 0,
        }
    )
    return analytics


def increment_views(event, analytics_date=None):
    """
    Increment view count for an event.
    
    Args:
        event: Event instance
        analytics_date: Date object (defaults to today)
    """
    analytics = get_or_create_analytics(event, analytics_date)
    analytics.views += 1
    analytics.save(update_fields=['views', 'updated_at'])


def increment_clicks(event, analytics_date=None):
    """
    Increment click count for an event.
    
    Args:
        event: Event instance
        analytics_date: Date object (defaults to today)
    """
    analytics = get_or_create_analytics(event, analytics_date)
    analytics.clicks += 1
    analytics.save(update_fields=['clicks', 'updated_at'])


def increment_shares(event, analytics_date=None):
    """
    Increment share count for an event.
    
    Args:
        event: Event instance
        analytics_date: Date object (defaults to today)
    """
    analytics = get_or_create_analytics(event, analytics_date)
    analytics.shares += 1
    analytics.save(update_fields=['shares', 'updated_at'])


def increment_leads(event, analytics_date=None):
    """
    Increment lead count for an event.
    
    Args:
        event: Event instance
        analytics_date: Date object (defaults to today)
    """
    analytics = get_or_create_analytics(event, analytics_date)
    analytics.leads += 1
    analytics.save(update_fields=['leads', 'updated_at'])


def get_analytics_summary(event, days=30):
    """
    Get analytics summary for an event over a period.
    
    Args:
        event: Event instance
        days: Number of days to look back
    
    Returns:
        Dict with aggregated analytics
    """
    from django.utils import timezone
    from datetime import timedelta
    
    start_date = timezone.now().date() - timedelta(days=days)
    
    analytics = EventAnalytics.objects.filter(
        event=event,
        date__gte=start_date
    )
    
    return {
        'total_views': sum(a.views for a in analytics),
        'total_clicks': sum(a.clicks for a in analytics),
        'total_shares': sum(a.shares for a in analytics),
        'total_leads': sum(a.leads for a in analytics),
        'daily_breakdown': [
            {
                'date': str(a.date),
                'views': a.views,
                'clicks': a.clicks,
                'shares': a.shares,
                'leads': a.leads,
            }
            for a in analytics.order_by('-date')
        ]
    }


def update_analytics(event, analytics_date, views=None, clicks=None, shares=None, leads=None):
    """
    Update analytics for an event on a specific date.
    Used by frontend to send analytics events.
    
    Args:
        event: Event instance
        analytics_date: Date object
        views: Views to add (optional)
        clicks: Clicks to add (optional)
        shares: Shares to add (optional)
        leads: Leads to add (optional)
    """
    analytics = get_or_create_analytics(event, analytics_date)
    
    if views is not None:
        analytics.views += views
    if clicks is not None:
        analytics.clicks += clicks
    if shares is not None:
        analytics.shares += shares
    if leads is not None:
        analytics.leads += leads
    
    analytics.save()

