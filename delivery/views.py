from django.db.models import Q
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import DeliveryStaff, Delivery, DeliveryIssue
from .serializers import DeliveryStaffSerializer, DeliverySerializer, DeliveryIssueSerializer
from django.contrib.auth import get_user_model, authenticate
from django.core.mail import send_mail
from django.conf import settings
import uuid
import traceback
from rest_framework.authtoken.models import Token

User = get_user_model()

class DeliveryStaffViewSet(viewsets.ModelViewSet):
    queryset = DeliveryStaff.objects.all()
    serializer_class = DeliveryStaffSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['GET', 'PUT'])
    def me(self, request):
        if request.method == 'GET':
            serializer = self.get_serializer(request.user)
            return Response(serializer.data)
        elif request.method == 'PUT':
            serializer = self.get_serializer(request.user, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class DeliveryViewSet(viewsets.ModelViewSet):
    queryset = Delivery.objects.all()
    serializer_class = DeliverySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Only return deliveries assigned to the current user or unassigned deliveries
        return Delivery.objects.filter(Q(delivery_staff=self.request.user) | Q(delivery_staff__isnull=True))

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}

        return Response(serializer.data)

    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

    @action(detail=True, methods=['POST'])
    def scan_qr(self, request, pk=None):
        delivery = self.get_object()
        qr_data = request.data.get('qr_data')
        if delivery.qr_code == qr_data:
            if delivery.status == 'in_progress':
                delivery.status = 'picked_up'
                delivery.save()
                return Response({'status': 'Delivery picked up'})
            else:
                return Response({'error': 'Delivery is not in progress'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'error': 'Invalid QR code'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['POST'])
    def confirm_delivery(self, request, pk=None):
        delivery = self.get_object()
        if delivery.status == 'picked_up':
            delivery.status = 'completed'
            delivery.save()
            return Response({'status': 'Delivery confirmed'})
        return Response({'error': 'Delivery is not in picked up status'}, status=status.HTTP_400_BAD_REQUEST)

    def perform_create(self, serializer):
        # Create delivery without assigning staff
        delivery = serializer.save()
        # Optionally, you can send a notification to all available staff about the new delivery
        # send_new_delivery_notification(delivery)

    @action(detail=True, methods=['POST'])
    def accept_job(self, request, pk=None):
        delivery = self.get_object()
        if delivery.status == 'pending' and delivery.delivery_staff is None:
            delivery.status = 'in_progress'
            delivery.delivery_staff = request.user
            delivery.save()
            return Response({'status': 'Delivery job accepted', 'delivery_staff': request.user.id})
        else:
            return Response({'error': 'Delivery is not available for acceptance'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['GET'])
    def accepted_deliveries(self, request):
        accepted_deliveries = Delivery.objects.filter(
            delivery_staff=request.user,
            status__in=['in_progress', 'picked_up']
        )
        serializer = self.get_serializer(accepted_deliveries, many=True)
        return Response(serializer.data)

class DeliveryIssueViewSet(viewsets.ModelViewSet):
    queryset = DeliveryIssue.objects.all()
    serializer_class = DeliveryIssueSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(reported_by=self.request.user)

    def get_queryset(self):
        return DeliveryIssue.objects.filter(delivery__delivery_staff=self.request.user)

@api_view(['POST'])
@permission_classes([AllowAny])
def register_user(request):
    serializer = DeliveryStaffSerializer(data=request.data)
    if serializer.is_valid():
        try:
            user = serializer.save()
            user.is_active = True  # Set to True for now
            user.confirmation_token = str(uuid.uuid4())
            user.save()

            # Comment out email sending for now
            # send_mail(...)

            return Response({"message": "User registered successfully."}, status=status.HTTP_201_CREATED)
        except Exception as e:
            print(traceback.format_exc())
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([AllowAny])
def confirm_email(request, token):
    try:
        user = User.objects.get(confirmation_token=token)
        user.is_active = True
        user.confirmation_token = ''
        user.save()
        return Response({"message": "Email confirmed. You can now log in."}, status=status.HTTP_200_OK)
    except User.DoesNotExist:
        return Response({"message": "Invalid token."}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([AllowAny])
def password_reset_request(request):
    email = request.data.get('email')
    try:
        user = User.objects.get(email=email)
        reset_token = str(uuid.uuid4())
        user.password_reset_token = reset_token
        user.save()

        # Send password reset email
        send_mail(
            'Password Reset Request',
            f'Please click this link to reset your password: {settings.SITE_URL}/reset-password/{reset_token}',
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )

        return Response({"message": "Password reset email sent."}, status=status.HTTP_200_OK)
    except User.DoesNotExist:
        return Response({"message": "User with this email does not exist."}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([AllowAny])
def password_reset_confirm(request, token):
    new_password = request.data.get('new_password')
    try:
        user = User.objects.get(password_reset_token=token)
        user.set_password(new_password)
        user.password_reset_token = ''
        user.save()
        return Response({"message": "Password reset successful."}, status=status.HTTP_200_OK)
    except User.DoesNotExist:
        return Response({"message": "Invalid token."}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([AllowAny])
def login_user(request):
    email = request.data.get('email')
    password = request.data.get('password')
    user = authenticate(request, username=email, password=password)
    if user:
        token, _ = Token.objects.get_or_create(user=user)
        return Response({'token': token.key}, status=status.HTTP_200_OK)
    else:
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)