from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def customer_required(view):
    @login_required
    @wraps(view)
    def wrapper(request, *a, **kw):
        if not hasattr(request.user, "customerprofile"):
            raise PermissionDenied
        return view(request, *a, **kw)
    return wrapper


def is_manager(user):
    return user.is_superuser or user.groups.filter(name__in=["MANAGER", "SUPERADMIN"]).exists()


def staff_required(manager=False):
    """Officer+ (active EmployeeProfile) or manager+ (group MANAGER / superuser)."""
    def deco(view):
        @login_required
        @wraps(view)
        def wrapper(request, *a, **kw):
            u = request.user
            emp = getattr(u, "employeeprofile", None)
            ok = u.is_superuser or (emp is not None and emp.status == "ACTIVE")
            if not ok or (manager and not is_manager(u)):
                raise PermissionDenied
            return view(request, *a, **kw)
        return wrapper
    return deco


def employee_of(user):
    return getattr(user, "employeeprofile", None)
