from rest_framework import permissions


class IsOwnerOrAdmin(permissions.BasePermission):
    """Permission to only allow owners or admins to access"""
    
    def has_object_permission(self, request, view, obj):
        # Allow if user is admin
        if request.user.is_admin:
            return True
        
        # Allow if user is the owner
        return obj == request.user


class IsSupervisorOrAdmin(permissions.BasePermission):
    """Permission to only allow supervisors or admins"""
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.is_admin or request.user.is_supervisor
        )


class HasPermission(permissions.BasePermission):
    """Permission checker for specific permissions"""
    
    def __init__(self, permission_name):
        self.permission_name = permission_name
    
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.has_permission(self.permission_name)
        )