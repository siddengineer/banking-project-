import threading
from decimal import Decimal
from unittest import skipUnless

from django.db import connection, connections
from django.test import TransactionTestCase

from apps.accounts.models import BankAccount
from apps.transactions.services.transfer_service import TransferError, move_funds
from apps.transactions.services.treasury import ensure_treasury

from .test_flow import mk_customer


@skipUnless(connection.vendor == "postgresql", "row-lock test needs PostgreSQL")
class ConcurrentTransferTests(TransactionTestCase):
    def test_no_negative_balance_under_concurrency(self):
        ensure_treasury()
        a, a_acct = mk_customer("alice1234", "9000000001", Decimal("100.00"))
        b, b_acct = mk_customer("bobby1234", "9000000002", Decimal("0.00"))
        results = []

        def worker(src, dst, user):
            try:
                move_funds(from_account=src, to_account=dst, amount="80.00", transfer_type="INTERNAL", initiated_by=user)
                results.append("ok")
            except TransferError:
                results.append("declined")
            finally:
                connections.close_all()

        ts = [threading.Thread(target=worker, args=(a_acct, b_acct, a)) for _ in range(2)]
        [t.start() for t in ts]; [t.join() for t in ts]
        self.assertEqual(sorted(results), ["declined", "ok"])
        self.assertEqual(BankAccount.objects.get(pk=a_acct.pk).balance, Decimal("20.00"))

    def test_opposing_transfers_do_not_deadlock(self):
        ensure_treasury()
        a, a_acct = mk_customer("alice1234", "9000000001", Decimal("500.00"))
        b, b_acct = mk_customer("bobby1234", "9000000002", Decimal("500.00"))

        def worker(src, dst, user):
            try:
                for _ in range(10):
                    move_funds(from_account=src, to_account=dst, amount="1.00", transfer_type="INTERNAL", initiated_by=user)
            finally:
                connections.close_all()

        ts = [threading.Thread(target=worker, args=(a_acct, b_acct, a)), threading.Thread(target=worker, args=(b_acct, a_acct, b))]
        [t.start() for t in ts]; [t.join() for t in ts]
        total = sum(BankAccount.objects.filter(pk__in=[a_acct.pk, b_acct.pk]).values_list("balance", flat=True))
        self.assertEqual(total, Decimal("1000.00"))
