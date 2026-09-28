import datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import AccountType, BankAccount, Branch, Nominee
from apps.accounts.services import open_account
from apps.beneficiaries.models import Beneficiary
from apps.cards.services import issue_demo_card
from apps.core.models import FAQ, InterestRate, Offer
from apps.deposits.models import DepositScheme
from apps.loans.models import LoanType
from apps.notifications.models import Announcement
from apps.transactions.services.treasury import ensure_treasury
from apps.users.models import Address, CustomerProfile, EmployeeProfile, KYCProfile, SecuritySettings

DEMO_PASSWORD = "Demo@12345"  # demo data only


class Command(BaseCommand):
    help = "Seeds demo data (idempotent). All demo users share the demo password printed at the end."

    @transaction.atomic
    def handle(self, *a, **kw):
        User = get_user_model()
        ensure_treasury()
        for g in ("OFFICER", "MANAGER", "SUPERADMIN"):
            Group.objects.get_or_create(name=g)
        branches = []
        for code, name, city, state, pin in [("B0001", "Mumbai Main", "Mumbai", "Maharashtra", "400001"), ("B0002", "Delhi Connaught Place", "New Delhi", "Delhi", "110001"),
                                             ("B0003", "Bengaluru MG Road", "Bengaluru", "Karnataka", "560001"), ("B0004", "Chennai Anna Salai", "Chennai", "Tamil Nadu", "600002")]:
            b, _ = Branch.objects.get_or_create(branch_code=code, defaults=dict(branch_name=name, ifsc_code=f"BNBK000{code[-4:]}", address=f"1 Main Road, {city}",
                                                                              city=city, district=city, state=state, pincode=pin, phone="01123456789", manager_name="Branch Manager"))
            branches.append(b)
        types = {c: AccountType.objects.get_or_create(code=c, defaults=dict(type_name=n, min_balance=m, interest_rate=r))[0]
                 for c, n, m, r in [("SAV", "Savings", 1000, "3.00"), ("CUR", "Current", 5000, "0.00"), ("SAL", "Salary", 0, "3.00"), ("SEN", "Senior Citizen", 500, "3.50"), ("MIN", "Minor", 0, "3.00"), ("BSB", "Basic Savings", 0, "2.75")]}
        for code, name, r, lo, hi, tmin, tmax in [("PL", "Personal Loan", "11.50", 50000, 2000000, 6, 60), ("HL", "Home Loan", "8.50", 500000, 20000000, 60, 360),
                                                   ("CL", "Car Loan", "9.00", 100000, 3000000, 12, 84), ("GL", "Gold Loan", "8.75", 20000, 2500000, 6, 36), ("EL", "Education Loan", "9.50", 50000, 5000000, 12, 120)]:
            LoanType.objects.get_or_create(code=code, defaults=dict(name=name, interest_rate=r, min_amount=lo, max_amount=hi, tenure_min=tmin, tenure_max=tmax))
        DepositScheme.objects.get_or_create(code="FD1", defaults=dict(name="Fixed Deposit", scheme_type="FD", interest_rate="6.80", min_amount=1000, min_tenure_months=6, max_tenure_months=120))
        DepositScheme.objects.get_or_create(code="RD1", defaults=dict(name="Recurring Deposit", scheme_type="RD", interest_rate="6.50", min_amount=500, min_tenure_months=6, max_tenure_months=60))
        today = datetime.date.today()
        Offer.objects.get_or_create(title="Festive Home Loan Offer", defaults=dict(description="Reduced processing fee.", scheme_type="LOAN", interest_rate="8.35", valid_from=today, valid_to=today + datetime.timedelta(days=90)))
        InterestRate.objects.get_or_create(category="DEPOSIT", product_name="Fixed Deposit", tenure_label="1 year", defaults=dict(rate="6.80"))
        InterestRate.objects.get_or_create(category="LENDING", product_name="Home Loan", tenure_label="", defaults=dict(rate="8.50"))
        FAQ.objects.get_or_create(question="Is this a real bank?", defaults=dict(answer="No. Bharat Nidhi Bank is an academic simulation."))
        Announcement.objects.get_or_create(title="Welcome to Bharat Nidhi Bank (demo)", defaults=dict(body="Academic simulation - no real money."))

        def customer(username, mobile, name, gender, pan, aadhaar, branch, deposit):
            if User.objects.filter(username=username).exists():
                return User.objects.get(username=username)
            u = User.objects.create_user(username=username, email=f"{username}@example.com", mobile=mobile, password=DEMO_PASSWORD)
            cp = CustomerProfile.objects.create(user=u, full_name=name, date_of_birth=datetime.date(1992, 5, 17), gender=gender, annual_income=Decimal("900000"))
            KYCProfile.objects.create(user=u, pan_number=pan, aadhaar_number=aadhaar, kyc_status="VERIFIED")
            SecuritySettings.objects.create(user=u, registered_mobile=mobile, registered_email=u.email)
            Address.objects.create(user=u, address_type="PERMANENT", line1="12 Demo Street", city=branch.city, state=branch.state, pincode=branch.pincode, is_default=True)
            acct = open_account(customer=cp, account_type=types["SAV"], branch=branch, initiated_by=u, initial_deposit=deposit)
            Nominee.objects.create(account=acct, name="Nominee Kumar", relation="Spouse", date_of_birth=datetime.date(1994, 1, 1))
            issue_demo_card(customer=cp, account=acct)
            return u

        ravi = customer("ravikumar1", "9876500001", "Ravi Kumar", "MALE", "ABCDE1234F", "111122223333", branches[0], Decimal("250000"))
        priya = customer("priyasharma1", "9876500002", "Priya Sharma", "FEMALE", "PQRST5678U", "444455556666", branches[1], Decimal("125000"))
        r_acct, p_acct = ravi.customerprofile.accounts.first(), priya.customerprofile.accounts.first()
        Beneficiary.objects.get_or_create(owner=ravi.customerprofile, account_number=p_acct.account_number, ifsc_code=p_acct.branch.ifsc_code,
                                          defaults=dict(beneficiary_name="Priya Sharma", bank_name="Bharat Nidhi Bank", beneficiary_type="INTERNAL", verification_status="VERIFIED"))
        Beneficiary.objects.get_or_create(owner=ravi.customerprofile, account_number="1234567890123", ifsc_code="HDFC0001234",
                                          defaults=dict(beneficiary_name="Amit Verma", bank_name="Other Bank (demo)", beneficiary_type="EXTERNAL", verification_status="VERIFIED"))

        for username, mobile, code, desig, group in [("officer01", "9876500011", "EMP001", "Officer", "OFFICER"), ("manager01", "9876500012", "EMP002", "Manager", "MANAGER")]:
            if not User.objects.filter(username=username).exists():
                u = User.objects.create_user(username=username, email=f"{username}@bnb.demo", mobile=mobile, password=DEMO_PASSWORD, is_staff=True)
                EmployeeProfile.objects.create(user=u, employee_code=code, designation=desig, department="Operations", branch=branches[0], joining_date=datetime.date(2020, 1, 1))
                u.groups.add(Group.objects.get(name=group))
        self.stdout.write(self.style.SUCCESS(f"Seeded. Demo users: ravikumar1, priyasharma1 (customers), officer01, manager01 (staff). Password: {DEMO_PASSWORD}"))
        self.stdout.write("Create an admin with: python manage.py createsuperuser")
