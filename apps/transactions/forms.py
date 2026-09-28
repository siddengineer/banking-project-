from datetime import timedelta

from django import forms

from apps.accounts.models import BankAccount
from apps.beneficiaries.models import Beneficiary
from apps.transactions.models import Transaction, Transfer


class TransferForm(forms.Form):
    idempotency_key = forms.CharField(widget=forms.HiddenInput, max_length=64)
    transfer_type = forms.ChoiceField(choices=[("OWN", "Own accounts"), ("INTERNAL", "To BNB beneficiary"), ("EXTERNAL", "To other bank (simulated)")])
    from_account = forms.ModelChoiceField(queryset=BankAccount.objects.none())
    to_account = forms.ModelChoiceField(queryset=BankAccount.objects.none(), required=False, label="To (own account)")
    beneficiary = forms.ModelChoiceField(queryset=Beneficiary.objects.none(), required=False)
    mode = forms.ChoiceField(choices=[("", "-"), ("IMPS", "IMPS"), ("NEFT", "NEFT"), ("RTGS", "RTGS")], required=False)
    amount = forms.DecimalField(max_digits=18, decimal_places=2, min_value=0.01)
    remarks = forms.CharField(max_length=140, required=False)

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        cust = user.customerprofile
        own = BankAccount.objects.filter(customer=cust, status="ACTIVE")
        self.fields["from_account"].queryset = own
        self.fields["to_account"].queryset = own
        self.fields["beneficiary"].queryset = Beneficiary.objects.filter(owner=cust, is_active=True, verification_status="VERIFIED")

    def clean(self):
        d = super().clean()
        t = d.get("transfer_type")
        if t == "OWN" and not d.get("to_account"):
            self.add_error("to_account", "Select the destination account.")
        if t in ("INTERNAL", "EXTERNAL") and not d.get("beneficiary"):
            self.add_error("beneficiary", "Select a beneficiary.")
        if t == "EXTERNAL" and not d.get("mode"):
            self.add_error("mode", "Select a mode.")
        return d


class OTPForm(forms.Form):
    otp = forms.RegexField(regex=r"^\d{6}$", max_length=6, min_length=6, label="6-digit OTP",
                           error_messages={"invalid": "Enter the 6-digit OTP."})


class DateRangeMixin:
    max_days = 92

    def clean(self):
        d = super().clean()
        f, t = d.get("date_from"), d.get("date_to")
        if f and t:
            if f > t:
                raise forms.ValidationError("'From' must not be after 'To'.")
            if (t - f).days > self.max_days:
                raise forms.ValidationError(f"Date range may not exceed {self.max_days} days.")
        return d


class HistoryFilterForm(DateRangeMixin, forms.Form):
    account = forms.ModelChoiceField(queryset=BankAccount.objects.none(), required=False)
    date_from = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    date_to = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    entry_type = forms.ChoiceField(choices=[("", "All"), ("DEBIT", "Debit"), ("CREDIT", "Credit")], required=False)
    min_amount = forms.DecimalField(required=False, min_value=0, max_digits=18, decimal_places=2)
    max_amount = forms.DecimalField(required=False, min_value=0, max_digits=18, decimal_places=2)
    q = forms.CharField(required=False, max_length=50, label="Reference / remarks")

    def __init__(self, *a, user, **kw):
        super().__init__(*a, **kw)
        self.fields["account"].queryset = BankAccount.objects.filter(customer__user=user)

    def clean(self):
        d = super().clean()
        mn, mx = d.get("min_amount"), d.get("max_amount")
        if mn is not None and mx is not None and mn > mx:
            raise forms.ValidationError("Min amount exceeds max amount.")
        return d


class StatementForm(DateRangeMixin, forms.Form):
    max_days = 366
    account = forms.ModelChoiceField(queryset=BankAccount.objects.none())
    date_from = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    date_to = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    format = forms.ChoiceField(choices=[("html", "HTML"), ("csv", "CSV")])

    def __init__(self, *a, user, **kw):
        super().__init__(*a, **kw)
        self.fields["account"].queryset = BankAccount.objects.filter(customer__user=user)
