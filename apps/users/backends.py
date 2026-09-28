from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q


def find_user(identifier):
    if not identifier:
        return None
    ident = identifier.strip()
    return get_user_model().objects.filter(
        Q(username__iexact=ident) | Q(email__iexact=ident) | Q(mobile=ident)
    ).first()


class BNBBackend(ModelBackend):
    """Login with username, email or registered mobile. Locked/inactive users are refused."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        user = find_user(username)
        if user is None:
            get_user_model()().set_password(password or "")  # equalise timing
            return None
        if not user.check_password(password or ""):
            return None
        if user.is_locked or not user.is_active:
            return None
        return user
