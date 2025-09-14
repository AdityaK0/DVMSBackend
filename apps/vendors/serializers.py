from rest_framework import serializers
from .models import Vendor
from apps.users.serializers import VendorProfileSerializer,AddressSerializer


class VendorSerializer(serializers.ModelSerializer):
    total_products = serializers.ReadOnlyField()
    average_rating = serializers.ReadOnlyField()
    address_details = serializers.SerializerMethodField()  # Custom method to get user's address
    
    class Meta:
        model = Vendor
        fields = [
            "id", "business_name", "business_description",
            "business_email", "business_type", "business_phone",
            "gstin", "website", "logo",
            "is_active", "is_verified", 
            "total_products", "average_rating",
            "created_at", "updated_at", "is_onboarded", "address_details"
        ]
        read_only_fields = ["user", "is_verified", "created_at", "updated_at"]
    
    def get_address_details(self, obj):
        # Get user's default address or first address
        address = obj.user.addresses.filter(is_default=True).first()
        if not address:
            address = obj.user.addresses.first()
        
        if address:
            return AddressSerializer(address).data
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
