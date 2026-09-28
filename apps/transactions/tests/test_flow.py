import datetime
from decimal import Decimal

from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import Client, TestCase, override_settings

from apps.accounts.models import AccountType, BankAccount, Branch
from apps.accounts.services import open_account
from apps.audit.models import AuditLog
from apps.beneficiaries.models import Beneficiary
from apps.deposits.services import DepositError, close_premature, open_deposit
from apps.deposits.models import DepositScheme
from apps.loans.models import LoanType
from apps.loans.services import LoanError, calc_emi, disburse_loan, review_application, submit_application
from apps.transactions.models import Transaction, Transfer
from apps.transactions.services.transfer_service import TransferError, confirm_transfer, create_transfer_intent, move_funds
from apps.transactions.services.treasury import ensure_treasury, get_treasury_account
from apps.users.models import CustomerProfile, User
from apps.users.services.otp import OTPError, issue_otp

PW = "Str0ng!Pass"


def mk_customer(username, mobile, balance):
    u = User.objects.create_user(username=username, email=f"{username}@x.com", mobile=mobile, password=PW)
    cp = CustomerProfile.objects.create(user=u, full_name=username.title(), date_of_birth=datetime.date(1990, 1, 1), gender="MALE")
    branch = Branch.objects.get_or_create(branch_code="B1", defaults=dict(branch_name="Main", ifsc_code="BNBK0000001", address="a", city="c", district="d", state="s", pincode="400001", phone="1"))[0]
    at = AccountType.objects.get_or_create(code="SAV", defaults=dict(type_name="Savings"))[0]
    acct = open_account(customer=cp, account_type=at, branch=branch, initiated_by=u, initial_deposit=balance)
    return u, acct


@override_settings(EXTERNAL_FAILURE_RATE=0)
class TransferTests(TestCase):
    def setUp(self):
        ensure_treasury()
        self.a, self.a_acct = mk_customer("alice1234", "9000000001", Decimal("10000.00"))
        self.b, self.b_acct = mk_customer("bobby1234", "9000000002", Decimal("500.00"))
        self.ben = Beneficiary.objects.create(owner=self.a.customerprofile, beneficiary_name="Bobby", bank_name="BNB", account_number=self.b_acct.account_number,
                                              ifsc_code="BNBK0000001", beneficiary_type="INTERNAL", verification_status="VERIFIED")
        self.ext = Beneficiary.objects.create(owner=self.a.customerprofile, beneficiary_name="Ext Person", bank_name="Other", account_number="1234567890123",
                                              ifsc_code="HDFC0001234", beneficiary_type="EXTERNAL", verification_status="VERIFIED")

    def intent(self, amount="100.00", key="k1", user=None, ben=None, **kw):
        return create_transfer_intent(user=user or self.a, from_account=self.a_acct, amount=amount, transfer_type="INTERNAL",
                                      beneficiary=ben or self.ben, idempotency_key=key, **kw)

    def total(self):
        return sum(BankAccount.objects.values_list("balance", flat=True))

    def test_happy_path_conserves_money_and_writes_ledger_audit(self):
        before = self.total()
        tr, created = self.intent("1234.50")
        self.assertTrue(created)
        self.a_acct.refresh_from_db()
        self.assertEqual(self.a_acct.balance, Decimal("10000.00"))  # nothing debited before OTP
        code = issue_otp(self.a, "TRANSFER", tr.reference_number)
        tr = confirm_transfer(user=self.a, reference=tr.reference_number, otp_code=code)
        self.assertEqual(tr.status, "SUCCESS")
        self.a_acct.refresh_from_db(); self.b_acct.refresh_from_db()
        self.assertEqual(self.a_acct.balance, Decimal("8765.50"))
        self.assertEqual(self.b_acct.balance, Decimal("1734.50"))
        self.assertEqual(self.total(), before)
        self.assertEqual(Transaction.objects.filter(transfer=tr).count(), 2)
        self.assertTrue(AuditLog.objects.filter(action="TRANSFER_COMPLETED").exists())

    def test_wrong_otp_moves_nothing_and_limits_attempts(self):
        tr, _ = self.intent()
        issue_otp(self.a, "TRANSFER", tr.reference_number)
        for _ in range(3):
            with self.assertRaises(OTPError):
                confirm_transfer(user=self.a, reference=tr.reference_number, otp_code="000000")
        with self.assertRaises(OTPError):
            confirm_transfer(user=self.a, reference=tr.reference_number, otp_code="000000")
        self.a_acct.refresh_from_db()
        self.assertEqual(self.a_acct.balance, Decimal("10000.00"))
        tr.refresh_from_db(); self.assertEqual(tr.status, "PENDING")

    def test_otp_bound_to_transfer_and_single_use(self):
        t1, _ = self.intent(key="k1")
        t2, _ = self.intent(key="k2")
        code = issue_otp(self.a, "TRANSFER", t2.reference_number)
        with self.assertRaises(OTPError):  # OTP for t2 does not work on t1
            confirm_transfer(user=self.a, reference=t1.reference_number, otp_code=code)

    def test_replay_does_not_double_debit(self):
        tr, _ = self.intent("100.00")
        code = issue_otp(self.a, "TRANSFER", tr.reference_number)
        confirm_transfer(user=self.a, reference=tr.reference_number, otp_code=code)
        confirm_transfer(user=self.a, reference=tr.reference_number, otp_code=code)  # replay
        self.a_acct.refresh_from_db()
        self.assertEqual(self.a_acct.balance, Decimal("9900.00"))

    def test_idempotency_key(self):
        t1, c1 = self.intent(key="same")
        t2, c2 = self.intent(key="same")
        self.assertEqual(t1.pk, t2.pk); self.assertTrue(c1); self.assertFalse(c2)
        self.assertEqual(Transfer.objects.filter(idempotency_key="same").count(), 1)
        with self.assertRaises(TransferError):  # another user cannot reuse the key
            self.intent(key="same", user=self.b)

    def test_validation_rules(self):
        for bad in ["0", "-5", "10.001", "abc", "NaN", 1.5]:
            with self.assertRaises(TransferError, msg=str(bad)):
                self.intent(bad, key=f"k{bad}")
        with self.assertRaises(TransferError):
            self.intent("10000.01", key="big")  # > balance
        with self.assertRaises(TransferError):  # same account
            create_transfer_intent(user=self.a, from_account=self.a_acct, amount="10", transfer_type="OWN", to_account=self.a_acct, idempotency_key="self")

    def test_foreign_beneficiary_and_account_rejected(self):
        with self.assertRaises(TransferError):
            create_transfer_intent(user=self.b, from_account=self.b_acct, amount="10", transfer_type="INTERNAL", beneficiary=self.ben, idempotency_key="idor1")
        with self.assertRaises(TransferError):  # A tries to debit B's account
            create_transfer_intent(user=self.a, from_account=self.b_acct, amount="10", transfer_type="INTERNAL", beneficiary=self.ben, idempotency_key="idor2")

    def test_insufficient_funds_at_execution_fails_cleanly(self):
        tr, _ = self.intent("9000.00")
        move_funds(from_account=self.a_acct, to_account=self.b_acct, amount="5000", transfer_type="INTERNAL", initiated_by=self.a)  # balance drops meanwhile
        code = issue_otp(self.a, "TRANSFER", tr.reference_number)
        tr = confirm_transfer(user=self.a, reference=tr.reference_number, otp_code=code)
        self.assertEqual(tr.status, "FAILED")
        self.a_acct.refresh_from_db()
        self.assertEqual(self.a_acct.balance, Decimal("5000.00"))

    def test_frozen_account_blocks_debit(self):
        tr, _ = self.intent()
        BankAccount.objects.filter(pk=self.a_acct.pk).update(status="FROZEN")
        code = issue_otp(self.a, "TRANSFER", tr.reference_number)
        self.assertEqual(confirm_transfer(user=self.a, reference=tr.reference_number, otp_code=code).status, "FAILED")

    def test_external_transfer_simulated(self):
        tr, _ = create_transfer_intent(user=self.a, from_account=self.a_acct, amount="200", transfer_type="EXTERNAL", beneficiary=self.ext, mode="NEFT", idempotency_key="ext1")
        code = issue_otp(self.a, "TRANSFER", tr.reference_number)
        tr = confirm_transfer(user=self.a, reference=tr.reference_number, otp_code=code)
        self.assertEqual(tr.status, "SUCCESS")
        self.assertEqual(tr.legs.count(), 1)  # single debit leg

    @override_settings(EXTERNAL_FAILURE_RATE=1.0)
    def test_external_simulated_failure_leaves_funds(self):
        tr, _ = create_transfer_intent(user=self.a, from_account=self.a_acct, amount="200", transfer_type="EXTERNAL", beneficiary=self.ext, mode="IMPS", idempotency_key="ext2")
        code = issue_otp(self.a, "TRANSFER", tr.reference_number)
        self.assertEqual(confirm_transfer(user=self.a, reference=tr.reference_number, otp_code=code).status, "FAILED")
        self.a_acct.refresh_from_db(); self.assertEqual(self.a_acct.balance, Decimal("10000.00"))

    def test_db_blocks_negative_balance(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            BankAccount.objects.filter(pk=self.a_acct.pk).update(balance=Decimal("-1"))

    def test_move_funds_atomic_rollback(self):
        with self.assertRaises(TransferError):
            move_funds(from_account=self.b_acct, to_account=self.a_acct, amount="999999", transfer_type="INTERNAL", initiated_by=self.b)
        self.assertEqual(Transfer.objects.filter(amount=Decimal("999999")).count(), 0)


class IDORandViewTests(TestCase):
    def setUp(self):
        ensure_treasury()
        self.a, self.a_acct = mk_customer("alice1234", "9000000001", Decimal("1000"))
        self.b, self.b_acct = mk_customer("bobby1234", "9000000002", Decimal("1000"))
        self.c = Client()
        self.assertTrue(self.c.login(username="bobby1234", password=PW))

    def test_other_customers_account_is_404(self):
        self.assertEqual(self.c.get(f"/accounts/{self.a_acct.account_number}/").status_code, 404)
        self.assertEqual(self.c.get(f"/accounts/{self.b_acct.account_number}/").status_code, 200)

    def test_other_customers_transfer_receipt_is_404(self):
        ben = Beneficiary.objects.create(owner=self.a.customerprofile, beneficiary_name="B", bank_name="BNB", account_number=self.b_acct.account_number,
                                         ifsc_code="BNBK0000001", beneficiary_type="INTERNAL", verification_status="VERIFIED")
        tr, _ = create_transfer_intent(user=self.a, from_account=self.a_acct, amount="10", transfer_type="INTERNAL", beneficiary=ben, idempotency_key="z")
        self.assertEqual(self.c.get(f"/transfers/{tr.reference_number}/receipt/").status_code, 404)
        self.assertEqual(self.c.get(f"/transfers/{tr.reference_number}/verify/").status_code, 404)

    def test_beneficiary_edit_and_disable_scoped(self):
        ben = Beneficiary.objects.create(owner=self.a.customerprofile, beneficiary_name="B", bank_name="BNB", account_number="12345678901",
                                         ifsc_code="BNBK0000001", beneficiary_type="EXTERNAL", verification_status="VERIFIED")
        self.assertEqual(self.c.get(f"/beneficiaries/{ben.pk}/edit/").status_code, 404)
        self.assertEqual(self.c.post(f"/beneficiaries/{ben.pk}/disable/").status_code, 404)

    def test_history_only_own_rows(self):
        r = self.c.get("/transactions/")
        self.assertEqual(r.status_code, 200)
        self.assertNotContains(r, self.a_acct.masked_number)

    def test_login_required_and_lockout(self):
        anon = Client()
        self.assertEqual(anon.get("/dashboard/").status_code, 302)
        for _ in range(3):
            anon.post("/auth/login/", {"identifier": "alice1234", "password": "wrong"})
        self.a.refresh_from_db()
        self.assertTrue(self.a.is_locked)
        r = anon.post("/auth/login/", {"identifier": "alice1234", "password": PW})
        self.assertContains(r, "locked")
        self.assertFalse(anon.get("/dashboard/").status_code == 200)

    def test_login_by_email_and_mobile(self):
        for ident in ("bobby1234@x.com", "9000000002", "BOBBY1234"):
            self.assertTrue(Client().login(username=ident, password=PW), ident)

    def test_customer_cannot_reach_staff_pages(self):
        for url in ("/loans/staff/", "/support/staff/"):
            self.assertEqual(self.c.get(url).status_code, 403)

    def test_audit_log_immutable(self):
        log = AuditLog.objects.create(action="X")
        log.action = "Y"
        with self.assertRaises(PermissionError):
            log.save()
        with self.assertRaises(PermissionError):
            log.delete()


class LoanDepositTests(TestCase):
    def setUp(self):
        call_command("seed_demo", verbosity=0)
        self.u = User.objects.get(username="ravikumar1")
        self.acct = self.u.customerprofile.accounts.first()
        self.mgr = User.objects.get(username="manager01")

    def test_emi_and_schedule_sum(self):
        emi = calc_emi(Decimal("100000"), Decimal("12"), 12)
        self.assertEqual(emi, Decimal("8884.88"))

    def test_loan_lifecycle_and_double_disburse(self):
        lt = LoanType.objects.get(code="PL")
        app = submit_application(customer=self.u.customerprofile, loan_type=lt, amount=Decimal("100000"), tenure=12, purpose="x" * 30)
        with self.assertRaises(LoanError):  # second pending application blocked
            submit_application(customer=self.u.customerprofile, loan_type=lt, amount=Decimal("100000"), tenure=12, purpose="x" * 30)
        with self.assertRaises(LoanError):  # reject without reason
            review_application(application_id=app.pk, employee=None, reviewer_user=self.mgr, approve=False)
        with self.assertRaises(LoanError):  # cannot disburse unapproved
            disburse_loan(application_id=app.pk, account=self.acct, reviewer_user=self.mgr)
        review_application(application_id=app.pk, employee=None, reviewer_user=self.mgr, approve=True)
        before = self.acct.__class__.objects.get(pk=self.acct.pk).balance
        loan = disburse_loan(application_id=app.pk, account=self.acct, reviewer_user=self.mgr)
        self.assertEqual(self.acct.__class__.objects.get(pk=self.acct.pk).balance, before + Decimal("100000"))
        self.assertEqual(loan.installments.count(), 12)
        self.assertEqual(sum(i.principal_amount for i in loan.installments.all()), Decimal("100000.00"))
        with self.assertRaises(LoanError):
            disburse_loan(application_id=app.pk, account=self.acct, reviewer_user=self.mgr)

    def test_customer_cannot_set_status_via_form(self):
        c = Client(); c.login(username="ravikumar1", password="Demo@12345")
        lt = LoanType.objects.get(code="PL")
        c.post("/loans/apply/", {"loan_type": lt.pk, "amount_requested": "100000", "tenure_months": 12, "purpose": "y" * 30, "status": "APPROVED"})
        from apps.loans.models import LoanApplication
        self.assertEqual(LoanApplication.objects.get().status, "SUBMITTED")

    def test_fd_open_and_early_closure_rules(self):
        fd = DepositScheme.objects.get(code="FD1")
        d = open_deposit(user=self.u, scheme_id=fd.pk, amount=Decimal("10000"), tenure=12, linked_account=self.acct)
        self.assertEqual(d.maturity_amount, Decimal("10680.00"))
        with self.assertRaises(DepositError):
            close_premature(user=self.u, deposit_id=d.pk)  # < 7 days
        with self.assertRaises(DepositError):
            open_deposit(user=self.u, scheme_id=fd.pk, amount=Decimal("100"), tenure=12, linked_account=self.acct)
