from rest_framework import permissions


class IsTargetUser(permissions.BasePermission):
    """
    Allows access to own profile only.
    """

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        return obj == request.user


class IsTargetUserOrCreate(IsTargetUser):
    """
    Allows access to own profile and new sign ups only.
    """

    def has_permission(self, request, view):
        is_authenticated = super().has_permission(request, view)
        if request.method == 'POST':
            if is_authenticated:
                return False
            # User sign up
            return True
        return is_authenticated
