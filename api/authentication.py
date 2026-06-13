from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from .models import Company


class ApiKeyAuthentication(BaseAuthentication):
    def authenticate(self, request):
        key = request.headers.get('X-Api-Key')
        if not key:
            return None
        try:
            company = Company.objects.select_related('user').get(api_key=key)
            return (company.user, key)
        except Company.DoesNotExist:
            raise AuthenticationFailed('Invalid API key.')

    def authenticate_header(self, request):
        return 'X-Api-Key'
