from rest_framework import serializers
from .models import Vendor
from apps.users.models import Address
from django.utils.text import slugify
from apps.portfolio.models import Portfolio
from ..utils.update_things import update_portfolio_url
import re
from .models import Event, PosterTemplate


class VendorSerializer(serializers.ModelSerializer):
    total_products = serializers.ReadOnlyField()
    average_rating = serializers.ReadOnlyField()
    address_details = serializers.SerializerMethodField()  # Custom method to get user's address
    # logo_url = serializers.SerializerMethodField()
    # telegram_link_valid = serializers.SerializerMethodField()
    
    class Meta:
        model = Vendor
        fields = [
            "id", "business_name", "business_description",
            "business_email", "business_type", "business_phone","business_name_slug",
            "gstin", "website", "logo",
            "is_active", "is_verified", 
            "total_products", "average_rating","whatsapp_number",
            "created_at", "updated_at", "is_onboarded", "address_details","secret","telegram_chat_id"
        ]
        read_only_fields = ["user", "is_verified", "created_at", "updated_at","logo_url","telegram_chat_id","secret"]
    
    def get_address_details(self, obj):
        # Get user's default address or first address
        from apps.users.serializers import AddressSerializer
        address = obj.user.addresses.filter(is_default=True).first()
        if not address:
            address = obj.user.addresses.first()
        
        if address:
            return AddressSerializer(address).data
        return None
    
    # def get_logo_url(self, obj):
    #     if obj.logo:
    #         return obj.logo
    #     return None
    
    # def get_telegram_link_valid(self, obj):
    #     """
    #     Returns True if vendor has valid Telegram link (chat_id exists & bot not blocked).
    #     """
    #     return is_telegram_chat_active(obj.telegram_chat_id)

class VendorListSerializer(serializers.ModelSerializer):
    total_products = serializers.ReadOnlyField()
    average_rating = serializers.ReadOnlyField()

    class Meta:
        model = Vendor
        fields = [
            "id", "business_name", "business_description",
            "logo", "is_active", "is_verified",
            "total_products", "average_rating"
        ]

class VendorUpdate(serializers.ModelSerializer):
    # All vendor fields are optional for updates
    business_name = serializers.CharField(required=False)
    business_description = serializers.CharField(required=False)
    business_type = serializers.CharField(required=False)
    website = serializers.URLField(required=False, allow_blank=True, default="https://www.google.com")
    logo = serializers.ImageField(required=False)
    gstin = serializers.CharField(required=False)
    whatsapp_number = serializers.CharField(required=False)
    business_phone = serializers.CharField(required=False)

    
    # Address fields - all optional
    street_address = serializers.CharField(write_only=True, required=False)
    city = serializers.CharField(write_only=True, required=False)
    state = serializers.CharField(write_only=True, required=False)
    zip_code = serializers.CharField(write_only=True, required=False)
    country = serializers.CharField(write_only=True, required=False)
    
    # Include address_details for response
    address_details = serializers.SerializerMethodField()
    
    class Meta:
        model = Vendor
        fields = [
            "business_name", "business_description", "business_type",
            "website", "logo", "gstin",
            "street_address", "city", "state", "zip_code", "country","business_phone",
            "address_details","whatsapp_number",
        ]
        read_only_fields = ["user", "is_verified", "created_at", "updated_at"]
    
    def get_address_details(self, obj):
        """Return current address details"""
        address = obj.user.addresses.filter(is_default=True).first()
        if not address:
            address = obj.user.addresses.first()
        
        if address:
            return {
                'street_address': address.street_address,
                'city': address.city,
                'state': address.state,
                'zip_code': address.zip_code,
                'country': address.country,
                'postal_code': address.postal_code
            }
        return None
    
    def update(self, instance, validated_data):
        # Extract address fields
        address_fields = ['street_address', 'city', 'state', 'zip_code', 'country']
        address_data = {}
        
        for field in address_fields:
            if field in validated_data:
                value = validated_data.pop(field)
                if field == 'street_address':
                    address_data['street_address'] = value
                elif field == 'zip_code':
                    address_data['postal_code'] = value
                    address_data['zip_code'] = value
                else:
                    address_data[field] = value
                    
        old_name = instance.business_name
        new_name = validated_data.get("business_name", old_name)            
        
        # Update only the vendor fields that were provided
        if 'website' not in validated_data or not validated_data['website']:
            validated_data['website'] = "https://www.google.com"
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        if new_name != old_name:
            new_slug = f"{slugify(new_name)}-{instance.id}"
            instance.business_name_slug = new_slug
            
            # FIXED: Avoid DoesNotExist crash by get_or_create
            portfolio, _ = Portfolio.objects.get_or_create(vendor=instance)
            update_portfolio_url(portfolio, new_slug)
        instance.save()
        

        
        # Update address only if address data is provided
        if address_data:
            # Get user's default address or first address
            address = instance.user.addresses.filter(is_default=True).first()
            if not address:
                address = instance.user.addresses.first()
            
            if address:
                # Update only the address fields that were provided
                for attr, value in address_data.items():
                    setattr(address, attr, value)
                address.save()
            else:
                # Create new address if none exists (edge case)
                Address.objects.create(
                    user=instance.user,
                    address_type='both',
                    is_default=True,
                    **address_data
                )
        
        return instance
    
    def validate_business_name(self, value):
        slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")

        if len(slug) > 50:
            raise serializers.ValidationError("Business name is too long. Choose a shorter name.")

        if not re.match(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", slug):
            raise serializers.ValidationError("Only letters, numbers and hyphens allowed.")

        return value

    def validate_business_phone(self, value):
        # Basic validation: 10 to 15 digits, optional leading +
        if value and not re.match(r'^\+?\d{10,15}$', value):
            raise serializers.ValidationError("Enter a valid phone number (10-15 digits).")
        return value
    
    


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = "__all__"


class PosterTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PosterTemplate
        fields = "__all__"
