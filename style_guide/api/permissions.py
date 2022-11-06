from rest_framework import permissions


class IsIssueOwnerOrReviewer(permissions.BasePermission):
    """
    Allow access to own if owner or reviewier
    """

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request
        if request.method in permissions.SAFE_METHODS:
            return True

        language = request.resolver_match.kwargs[
            'parent_lookup_style_guide__language'
        ]
        reputation = request.user.get_reputation(language)
        role = request.user.get_role_from_reputation(reputation)

        return obj.user == request.user or role == 'reviewer'
