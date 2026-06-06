# Permissions: IsAdminUser restricts access to companies with role=admin
from rest_framework.permissions import BasePermission

from .models import Company


class IsAdminUser(BasePermission):
    """
    Grants access only to authenticated users whose Company.role == 'admin'.

    - Does NOT use Django's built-in is_staff or is_superuser flags —
      those are unrelated to TeamBoard's role system.
    - Returns 403 for any authenticated CLIENT user.
    - Returns 401 for unauthenticated requests (handled upstream by JWT middleware).
    """

    message = "Access restricted to platform administrators."

    def has_permission(self, request, view):
        # Must be authenticated first (JWT middleware handles 401)
        if not request.user or not request.user.is_authenticated:
            return False

        # Check our custom role field, not Django's is_staff
        try:
            return request.user.company.role == Company.Role.ADMIN
        except Company.DoesNotExist:
            return False
