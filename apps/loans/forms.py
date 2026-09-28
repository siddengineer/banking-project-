from django import forms

from .models import LoanApplication, LoanType


class LoanApplicationForm(forms.ModelForm):
    class Meta:
        model = LoanApplication
        fields = ["loan_type", "amount_requested", "tenure_months", "purpose"]  # status is never customer-settable

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.fields["loan_type"].queryset = LoanType.objects.filter(is_active=True)

    def clean(self):
        d = super().clean()
        lt, amt, ten = d.get("loan_type"), d.get("amount_requested"), d.get("tenure_months")
        if lt and amt is not None and not lt.min_amount <= amt <= lt.max_amount:
            self.add_error("amount_requested", f"Amount must be between {lt.min_amount} and {lt.max_amount}.")
        if lt and ten is not None and not lt.tenure_min <= ten <= lt.tenure_max:
            self.add_error("tenure_months", f"Tenure must be {lt.tenure_min}-{lt.tenure_max} months.")
        if d.get("purpose") is not None and not 20 <= len(d["purpose"].strip()) <= 1000:
            self.add_error("purpose", "Purpose must be 20-1000 characters.")
        return d


class ReviewForm(forms.Form):
    decision = forms.ChoiceField(choices=[("APPROVE", "Approve"), ("REJECT", "Reject")])
    sanctioned_amount = forms.DecimalField(required=False, max_digits=18, decimal_places=2, min_value=0)
    sanctioned_rate = forms.DecimalField(required=False, max_digits=5, decimal_places=2, min_value=0)
    admin_remarks = forms.CharField(required=False, widget=forms.Textarea)
    rejection_reason = forms.CharField(required=False, widget=forms.Textarea)

    def clean(self):
        d = super().clean()
        if d.get("decision") == "REJECT" and len((d.get("rejection_reason") or "").strip()) < 5:
            self.add_error("rejection_reason", "Reason required to reject.")
        return d
