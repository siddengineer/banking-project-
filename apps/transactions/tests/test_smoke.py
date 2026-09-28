import re
from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from django.contrib.auth import get_user_model
from apps.transactions.models import Transfer

@override_settings(DEMO_SHOW_OTP=True, EXTERNAL_FAILURE_RATE=0)
class Smoke(TestCase):
    def test_flow(self):
        call_command("seed_demo", verbosity=0)
        c = Client(); assert c.login(username="ravikumar1", password="Demo@12345")
        for u in ["/dashboard/","/accounts/","/beneficiaries/","/beneficiaries/add/","/transfers/new/","/transactions/","/statements/","/cards/","/loans/","/loans/apply/","/deposits/","/deposits/open/","/notifications/","/support/","/support/new/","/auth/profile/","/auth/change-password/","/","/faq/","/interest-rates/"]:
            r = c.get(u); assert r.status_code == 200, (u, r.status_code)
        r = c.get("/transfers/new/")
        key = re.search(r'name="idempotency_key" value="(\w+)"', r.content.decode()).group(1)
        U = get_user_model().objects.get(username="ravikumar1")
        acct = U.customerprofile.accounts.first(); ben = U.customerprofile.beneficiaries.filter(beneficiary_type="INTERNAL").first()
        data = dict(idempotency_key=key, transfer_type="INTERNAL", from_account=acct.pk, beneficiary=ben.pk, amount="150.00", remarks="test")
        r = c.post("/transfers/new/", data, follow=True)
        otp = re.search(r"OTP is (\d{6})", r.content.decode()).group(1)
        c.post("/transfers/new/", data)  # double submit
        assert Transfer.objects.filter(idempotency_key=key).count() == 1
        tr = Transfer.objects.get(idempotency_key=key)
        r = c.post(f"/transfers/{tr.reference_number}/verify/", {"otp": otp}, follow=True)
        assert "Transfer successful" in r.content.decode(), r.content.decode()[:800]
        assert c.get("/statements/?account=%d&date_from=2020-01-01&date_to=2030-01-01&format=csv" % acct.pk).status_code == 200
        # admin
        call_command("createsuperuser", interactive=False, username="admin1", email="a@a.com", mobile="9111111111", verbosity=0)
        A = get_user_model().objects.get(username="admin1"); A.set_password("Adm!n12345"); A.save()
        ac = Client(); ac.login(username="admin1", password="Adm!n12345")
        for m in ["users/user","accounts/bankaccount","transactions/transfer","audit/auditlog","cards/card","loans/loanapplication","deposits/depositaccount","support/servicerequest","notifications/announcement","core/offer","beneficiaries/beneficiary"]:
            assert ac.get(f"/admin/{m}/").status_code == 200, m
        assert ac.get("/admin/transactions/transfer/add/").status_code == 403
        # staff
        m = Client(); m.login(username="manager01", password="Demo@12345")
        assert m.get("/loans/staff/").status_code == 200 and m.get("/support/staff/").status_code == 200
