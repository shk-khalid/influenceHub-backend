from rest_framework import serializers
from .models import User


class UserSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'fullName', 'location', 'bio', 'socialLinks', 'profilePicture']

        
class RegistrationSerializer(serializers.ModelSerializer):
    password_confirmation = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password_confirmation']

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirmation']:
            raise serializers.ValidationError("Password must watch.")
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirmation')
        user = User.objects.create_user(**validated_data)
        return user

    
class LoginSerializer(serializers.Serializer):
    email_or_username = serializers.CharField()
    password = serializers.CharField()
    
    def validate(self, attrs):
        username_or_email = attrs.get('email_or_username')
        password = attrs.get('password')
        
        if '@' in username_or_email:
            user = User.objects.filter(email=username_or_email).first()
        else:
            user = User.objects.filter(username=username_or_email).first()
            
        if not user:
            raise serializers.ValidationError('Invalid credentials')
        
        if not user.check_password(password):
            raise serializers.ValidationError('Invalid credentials')
        
        attrs['user'] = user 
        return attrs


class ProfileUpdateSerializer(serializers.ModelSerializer):

    class Meta: 
        model = User 
        fields = ['fullName', 'location', 'bio', 'socialLinks', 'profilePicture', 'niche', 'languages', 'collaborate', 'is_admin_verified']

    def validate_languages(self, value):
        valid_languages = {'English', 'Spanish', 'French', 'German', 'Italian', 'Portuguese',
                           'Chinese', 'Japanese', 'Korean', 'Russian', 'Arabic', 'Hindi'}
        valid_levels = {'Native', 'Fluent', 'Advanced', 'Intermediate', 'Basic'}
        
        for lang in value:
            if lang['language'] not in valid_languages:
                raise serializers.ValidationError("Invalid language: {}. Must be one of {}.".format(lang['language'], ', '.join(valid_languages)))
            if lang['level'] not in valid_levels:
                raise serializers.ValidationError("Invalid level for {}: {}. Must be one of {}.".format(lang['language'], lang['level'], ', '.join(valid_levels)))
        
        return value

    def update(self, instance, validated_data):
        for field, value in validated_data.items():
            setattr(instance, field, value)
        
        if 'profilePicture' in validated_data:
            instance.profilePicture = validated_data.get('profilePicture')  
              
        instance.save() 
        return instance
