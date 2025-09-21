from rest_framework import serializers
from .models import Vendor
from apps.users.serializers import VendorProfileSerializer,AddressSerializer
from apps.users.models import Address


class VendorSerializer(serializers.ModelSerializer):
    total_products = serializers.ReadOnlyField()
    average_rating = serializers.ReadOnlyField()
    address_details = serializers.SerializerMethodField()  # Custom method to get user's address
    logo_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Vendor
        fields = [
            "id", "business_name", "business_description",
            "business_email", "business_type", "business_phone",
            "gstin", "website", "logo","logo_url",
            "is_active", "is_verified", 
            "total_products", "average_rating",
            "created_at", "updated_at", "is_onboarded", "address_details"
        ]
        read_only_fields = ["user", "is_verified", "created_at", "updated_at","logo_url"]
    
    def get_address_details(self, obj):
        # Get user's default address or first address
        address = obj.user.addresses.filter(is_default=True).first()
        if not address:
            address = obj.user.addresses.first()
        
        if address:
            return AddressSerializer(address).data
        return None
    
    def get_logo_url(self, obj):
        if obj.logo:
            return obj.logo.url  # full Cloudinary URL
        return None


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
    
    # Address fields - all optional
    street = serializers.CharField(write_only=True, required=False)
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
            "street", "city", "state", "zip_code", "country",
            "address_details"
        ]
        read_only_fields = ["user", "is_verified", "created_at", "updated_at"]
    
    def get_address_details(self, obj):
        """Return current address details"""
        address = obj.user.addresses.filter(is_default=True).first()
        if not address:
            address = obj.user.addresses.first()
        
        if address:
            return {
                'street': address.street_address,
                'city': address.city,
                'state': address.state,
                'zip_code': address.zip_code,
                'country': address.country,
                'postal_code': address.postal_code
            }
        return None
    
    def update(self, instance, validated_data):
        # Extract address fields
        address_fields = ['street', 'city', 'state', 'zip_code', 'country']
        address_data = {}
        
        for field in address_fields:
            if field in validated_data:
                value = validated_data.pop(field)
                if field == 'street':
                    address_data['street_address'] = value
                elif field == 'zip_code':
                    address_data['postal_code'] = value
                    address_data['zip_code'] = value
                else:
                    address_data[field] = value
        
        # Update only the vendor fields that were provided
        if 'website' not in validated_data or not validated_data['website']:
            validated_data['website'] = "https://www.google.com"
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
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