from rest_framework import serializers
from django.contrib.auth import authenticate
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import User, Address, CustomerProfile, VendorProfile
from ..vendors.models import Vendor
from apps.vendors.serializers import VendorSerializer

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'phone_number', 
                 'role', 'password', 'password_confirm']

    def validate(self, attrs):
        password = attrs.get('password')
        password_confirm = attrs.get('password_confirm')

        if not password or not password_confirm:
            raise serializers.ValidationError("Both password and password_confirm are required")

        if len(password) < 6 or len(password_confirm) < 6:
            raise serializers.ValidationError("Password length must be at least 6 characters")
        
        if password != password_confirm:
            raise serializers.ValidationError("Passwords don't match")
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        user = User.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()
        
        if user.role == 'customer':
            CustomerProfile.objects.create(user=user)
        elif user.role == 'vendor':
            vendor = Vendor.objects.create(user=user, business_name=f"{user.first_name}'s Business")
            VendorProfile.objects.create(vendor=vendor)
        return user

class UserLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()

    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')

        if username and password:
            user = authenticate(username=username, password=password)
            if not user:
                raise serializers.ValidationError('Invalid credentials')
            if not user.is_active:
                raise serializers.ValidationError('User account is disabled')
            attrs['user'] = user
        else:
            raise serializers.ValidationError('Must include username and password')
        
        return attrs

class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = '__all__'
        read_only_fields = ['user']

class CustomerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerProfile
        fields = '__all__'
        read_only_fields = ['user']

        
class UserSerializer(serializers.ModelSerializer):
    vendor_profile = VendorSerializer(source="vendor", read_only=True)
    addresses = AddressSerializer(many=True, read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 
                 'phone_number', 'role', 'is_verified', 'created_at', 'vendor_profile', 'addresses']
        read_only_fields = ['id', 'created_at', 'is_verified']


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating non-sensitive user profile information.
    """
    class Meta:
        model = User
        fields = [
            'first_name',
            'last_name',
            'phone_number'
        ]
        # def update(self, instance, validated_data):
        #     # Example of a bug where first_name is not handled correctly
        #     # This is just an illustration; your code may look different
        #     instance.first_name = validated_data.get('first_name', instance.first_name)
        #     instance.last_name = validated_data.get('last_name', instance.last_name)
        #     instance.phone_number = validated_data.get('phone_number', instance.phone_number)
            
        #     # If first_name handling is missing or buggy
        #     # validated_data.get('first_name', instance.first_name) might resolve to an empty string incorrectly
        #     instance.save()
        #     return instance


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom JWT serializer that adds vendor_id claim for security validation.
    This prevents JWT token manipulation attacks.
    """
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        
        # Add custom claims for validation
        token['username'] = user.username
        token['role'] = user.role
        token['email'] = user.email
        
        # Add vendor ID if user is a vendor
        if hasattr(user, 'vendor') and user.vendor:
            token['vendor_id'] = user.vendor.id
        else:
            token['vendor_id'] = None
        
        return token