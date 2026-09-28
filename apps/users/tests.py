from datetime import date, timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import AccountType, Branch
from apps.users.models import CustomerProfile, KYCProfile, OTPVerification, User


def make_user(username="alice123", email="alice@example.com", mobile="9876543210"):
    return User.objects.create_user(username=username, email=email, mobile=mobile, password="Str0ng!Pass")


class UserModelTests(TestCase):
    def test_auth_user_model_is_custom(self):
        self.assertEqual(settings.AUTH_USER_MODEL, "users.User")

    def test_password_is_hashed(self):
        u = make_user()
        self.assertNotEqual(u.password, "Str0ng!Pass")
        self.assertTrue(u.check_password("Str0ng!Pass"))

    def test_username_rules(self):
        for bad in ["abc", "has space1", "x" * 21, "bad_name!"]:
            u = User(username=bad, email="b@example.com", mobile="9876543211")
            with self.assertRaises(ValidationError):
                u.full_clean(exclude=["password"])

    def test_mobile_rules(self):
        u = User(username="bob12345", email="b@example.com", mobile="5876543210")
        with self.assertRaises(ValidationError):
            u.full_clean(exclude=["password"])

    def test_username_case_insensitive_unique_at_db_level(self):
        make_user()
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create_user(
                username="ALICE123", email="other@example.com", mobile="9876543299", password="x"
            )

    def test_email_normalised_and_ci_unique(self):
        u = make_user(email="Alice@Example.com")
        self.assertEqual(u.email, "alice@example.com")


class ProfileTests(TestCase):
    def test_customer_profile_defaults_and_age(self):
        u = make_user()
        p = CustomerProfile(user=u, full_name="Alice Sharma", date_of_birth=date(1995, 1, 1), gender="FEMALE")
        p.full_clean()
        p.save()
        self.assertEqual(len(p.customer_number), 12)
        young = CustomerProfile(user=u, full_name="Kid", date_of_birth=date.today() - timedelta(days=365 * 5), gender="MALE")
        with self.assertRaises(ValidationError):
            young.full_clean(exclude=["user", "customer_number"])

    def test_negative_income_rejected_by_db(self):
        u = make_user()
        with self.assertRaises(IntegrityError), transaction.atomic():
            CustomerProfile.objects.create(
                user=u, full_name="Alice Sharma", date_of_birth=date(1990, 1, 1), gender="FEMALE", annual_income=-1
            )

    def test_kyc_masking_and_regex(self):
        u = make_user()
        k = KYCProfile(user=u, pan_number="ABCDE1234F", aadhaar_number="123456789012")
        k.full_clean()
        self.assertEqual(k.masked_aadhaar, "XXXXXXXX9012")
        self.assertNotIn("123456789012", k.masked_aadhaar)
        bad = KYCProfile(user=u, pan_number="abcde1234f", aadhaar_number="12")
        with self.assertRaises(ValidationError):
            bad.full_clean(exclude=["user"])


class OTPModelTests(TestCase):
    def test_constraints(self):
        u = make_user()
        now = timezone.now()
        with self.assertRaises(IntegrityError), transaction.atomic():
            OTPVerification.objects.create(
                user=u, purpose="LOGIN", hashed_otp="x", created_at=now, expires_at=now - timedelta(minutes=1)
            )
        with self.assertRaises(IntegrityError), transaction.atomic():
            OTPVerification.objects.create(
                user=u, purpose="LOGIN", hashed_otp="x", created_at=now,
                expires_at=now + timedelta(minutes=5), attempt_count=4, max_attempts=3,
            )


class AccountsRefTests(TestCase):
    def test_account_type_and_branch(self):
        AccountType.objects.create(type_name="Savings", code="SAV", min_balance=1000)
        with self.assertRaises(IntegrityError), transaction.atomic():
            AccountType.objects.create(type_name="Bad", code="BAD", min_balance=-1)
        b = Branch(branch_code="B001", branch_name="Main", ifsc_code="BNBK0000001", address="1 MG Road",
                   city="Pune", district="Pune", state="MH", pincode="411001", phone="02012345678")
        b.full_clean()
        b.ifsc_code = "BAD"
        with self.assertRaises(ValidationError):
            b.full_clean()
