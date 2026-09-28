import re

from django import forms
from django.conf import settings

from apps.accounts.models import BankAccount
from apps.core.validators import ifsc_validator

from .models import Beneficiary


class BeneficiaryForm(forms.ModelForm):
    class Meta:
        model = Beneficiary
        fields = ["beneficiary_name", "bank_name", "account_number", "ifsc_code", "nickname", "beneficiary_type"]

    def __init__(self, *args, customer, **kwargs):
        super().__init__(*args, **kwargs)
        self.customer = customer

    def clean_beneficiary_name(self):
        n = self.cleaned_data["beneficiary_name"].strip()
        if not (3 <= len(n) <= 100) or not re.fullmatch(r"[A-Za-z][A-Za-z .'-]*", n):
            raise forms.ValidationError("Name must be 3-100 letters/spaces.")
        return n

    def clean_account_number(self):
        a = self.cleaned_data["account_number"].strip()
        if not re.fullmatch(r"\d{11,16}", a):
            raise forms.ValidationError("Account number must be 11-16 digits.")
        return a

    def clean_ifsc_code(self):
        c = self.cleaned_data["ifsc_code"].strip().upper()
        ifsc_validator(c)
        return c

    def clean(self):
        d = super().clean()
        acc, ifsc, typ = d.get("account_number"), d.get("ifsc_code"), d.get("beneficiary_type")
        if not (acc and ifsc and typ):
            return d
        if Beneficiary.objects.filter(owner=self.customer, account_number=acc, ifsc_code=ifsc).exists():
            raise forms.ValidationError("Beneficiary already exists.")
        if Beneficiary.objects.filter(owner=self.customer, is_active=True).count() >= settings.MAX_ACTIVE_BENEFICIARIES:
            raise forms.ValidationError("Delete an existing beneficiary first.")
        if typ == "INTERNAL" and not BankAccount.objects.filter(account_number=acc, branch__ifsc_code=ifsc).exists():
            raise forms.ValidationError("No such Bharat Nidhi Bank account for this IFSC.")
        return d

    def save(self, commit=True):
        b = super().save(commit=False)
        b.owner = self.customer
        b.verification_status = Beneficiary.Verification.VERIFIED  # simulated verification
        if commit:
            b.save()
        return b


class BeneficiaryEditForm(forms.ModelForm):
    class Meta:
        model = Beneficiary
        fields = ["beneficiary_name", "nickname"]  # account number is locked after creation

    clean_beneficiary_name = BeneficiaryForm.clean_beneficiary_name
