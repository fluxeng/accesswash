from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'portal'

# API URLs
urlpatterns = [
    # Authentication endpoints
    path('auth/register/', views.CustomerRegistrationView.as_view(), name='register'),
    path('auth/login/', views.CustomerLoginView.as_view(), name='login'),
    path('auth/logout/', views.CustomerLogoutView.as_view(), name='logout'),
    path('auth/forgot-password/', views.ForgotPasswordView.as_view(), name='forgot_password'),
    path('auth/reset-password/', views.ResetPasswordView.as_view(), name='reset_password'),
    path('auth/change-password/', views.ChangePasswordView.as_view(), name='change_password'),
    
    # Customer endpoints
    path('dashboard/', views.CustomerDashboardView.as_view(), name='dashboard'),
    path('profile/', views.CustomerProfileView.as_view(), name='profile'),
    path('auth/verify-connection/', views.verify_connection, name='verify_connection'),

    
    # Session management
    path('sessions/', views.customer_sessions_view, name='sessions'),
    path('sessions/<int:session_id>/logout/', views.logout_session_view, name='logout_session'),
]