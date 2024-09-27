from rest_framework import serializers
from .models import DeliveryStaff, Delivery, DeliveryIssue
from decimal import Decimal

class DeliveryStaffSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryStaff
        fields = ['id', 'email', 'password', 'first_name', 'last_name', 'phone_number', 'address', 'email_confirmed', 'gender', 'license_number', 'vehicle_type', 'vehicle_number', 'dob']
        extra_kwargs = {
            'password': {'write_only': True},
            'email_confirmed': {'read_only': True},
            'email': {'required': True}
        }

    def create(self, validated_data):
        user = DeliveryStaff.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            **{k: v for k, v in validated_data.items() if k not in ('email', 'password')}
        )
        return user

class LocationSerializer(serializers.Serializer):
    address = serializers.CharField(max_length=255)
    lat = serializers.CharField(max_length=20)
    lon = serializers.CharField(max_length=20)

    # Remove the to_internal_value method

class DeliverySerializer(serializers.ModelSerializer):
    pickup_location = LocationSerializer()
    dropoff_location = LocationSerializer()

    class Meta:
        model = Delivery
        fields = '__all__'

    def create(self, validated_data):
        pickup_location = validated_data.pop('pickup_location')
        dropoff_location = validated_data.pop('dropoff_location')
        delivery = Delivery.objects.create(
            pickup_location=pickup_location,
            dropoff_location=dropoff_location,
            **validated_data
        )
        return delivery

    def update(self, instance, validated_data):
        pickup_location = validated_data.pop('pickup_location', None)
        dropoff_location = validated_data.pop('dropoff_location', None)
        
        if pickup_location:
            instance.pickup_location.update(pickup_location)
        if dropoff_location:
            instance.dropoff_location.update(dropoff_location)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.save()
        return instance

    def validate(self, data):
        for location_type in ['pickup_location', 'dropoff_location']:
            location = data.get(location_type)
            if location:
                if not all(key in location for key in ['address', 'lat', 'lon']):
                    raise serializers.ValidationError(f"{location_type} must contain 'address', 'lat', and 'lon'.")
        return data

class DeliveryIssueSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryIssue
        fields = '__all__'