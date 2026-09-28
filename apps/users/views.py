from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.conf import settings
from django.db import transaction
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from apps.audit.services import Actions, log_event
from apps.core.http import form_page, page
from apps.notifications.services import notify

from .backends import find_user
from .forms import ForgotPasswordForm, LoginForm, ResetPasswordForm
from .models import SecuritySettings
from .services.lockout import register_failed_login, reset_failed_logins, unlock
from .services.otp import OTPError, consume_otp, issue_otp, verify_otp

GENERIC_FAIL = "Invalid username or password."


def login_view(request):
    if request.user.is_authenticated:
        return redirect(settings.LOGIN_REDIRECT_URL)
    form = LoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        ident, pw = form.cleaned_data["identifier"], form.cleaned_data["password"]
        target = find_user(ident)
        user = authenticate(request, username=ident, password=pw)
        if user is not None:
            reset_failed_logins(user)
            login(request, user)
            log_event(Actions.LOGIN_SUCCESS, user=user, entity_type="User", entity_id=user.pk, request=request)
            notify(user, "Login successful", "You logged in to net-banking.", "SECURITY")
            nxt = request.POST.get("next") or request.GET.get("next")
            if nxt and url_has_allowed_host_and_scheme(nxt, {request.get_host()}, request.is_secure()):
                return redirect(nxt)
            return redirect(settings.LOGIN_REDIRECT_URL)
        msg = GENERIC_FAIL
        if target is not None:
            if target.check_password(pw):  # correct password but refused
                msg = "Contact your branch." if not target.is_active else "Your username is locked due to repeated failed attempts. Use Forgot password to unlock."
            elif not target.is_locked and target.is_active:
                if register_failed_login(target):
                    log_event(Actions.ACCOUNT_LOCKED, user=target, entity_type="User", entity_id=target.pk, request=request)
        log_event(Actions.LOGIN_FAILED, user=target, entity_type="User", entity_id=getattr(target, "pk", ""), request=request)
        form.add_error(None, msg)
    return render(request, "users/login.html", {
        "title": "Internet Banking Login",
        "form": form,
        "is_public_page": True,
        "is_auth_flow": True,
    })


@require_POST
def logout_view(request):
    if request.user.is_authenticated:
        log_event(Actions.LOGOUT, user=request.user, request=request)
    logout(request)
    return redirect(settings.LOGIN_URL)


@login_required
def password_change(request):
    form = PasswordChangeForm(request.user, request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        update_session_auth_hash(request, user)  # other sessions become invalid
        SecuritySettings.objects.filter(user=user).update(last_password_change=timezone.now())
        log_event(Actions.PASSWORD_CHANGED, user=user, entity_type="User", entity_id=user.pk, request=request)
        notify(user, "Password changed", "Your password was changed.", "SECURITY")
        messages.success(request, "Password changed.")
        return redirect("core:dashboard")
    return render(request, "users/password_change.html", {"form": form})


def forgot_password(request):
    form = ForgotPasswordForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        u = find_user(form.cleaned_data["identifier"])
        if u is not None and u.is_active:
            code = issue_otp(u, "PASSWORD_RESET")
            request.session["pw_reset_user"] = u.pk
            if settings.DEMO_SHOW_OTP:
                messages.info(request, f"DEMO MODE - your OTP is {code}")
        messages.success(request, "If the account exists, an OTP has been sent.")  # never reveal existence
        return redirect("users:reset_password")
    return form_page(request, "Forgot password", form, "Send OTP")


def reset_password(request):
    from .models import User
    uid = request.session.get("pw_reset_user")
    user = User.objects.filter(pk=uid, is_active=True).first() if uid else None
    if user is None:
        form = ResetPasswordForm(User(), request.POST or None)
        if request.method == "POST":
            form.add_error(None, "Invalid or expired request.")
        return form_page(request, "Reset password", form)
    form = ResetPasswordForm(user, request.POST or None)
    if request.method == "POST" and form.is_valid():
        rec, err = verify_otp(user, "PASSWORD_RESET", form.cleaned_data["otp"])
        if rec is None:
            form.add_error("otp", err)
        else:
            with transaction.atomic():
                consume_otp(rec)
                form.save()
                unlock(user)  # SRS: successful reset clears lock
            request.session.pop("pw_reset_user", None)
            SecuritySettings.objects.filter(user=user).update(last_password_change=timezone.now())
            log_event(Actions.PASSWORD_CHANGED, user=user, entity_type="User", entity_id=user.pk, metadata={"via": "reset"}, request=request)
            messages.success(request, "Password reset. Please log in.")
            return redirect(settings.LOGIN_URL)
    return form_page(request, "Reset password", form, "Reset")


@login_required
def profile(request):
    u = request.user
    cp = getattr(u, "customerprofile", None)
    kyc = getattr(u, "kycprofile", None)
    addresses = u.addresses.all()
    sec = getattr(u, "securitysettings", None)
    return render(request, "users/profile.html", {
        "user": u,
        "customer": cp,
        "kyc": kyc,
        "addresses": addresses,
        "security": sec,
    })
