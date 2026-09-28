from django.core.management.base import BaseCommand

from apps.deposits.services import run_due_deposits
from apps.loans.services import run_due_installments


class Command(BaseCommand):
    help = "Runs scheduled simulation jobs: due EMIs and matured deposits (run daily, e.g. via cron)."

    def handle(self, *a, **kw):
        paid, failed = run_due_installments()
        matured = run_due_deposits()
        self.stdout.write(f"EMIs paid={paid} failed={failed}; deposits matured={matured}")
