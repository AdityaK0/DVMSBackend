"""
Campaign logging service.
Logs WhatsApp campaign attempts (does not send messages).
"""
from apps.events.models import CampaignLog
import logging

logger = logging.getLogger(__name__)


def log_campaign(event, message_text, poster_url, sent_to_phone, status='sent'):
    """
    Log a WhatsApp campaign attempt.
    
    Note: This does NOT send WhatsApp messages.
    Frontend will open: https://wa.me/{phone}?text={encoded_msg}
    
    Args:
        event: Event instance
        message_text: Message text to send
        poster_url: URL of poster (if any)
        sent_to_phone: Phone number to send to
        status: 'sent' or 'failed'
    
    Returns:
        CampaignLog instance
    """
    try:
        campaign_log = CampaignLog.objects.create(
            event=event,
            message_text=message_text,
            poster_url=poster_url,
            sent_to_phone=sent_to_phone,
            status=status
        )
        logger.info(f"Campaign logged for event {event.id} to {sent_to_phone}")
        return campaign_log
    except Exception as e:
        logger.error(f"Error logging campaign: {str(e)}")
        raise


def increment_click_count(campaign_log):
    """
    Increment click count for a campaign log.
    
    Args:
        campaign_log: CampaignLog instance
    """
    campaign_log.click_count += 1
    campaign_log.save(update_fields=['click_count'])


def get_campaign_stats(event):
    """
    Get campaign statistics for an event.
    
    Args:
        event: Event instance
    
    Returns:
        Dict with campaign stats
    """
    logs = CampaignLog.objects.filter(event=event)
    
    return {
        'total_campaigns': logs.count(),
        'sent': logs.filter(status='sent').count(),
        'failed': logs.filter(status='failed').count(),
        'total_clicks': sum(log.click_count for log in logs),
        'unique_recipients': logs.values('sent_to_phone').distinct().count(),
    }

