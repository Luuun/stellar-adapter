import os
from rest_framework import permissions
from logging import getLogger

from stellar_adapter import settings

logger = getLogger('django')


# Check that the required secret key matches the secret sent in the authorization headers
def authenticate(required_secret, request, view):
    secret = request.META.get('HTTP_AUTHORIZATION')

    if (not secret) or not (('Secret ' + required_secret) == secret):
       return False

    return True


class AdapterGlobalPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        return authenticate(getattr(settings, 'ADAPTER_TOKEN'), request, view)

