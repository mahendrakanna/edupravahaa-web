from rest_framework import permissions

class IsAdmin(permissions.BasePermission):
    """
    Custom permission to only allow admins to access.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_admin

class IsTeacher(permissions.BasePermission):
    """
    Custom permission to only allow teachers to access.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_teacher

class IsStudent(permissions.BasePermission):
    """
    Custom permission to only allow students to access.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_student

class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object or admins to edit it.
    """
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions are only allowed to the owner or admin
        return obj == request.user or request.user.is_admin

class IsTeacherOrAdmin(permissions.BasePermission):
    """
    Custom permission to only allow teachers or admins to access.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and (
            request.user.is_teacher or request.user.is_admin
        )