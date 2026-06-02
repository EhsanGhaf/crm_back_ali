from django.urls import path , include
from rest_framework.routers import DefaultRouter
from .views import *


router = DefaultRouter()
# ثبت API مربوط به تیم‌ها (مسیر: /api/accounts/teams/)
router.register(r'teams', TeamViewSet, basename='team')

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('verify-2fa/', Verify2FAView.as_view(), name='verify-2fa'),

    # تنظیمات شخصی کارشناس (فعال‌سازی 2FA)
    path('setup-2fa/', Setup2FAView.as_view(), name='setup-2fa'),
    path('admin/reset-2fa/<int:user_id>/', reset_agent_2fa, name='reset-2fa'),

    path('', include(router.urls)),

    path('users/', UserListAPIView.as_view(), name='user-list'),

    path('teams/<int:pk>/members/', ManageTeamMembersAPIView.as_view(), name='manage-team-members'),

    path('register/', RegisterUserAPIView.as_view(), name='register_user'),

    path('users/<int:pk>/sync/', SyncUserWithZammadAPIView.as_view(), name='user-sync-zammad'),
    path('users/<int:pk>/', UserDetailAPIView.as_view(), name='user-detail'),
    path('me/', CurrentUserAPIView.as_view(), name='current-user'),

]
