from rest_framework import serializers
from .models import Vendor
from apps.users.serializers import VendorProfileSerializer


class VendorSerializer(serializers.ModelSerializer):
    total_products = serializers.ReadOnlyField()
    average_rating = serializers.ReadOnlyField()

    class Meta:
        model = Vendor
        fields = [
            "id", "business_name", "business_description",
            "business_email", "business_type", "business_phone",
            "gstin", "website", "logo",
            "is_active", "is_verified", 
             "total_products", "average_rating",
            "created_at", "updated_at","is_onboarded"
        ]
        read_only_fields = ["user", "is_verified", "created_at", "updated_at"]


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
