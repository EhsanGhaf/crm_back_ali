import pyotp
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework import viewsets
from rest_framework.decorators import api_view
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.views import APIView
from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model

from tickets.services import get_ticketing_service
from .models import Team
from .serializers import TeamSerializer, UserSerializer, UserRegistrationSerializer

User = get_user_model()

@api_view(['POST'])
def reset_agent_2fa(request, user_id):
    if not (request.user.is_superuser or request.user.is_staff):
        return Response({"error": "شما سطح دسترسی لازم برای این کار را ندارید."}, status=403)

    try:
        user = User.objects.get(id=user_id)
        user.is_2fa_enabled = False
        user.otp_base32 = None
        user.save()

        return Response({"message": f"احراز هویت دو مرحله‌ای برای '{user.username}' با موفقیت ریست شد."})

    except User.DoesNotExist:
        return Response({"error": "کاربر یافت نشد."}, status=404)


class LoginView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        user = authenticate(username=username, password=password)

        if user:
            if user.is_2fa_enabled:
                return Response({
                    "step": "2fa_required",
                    "temp_token": str(RefreshToken.for_user(user).access_token),
                    "message": "لطفاً کد تایید گوگل را وارد کنید."
                })

            return self.get_full_tokens(user)
        print("❌ رمز عبور اشتباه است یا کاربر یافت نشد.")
        return Response({"error": "نام کاربری یا رمز عبور اشتباه است."}, status=401)

    def get_full_tokens(self, user):
        refresh = RefreshToken.for_user(user)
        return Response({
            "step": "completed",
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "is_admin": user.is_superuser or user.is_staff
        })


class Verify2FAView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        otp_code = request.data.get('code')
        username = request.data.get('username')

        try:
            user = User.objects.get(username=username)

            if user.verify_otp(otp_code):
                refresh = RefreshToken.for_user(user)
                return Response({
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                    "is_admin": user.is_superuser or user.is_staff
                })
            else:
                return Response({"error": "کد تایید اشتباه است."}, status=400)
        except User.DoesNotExist:
            return Response({"error": "کاربر یافت نشد."}, status=404)

class Setup2FAView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        if not user.otp_base32:
            user.generate_otp_secret()

        totp = pyotp.TOTP(user.otp_base32)

        provisioning_uri = totp.provisioning_uri(
            name=user.username,
            issuer_name='Wallex CRM'
        )

        return Response({
            "secret": user.otp_base32,
            "qr_uri": provisioning_uri,
            "message": "لطفا این qrcode را در Google Authenticator اسکن کنید"
        })

    def post(self, request):
        code = request.data.get('code')
        user = request.user

        if not code:
            return Response({"error": "کد تایید را ارسال کنید."}, status=status.HTTP_400_BAD_REQUEST)

        if user.verify_otp(code):
            user.is_2fa_enabled = True
            user.save()
            return Response({"message": "کد دو مرحله‌ای شما با موفقیت فعال شد"})

        return Response({"error": "کد وارد شده اشتباه است."}, status=status.HTTP_400_BAD_REQUEST)

class TeamViewSet(viewsets.ModelViewSet):
    queryset = Team.objects.all().order_by('-created_at')
    serializer_class = TeamSerializer
    permission_classes = [AllowAny]


class ManageTeamMembersAPIView(APIView):
    def post(self, request, pk):
        team = get_object_or_404(Team, pk=pk)
        user_id = request.data.get('user_id')
        action = request.data.get('action')

        if not user_id or action not in ['add', 'remove']:
            return Response(
                {"error": "پارامترهای user_id و action الزامی هستند."},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = get_object_or_404(User, pk=user_id)
        zammad = get_ticketing_service()
        user_email = user.email if user.email else f"{user.username}@crm.local"

        if action == 'add':
            team.members.add(user)
            zammad.assign_user_to_group(user_email, team.name, action='add')
            message = f"کاربر {user.first_name} با موفقیت به کارتابل اضافه شد."

        elif action == 'remove':
            team.members.remove(user)
            zammad.assign_user_to_group(user_email, team.name, action='remove')
            message = f"کاربر {user.first_name} با موفقیت از کارتابل حذف شد."

        return Response({"message": message}, status=status.HTTP_200_OK)


class UserListAPIView(APIView):
    def get(self, request):
        users = User.objects.filter(is_active=True).order_by('-id')
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class RegisterUserAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)

        if serializer.is_valid():
            user = serializer.save()
            ticketing_service = get_ticketing_service()
            identifier = user.email if user.email else user.username

            zammad_id = ticketing_service.get_or_create_user(
                identifier=identifier,
                firstname=user.first_name or 'کارشناس',
                lastname=user.last_name or 'پشتیبانی',
                role="Agent",
            )

            if zammad_id:
                user.zammad_id = zammad_id
                user.save()

            return Response({
                "message": "حساب کاربری با موفقیت ساخته و با زمد همگام‌سازی شد.",
                "user_id": user.id,
                "zammad_id": zammad_id
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class SyncUserWithZammadAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        ticketing_service = get_ticketing_service()
        identifier = user.email if user.email else user.username

        try:
            zammad_id = ticketing_service.get_or_create_user(
                identifier=identifier,
                firstname=user.first_name or 'کارشناس',
                lastname=user.last_name or 'پشتیبانی',
                role="Agent",
            )

            if zammad_id:
                user.zammad_id = zammad_id
                user.save()
                return Response({
                    "message": "کارشناس با موفقیت با زمد همگام شد.",
                    "zammad_id": zammad_id
                }, status=status.HTTP_200_OK)

            return Response(
                {"error": "عملیات همگام‌سازی ناموفق بود. زمد شناسه‌ای برنگرداند."},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": f"خطا در ارتباط با سرور زمد: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UserDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        user = get_object_or_404(User, pk=pk)

        if 'username' in request.data: user.username = request.data['username']
        if 'email' in request.data: user.email = request.data['email']
        if 'first_name' in request.data: user.first_name = request.data['first_name']
        if 'last_name' in request.data: user.last_name = request.data['last_name']

        if 'password' in request.data and request.data['password'].strip():
            user.set_password(request.data['password'])

        if 'is_active' in request.data:
            new_active_status = request.data['is_active']

            if request.user.id == user.id and new_active_status is False:
                return Response(
                    {"error": "شما نمی‌توانید حساب کاربری خودتان را غیرفعال کنید."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            user.is_active = new_active_status



        user.save()
        return Response({"message": "اطلاعات کاربر با موفقیت به‌روزرسانی شد."}, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        user = get_object_or_404(User, pk=pk)

        if request.user.id == user.id:
            return Response({"error": "شما نمی‌توانید حساب کاربری خودتان را حذف کنید."},
                            status=status.HTTP_400_BAD_REQUEST)

        user.delete()
        return Response({"message": "کاربر با موفقیت حذف شد."}, status=status.HTTP_200_OK)

class CurrentUserAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response({
            "id": user.id,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "is_2fa_enabled": user.is_2fa_enabled,
            "zammad_id": user.zammad_id,
            "is_admin": user.is_superuser or user.is_staff
        }, status=status.HTTP_200_OK)