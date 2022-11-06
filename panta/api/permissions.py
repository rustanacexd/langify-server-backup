from rest_framework import permissions

from .. import models

POST = 'POST'
PUT = 'PUT'
PATCH = 'PATCH'
DELETE = 'DELETE'


class ObjectPermissions(permissions.DjangoObjectPermissions):
    """
    View permissions per object.
    """

    perms_map = {
        'GET': ['%(app_label)s.view_%(model_name)s'],
        'OPTIONS': ['%(app_label)s.view_%(model_name)s'],
        'HEAD': ['%(app_label)s.view_%(model_name)s'],
        'POST': ['%(app_label)s.add_%(model_name)s'],
        'PUT': ['%(app_label)s.change_%(model_name)s'],
        'PATCH': ['%(app_label)s.change_%(model_name)s'],
        'DELETE': ['%(app_label)s.delete_%(model_name)s'],
    }

    def has_permission(self, request, view):
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        """
        Allows authenticated users to retreive works, object perms otherwise.
        """
        safe_method = request.method in permissions.SAFE_METHODS
        if safe_method and request.user.is_authenticated:
            return True
            # todo
            # return getattr(obj, 'private', True)

        return obj.members.filter(pk=request.user.pk).exists()


class WorkPermissions(ObjectPermissions):
    def has_permission(self, request, view):
        """
        Allows anonymous users to retrieve data.
        """
        return request.method == 'GET' or super().has_permission(request, view)

    def _queryset(self, view):
        return models.Trustee.objects.none()

    def has_object_permission(self, request, view, obj):
        return super().has_object_permission(request, view, obj.trustee)


class OriginalSegmentPermissions(WorkPermissions):
    def has_permission(self, request, view):
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        return super().has_object_permission(request, view, obj.work)


class ReputationPermissions(permissions.BasePermission):
    def has_required_reputation(self, request, work=None):
        if work is None:
            kwargs = request.parser_context['kwargs']
            work = kwargs.get('parent_lookup_work') or kwargs.get('pk')

        permissions = self.permissions[request.method]
        user = request.user
        return any(user.has_required_reputation(p, work) for p in permissions)

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        return self.has_required_reputation(request)

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        else:
            return self.has_required_reputation(request, obj.work)


class TranslatedSegmentPermissions(ReputationPermissions):
    permissions = {
        DELETE: ['delete_translation'],
        POST: ['add_translation', 'change_translation', 'restore_translation'],
        PATCH: ['add_translation', 'change_translation'],
        PUT: [],
    }

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        elif obj.work.protected:
            return False
        else:
            return self.has_required_reputation(request, obj.work)


class SegmentCommentPermissions(ReputationPermissions):
    permissions = {
        POST: ['add_comment'],
        PUT: ['change_comment'],
        PATCH: ['change_comment'],
        DELETE: ['delete_comment'],
    }

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.user == request.user


class FlagUserPermissions(ReputationPermissions):
    permissions = {POST: ['flag_user'], DELETE: ['flag_user']}
