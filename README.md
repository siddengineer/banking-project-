# Bharat Nidhi Bank (BNB) - academic banking simulation (Django + MySQL)
Fictional demo. No real payments, OTP delivery, KYC or banking network.

## Setup
    python -m venv venv && source venv/bin/activate
    pip install -r requirements.txt
    # MySQL 8.0.16+ required (CHECK constraints). Create DB:  CREATE DATABASE bharat_nidhi_bank CHARACTER SET utf8mb4;
    cp .env.example .env              # edit values; never commit .env
    python manage.py migrate
    python manage.py seed_demo        # demo data + bank settlement account (required)
    python manage.py createsuperuser
    python manage.py runserver
    python manage.py test
    python manage.py run_jobs         # daily: due EMIs + matured deposits

Demo logins (password `Demo@12345`): ravikumar1, priyasharma1 (customers); officer01, manager01 (staff).

## Design notes
- Money moves ONLY in `apps/transactions/services/transfer_service.py` (atomic, `select_for_update`, accounts locked in primary-key order).
- Transfer flow: intent (PENDING, idempotency key) -> OTP (HMAC-hashed, bound to user+purpose+transfer ref, 3 attempts, 5 min, single-use) -> atomic execute -> receipt.
- Loans/FDs/EMIs/opening deposits use a seeded bank settlement account (`BNB_TREASURY_ACCOUNT_NUMBER`) as counter-party, because `Transfer.from_account` is mandatory in the freeze.
- Customers get 404 (not 403) for other users' objects. Staff roles: active EmployeeProfile (officer) + group MANAGER / superuser (approve, disburse).
- Templates are minimal generic placeholders (`templates/generic/`) for the frontend engineer to replace.
