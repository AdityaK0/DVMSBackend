"""
Serializers for events app.
"""
from rest_framework import serializers
from apps.events.models import Event
from apps.products.models import Product


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









