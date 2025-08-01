from rest_framework import permissions
from .models import Customer


class IsCustomer(permissions.BasePermission):
    """Permission class to check if user is a customer"""
    
    def has_permission(self, request, view):
        return (
            request.user and
            isinstance(request.user, Customer) and
            request.user.is_active and
            not request.user.is_deleted
        )


class IsVerifiedCustomer(permissions.BasePermission):
    """Permission class to check if customer is verified"""
    
    def has_permission(self, request, view):
        return (
            request.user and
            isinstance(request.user, Customer) and
            request.user.is_active and
            not request.user.is_deleted and
            request.user.email_verified
        )