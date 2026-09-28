from django import forms

from apps.accounts.models import BankAccount

from .models import DepositScheme


class OpenDepositForm(forms.Form):
    scheme = forms.ModelChoiceField(queryset=DepositScheme.objects.filter(is_active=True))
    amount = forms.DecimalField(max_digits=18, decimal_places=2, min_value=1, label="Principal (FD) / monthly instalment (RD)")
    tenure_months = forms.IntegerField(min_value=1, max_value=120)
    linked_account = forms.ModelChoiceField(queryset=BankAccount.objects.none())

    def __init__(self, *a, user, **kw):
        super().__init__(*a, **kw)
        self.fields["linked_account"].queryset = BankAccount.objects.filter(customer__user=user, status="ACTIVE")

    def clean(self):
        d = super().clean()
        s, ten = d.get("scheme"), d.get("tenure_months")
        if s and ten and not s.min_tenure_months <= ten <= s.max_tenure_months:
            self.add_error("tenure_months", f"Tenure must be {s.min_tenure_months}-{s.max_tenure_months} months.")
        if s and d.get("amount") and d["amount"] < s.min_amount:
            self.add_error("amount", f"Minimum is {s.min_amount}.")
        return d
