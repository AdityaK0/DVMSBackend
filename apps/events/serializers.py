"""
Serializers for events app.
"""
from rest_framework import serializers
from apps.events.models import Event, CampaignLog, EventAnalytics
from apps.products.models import Product
from apps.vendors.models import Vendor


class EventSerializer(serializers.ModelSerializer):
    """Main serializer for Event model - used for read operations"""
    vendor_name = serializers.CharField(source='vendor.business_name', read_only=True)
    
    class Meta:
        model = Event
        fields = [
            'id', 'vendor', 'vendor_name', 'name', 'description',
            'start_date', 'end_date', 'status', 'festival_template_id',
            'poster_url', 'custom_message', 'selected_products',
            'is_deleted', 'deleted_at', 'created_at', 'updated_at'
        ]
        read_only_fields = ['vendor', 'created_at', 'updated_at', 'is_deleted', 'deleted_at']


class EventCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating events"""
    
    class Meta:
        model = Event
        fields = [
            'name', 'description', 'start_date', 'end_date',
            'status', 'festival_template_id', 'custom_message',
            'selected_products'
        ]
    
    def validate(self, attrs):
        """Validate that start_date is before end_date"""
        start_date = attrs.get('start_date')
        end_date = attrs.get('end_date')
        
        if start_date and end_date:
            if start_date >= end_date:
                raise serializers.ValidationError({
                    'end_date': 'End date must be after start date.'
                })
        
        # Validate status
        status = attrs.get('status', 'draft')
        valid_statuses = ['draft', 'scheduled', 'active', 'completed', 'cancelled']
        if status not in valid_statuses:
            raise serializers.ValidationError({
                'status': f'Status must be one of: {", ".join(valid_statuses)}'
            })
        
        return attrs
    
    def validate_selected_products(self, value):
        """Validate that selected products exist and belong to vendor"""
        if not value:
            return value
        
        request = self.context.get('request')
        if not request or not hasattr(request.user, 'vendor'):
            return value
        
        vendor = request.user.vendor
        product_ids = value
        
        # Check if all products exist and belong to vendor
        products = Product.objects.filter(
            id__in=product_ids,
            vendor=vendor,
            is_active=True
        )
        
        if products.count() != len(product_ids):
            raise serializers.ValidationError(
                'Some selected products do not exist or do not belong to your vendor account.'
            )
        
        return value


class EventUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating events"""
    
    class Meta:
        model = Event
        fields = [
            'name', 'description', 'start_date', 'end_date',
            'status', 'festival_template_id', 'custom_message',
            'selected_products'
        ]
    
    def validate(self, attrs):
        """Validate that start_date is before end_date"""
        # Get existing instance values if not provided
        start_date = attrs.get('start_date', self.instance.start_date if self.instance else None)
        end_date = attrs.get('end_date', self.instance.end_date if self.instance else None)
        
        if start_date and end_date:
            if start_date >= end_date:
                raise serializers.ValidationError({
                    'end_date': 'End date must be after start date.'
                })
        
        # Validate status
        status = attrs.get('status')
        if status:
            valid_statuses = ['draft', 'scheduled', 'active', 'completed', 'cancelled']
            if status not in valid_statuses:
                raise serializers.ValidationError({
                    'status': f'Status must be one of: {", ".join(valid_statuses)}'
                })
        
        return attrs
    
    def validate_selected_products(self, value):
        """Validate that selected products exist and belong to vendor"""
        if value is None:
            return value
        
        request = self.context.get('request')
        if not request or not hasattr(request.user, 'vendor'):
            return value
        
        vendor = request.user.vendor
        product_ids = value
        
        # Check if all products exist and belong to vendor
        products = Product.objects.filter(
            id__in=product_ids,
            vendor=vendor,
            is_active=True
        )
        
        if products.count() != len(product_ids):
            raise serializers.ValidationError(
                'Some selected products do not exist or do not belong to your vendor account.'
            )
        
        return value


class FestivalTemplateSerializer(serializers.Serializer):
    """Serializer for festival templates (static data)"""
    id = serializers.CharField()
    name = serializers.CharField()
    preset_message = serializers.CharField()
    preset_colors = serializers.DictField()
    preset_date_range = serializers.DictField()
    background = serializers.CharField()
    hashtags = serializers.ListField(child=serializers.CharField())
    recommended_products = serializers.IntegerField()


class PosterGenerationSerializer(serializers.Serializer):
    """Serializer for poster generation request"""
    template_id = serializers.CharField(required=True)
    selected_products = serializers.ListField(
        child=serializers.IntegerField(),
        required=True,
        allow_empty=False
    )
    custom_message = serializers.CharField(required=False, allow_blank=True)


class PosterResponseSerializer(serializers.Serializer):
    """Serializer for poster generation response"""
    poster_url = serializers.URLField()


class ProductRecommendationSerializer(serializers.Serializer):
    """Serializer for product recommendations"""
    id = serializers.IntegerField()
    name = serializers.CharField()
    price = serializers.DecimalField(max_digits=10, decimal_places=2)
    image = serializers.URLField(allow_null=True)
    is_in_stock = serializers.BooleanField()
    stock_quantity = serializers.IntegerField()
    is_featured = serializers.BooleanField()


class CampaignLogSerializer(serializers.ModelSerializer):
    """Serializer for campaign logs"""
    event_title = serializers.CharField(source='event.name', read_only=True)
    
    class Meta:
        model = CampaignLog
        fields = [
            'id', 'event', 'event_title', 'message_text', 'poster_url',
            'sent_to_phone', 'status', 'click_count', 'created_at'
        ]
        read_only_fields = ['created_at']


class CampaignLogCreateSerializer(serializers.Serializer):
    """Serializer for creating campaign logs"""
    message_text = serializers.CharField(required=True)
    poster_url = serializers.URLField(required=False, allow_blank=True)
    sent_to_phone = serializers.CharField(required=True, max_length=20)
    status = serializers.ChoiceField(
        choices=['sent', 'failed'],
        default='sent',
        required=False
    )


class AnalyticsSerializer(serializers.ModelSerializer):
    """Serializer for event analytics"""
    event_title = serializers.CharField(source='event.name', read_only=True)
    
    class Meta:
        model = EventAnalytics
        fields = [
            'id', 'event', 'event_title', 'date', 'views', 'clicks',
            'shares', 'leads', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class AnalyticsUpdateSerializer(serializers.Serializer):
    """Serializer for updating analytics"""
    date = serializers.DateField(required=True)
    views = serializers.IntegerField(required=False, min_value=0, default=0)
    clicks = serializers.IntegerField(required=False, min_value=0, default=0)
    shares = serializers.IntegerField(required=False, min_value=0, default=0)
    leads = serializers.IntegerField(required=False, min_value=0, default=0)

