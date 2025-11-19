from django.test import TestCase
from apps.users.serializers import UserRegistrationSerializer
from apps.users.models import User

class UserRegistrationValidationTests(TestCase):
    def setUp(self):
        self.valid_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User',
            'phone_number': '1234567890',
            'role': 'customer',
            'password': 'password123',
            'password_confirm': 'password123'
        }

    def test_valid_registration(self):
        serializer = UserRegistrationSerializer(data=self.valid_data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        user = serializer.save()
        self.assertEqual(user.username, 'testuser')

    def test_duplicate_email(self):
        User.objects.create_user(username='other', email='test@example.com', password='password')
        serializer = UserRegistrationSerializer(data=self.valid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('email', serializer.errors)
        # DRF default message or my custom message if it runs. 
        # Since default runs first, it might be "user with this email already exists." or similar.
        # Let's just check that we have an error.
        self.assertTrue(len(serializer.errors['email']) > 0)

    def test_duplicate_username(self):
        User.objects.create_user(username='testuser', email='other@example.com', password='password')
        serializer = UserRegistrationSerializer(data=self.valid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('username', serializer.errors)
        # Default DRF message is "A user with that username already exists."
        self.assertEqual(str(serializer.errors['username'][0]), "A user with that username already exists.")

    def test_invalid_phone_digits(self):
        data = self.valid_data.copy()
        data['phone_number'] = '12345abcde'
        serializer = UserRegistrationSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('phone_number', serializer.errors)
        self.assertEqual(str(serializer.errors['phone_number'][0]), "Phone number must contain only digits.")

    def test_invalid_phone_length(self):
        data = self.valid_data.copy()
        data['phone_number'] = '123'
        serializer = UserRegistrationSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('phone_number', serializer.errors)
        self.assertEqual(str(serializer.errors['phone_number'][0]), "Phone number must be between 10 and 15 digits.")

    def test_admin_role_registration(self):
        data = self.valid_data.copy()
        data['role'] = 'admin'
        serializer = UserRegistrationSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('role', serializer.errors)
        self.assertEqual(str(serializer.errors['role'][0]), "You cannot register as admin.")

    def test_password_mismatch(self):
        data = self.valid_data.copy()
        data['password_confirm'] = 'mismatch'
        serializer = UserRegistrationSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('non_field_errors', serializer.errors)
        self.assertEqual(str(serializer.errors['non_field_errors'][0]), "Passwords don't match")
