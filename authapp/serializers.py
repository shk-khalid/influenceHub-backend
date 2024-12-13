from rest_framework import serializers
from .models import User

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'fullName', 'is_verfied',  'location', 'bio', 'socialLinks']
        
class RegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['email', 'password', 'fullName', 'location', 'bio', 'socialLinks']

    def create(self, validated_data):
        # Ensure the create method returns the created user instance
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            fullName=validated_data['fullName'],
            location=validated_data.get('location', ''),
            bio=validated_data.get('bio', ''),
            socialLinks=validated_data.get('socialLinks', {}),
        )
        return user  # Returning the user instance
    
class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()
    
    
    