"""Format-only validators (no external verification - simulation constraint)."""
from datetime import date

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator

username_validator = RegexValidator(
    r"^[A-Za-z0-9]{6,20}$", "Username must be 6-20 letters/digits with no spaces."
)
mobile_validator = RegexValidator(
    r"^[6-9]\d{9}$", "Enter a 10-digit mobile number starting with 6-9."
)
ifsc_validator = RegexValidator(
    r"^[A-Z]{4}0[A-Z0-9]{6}$", "Enter a valid IFSC (e.g. BNBK0001234)."
)
pincode_validator = RegexValidator(r"^\d{6}$", "Enter a 6-digit pincode.")
pan_validator = RegexValidator(r"^[A-Z]{5}[0-9]{4}[A-Z]$", "Enter a valid PAN (e.g. ABCDE1234F).")
aadhaar_validator = RegexValidator(r"^\d{12}$", "Aadhaar must be 12 digits.")
name_length_validators = []  # length rules enforced by min_length in forms


def validate_min_age(dob, years=10):
    today = date.today()
    age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    if dob > today:
        raise ValidationError("Date of birth cannot be in the future.")
    if age < years:
        raise ValidationError(f"Age must be at least {years} years.")

account_number_validator = RegexValidator(r"^\d{11}$", "Account number must be 11 digits.")
