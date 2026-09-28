from django import forms

from .models import CardSettings

MAX_ATM, MAX_POS = 50000, 200000


class CardLimitsForm(forms.ModelForm):
    class Meta:
        model = CardSettings
        fields = ["daily_atm_limit", "daily_pos_limit"]

    def clean_daily_atm_limit(self):
        v = self.cleaned_data["daily_atm_limit"]
        if not 0 <= v <= MAX_ATM:
            raise forms.ValidationError(f"ATM limit must be between 0 and {MAX_ATM}.")
        return v

    def clean_daily_pos_limit(self):
        v = self.cleaned_data["daily_pos_limit"]
        if not 0 <= v <= MAX_POS:
            raise forms.ValidationError(f"POS limit must be between 0 and {MAX_POS}.")
        return v
