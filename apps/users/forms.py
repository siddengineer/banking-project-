from django import forms
from django.contrib.auth.forms import SetPasswordForm


class LoginForm(forms.Form):
    identifier = forms.CharField(label="Username / email / mobile", max_length=150)
    password = forms.CharField(widget=forms.PasswordInput, strip=False)


class ForgotPasswordForm(forms.Form):
    identifier = forms.CharField(label="Username / email / mobile", max_length=150)


class ResetPasswordForm(SetPasswordForm):
    otp = forms.RegexField(regex=r"^\d{6}$", label="6-digit OTP", max_length=6)
    field_order = ["otp", "new_password1", "new_password2"]
