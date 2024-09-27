from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
import uuid
from django.utils import timezone

class DeliveryStaffManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        return self.create_user(email, password, **extra_fields)

class DeliveryStaff(AbstractUser):
    username = None  # Remove username field
    email = models.EmailField(unique=True)  # Make email unique
    phone_number = models.CharField(max_length=15, default='')
    address = models.TextField(default='')
    email_confirmed = models.BooleanField(default=False)
    confirmation_token = models.UUIDField(default=uuid.uuid4, editable=False)
    gender = models.CharField(max_length=10, choices=[('male', 'Male'), ('female', 'Female'), ('other', 'Other')], default='other')
    license_number = models.CharField(max_length=50, default='')
    vehicle_type = models.CharField(max_length=50, default='')
    vehicle_number = models.CharField(max_length=20, default='')
    dob = models.DateField(default=timezone.now)

    objects = DeliveryStaffManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

class Delivery(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('picked_up', 'Picked Up'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )

    delivery_staff = models.ForeignKey(DeliveryStaff, on_delete=models.CASCADE, null=True, blank=True)
    pickup_location = models.JSONField()
    dropoff_location = models.JSONField()
    pickup_time = models.DateTimeField()
    blood_type = models.CharField(max_length=10)
    blood_units = models.PositiveIntegerField(default=1)  # Add this line
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    qr_code = models.CharField(max_length=100, unique=True)

class DeliveryIssue(models.Model):
    delivery = models.ForeignKey(Delivery, on_delete=models.CASCADE)
    description = models.TextField()
    photo = models.ImageField(upload_to='issue_photos/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)