from rest_framework import serializers
from .models import Vendor
from apps.users.models import Address
from django.utils.text import slugify
from apps.portfolio.models import Portfolio
import re
from .models import Event, PosterTemplate
from django.db import transaction


class VendorSerializer(serializers.ModelSerializer):
    # total_products = serializers.ReadOnlyField()
    # average_rating = serializers.ReadOnlyField()
    address_details = serializers.SerializerMethodField()  # Custom method to get user's address
    # logo_url = serializers.SerializerMethodField()
    # telegram_link_valid = serializers.SerializerMethodField()
    
    class Meta:
        model = Vendor
        fields = [
            "id", "business_name", "business_description",
            "business_email", "business_type", "business_phone", "handle",
            "gstin", "website", "logo",
            "is_active", "is_verified", "whatsapp_number",
            "created_at", "updated_at", "is_onboarded", "address_details", "secret", "telegram_chat_id",
            "handle"  # ✅ Permanent portfolio URL handle
        ]
        read_only_fields = ["user", "is_verified", "created_at", "updated_at", "logo_url", "telegram_chat_id", "secret", "handle"]
    
    
    
    def get_address_details(self, obj):
        from apps.users.serializers import AddressSerializer

        addresses = obj.user.addresses.all()  # uses prefetch, 0 DB hits

        if not addresses:
            return None

        default_address = next((a for a in addresses if a.is_default), None)
        default_address = default_address or addresses[0]

        return AddressSerializer(default_address).data
        

    # def get_address_details(self, obj):
    #     from apps.users.serializers import AddressSerializer
    #     addresses = getattr(obj.user, "addresses", []).all()

    #     default_address = next((addr for addr in addresses if addr.is_default), None)

    #     if not default_address and addresses:
    #         default_address = addresses[0]

    #     if default_address:
    #         return AddressSerializer(default_address).data

    #     return None


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
        """
        Atomic vendor update with address syncing.
        
        IMPORTANT: Business name CANNOT be changed after onboarding
        to maintain stable portfolio URLs and handles.
        """
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

        # ✅ PREVENT business name changes after onboarding
        # This ensures stable portfolio URLs and handles
        if 'business_name' in validated_data:
            if instance.is_onboarded and validated_data['business_name'] != instance.business_name:
                raise serializers.ValidationError({
                    "business_name": "Business name cannot be changed after onboarding. "
                                   "This ensures your portfolio URL remains stable. "
                                   "Contact admin if you need to update it."
                })

        if 'website' not in validated_data or not validated_data['website']:
            validated_data['website'] = "https://www.google.com"

        with transaction.atomic():
            for attr, value in validated_data.items():
                setattr(instance, attr, value)

            instance.save()

            if address_data:
                address = instance.user.addresses.filter(is_default=True).first() or instance.user.addresses.first()
                if address:
                    for attr, value in address_data.items():
                        setattr(address, attr, value)
                    address.save()
                else:
                    Address.objects.create(
                        user=instance.user,
                        address_type='both',
                        is_default=True,
                        **address_data
                    )

        return instance
    
    def validate_business_name(self, value):
        """
        Validate business name format.
        
        Note: This only validates format. The update() method prevents
        changes to business_name after onboarding.
        """
        slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")

        if len(slug) > 50:
            raise serializers.ValidationError("Business name is too long. Choose a shorter name.")

        if not re.match(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", slug):
            raise serializers.ValidationError("Only letters, numbers and hyphens allowed.")

        return value

    def validate_business_phone(self, value):
        # Basic validation: 10 to 15 digits, optional leading +

        if value and Vendor.objects.exclude(id=self.instance.id).filter(business_phone=value).exists():
            raise serializers.ValidationError("This business phone is already registered.")
        
        if value and not re.match(r'^\+?\d{10,15}$', value):
            raise serializers.ValidationError("Enter a valid phone number (10-15 digits).")
        return value

    def validate_zip_code(self, value):
        # Basic validation: 5 to 10 alphanumeric characters
        if value and not re.match(r'^[a-zA-Z0-9\s-]{5,10}$', value):
             raise serializers.ValidationError("Enter a valid zip/postal code.")
        return value


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = "__all__"


class PosterTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PosterTemplate
        fields = "__all__"
