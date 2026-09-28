from datetime import date
from decimal import Decimal

from django.db.models import Sum
from django.shortcuts import render

from apps.accounts.models import BankAccount
from apps.core.decorators import customer_required
from apps.core.http import Link, page
from apps.core.models import FAQ, InterestRate, Offer
from apps.notifications.models import Announcement, Notification
from apps.support.models import ServiceRequest
from apps.transactions.models import Transaction

from .utils import inr


def home(request):
    ann = Announcement.objects.filter(is_active=True).order_by("-published_at", "-id")[:5]
    offers = Offer.objects.filter(is_active=True, valid_from__lte=date.today(), valid_to__gte=date.today())[:5]
    rates = InterestRate.objects.filter(is_active=True)[:6]
    faqs = FAQ.objects.filter(is_active=True)[:6]
    return render(request, "core/home.html", {
        "title": "Bharat Nidhi Bank - Banking for a stronger Bharat",
        "announcements": ann,
        "offers": offers,
        "rates": rates,
        "faqs": faqs,
        "is_home": True,
        "is_public_page": True,
    })


def interest_rates(request):
    rows = [[r.get_category_display(), r.product_name, r.tenure_label, f"{r.rate}%"] for r in InterestRate.objects.filter(is_active=True)]
    return page(request, "Interest Rates", table={"headers": ["Category", "Product", "Tenure", "Rate"], "rows": rows})


def faq(request):
    return page(request, "Frequently Asked Questions (FAQ)", details=[(f.question, f.answer) for f in FAQ.objects.filter(is_active=True)])


def personal_banking(request):
    return render(request, "core/public_page.html", {
        "title": "Personal Banking",
        "category": "Consumer Banking",
        "subtitle": "Comprehensive savings, salary, and current accounts crafted for your lifestyle.",
        "image_url": "images/products/savings-account.jpg",
        "cta_url": "/auth/login/",
        "cta_text": "Access Net-Banking",
        "is_public_page": True,
        "features": [
            {"title": "High Yield Savings", "description": "Earn up to 3.50% p.a. interest calculated on daily end-of-day balances.", "icon": "bi-piggy-bank"},
            {"title": "Zero Minimum Balance", "description": "Salary accounts with zero balance requirements and complimentary insurance.", "icon": "bi-shield-check"},
            {"title": "Instant Debit Cards", "description": "Rupay and Global Platinum debit cards with contactless NFC payments.", "icon": "bi-credit-card-2-front"},
        ]
    })


def business_banking(request):
    return render(request, "core/public_page.html", {
        "title": "Business & Commercial Banking",
        "category": "Corporate Solutions",
        "subtitle": "Scalable working capital, current accounts, and credit facilities for growing Indian businesses.",
        "image_url": "images/banking/business-banking.jpg",
        "cta_url": "/contact/",
        "cta_text": "Connect with Relationship Manager",
        "is_public_page": True,
        "features": [
            {"title": "Commercial Current Accounts", "description": "High cash deposit limits and free bulk RTGS/NEFT payment transfers.", "icon": "bi-briefcase-fill"},
            {"title": "MSME Term Loans", "description": "Competitive interest rates and customized repayment for capital expenditure.", "icon": "bi-cash-coin"},
            {"title": "Dedicated Manager", "description": "Direct branch support from experienced banking relationship managers.", "icon": "bi-person-badge-fill"},
        ]
    })


def nri_banking(request):
    return render(request, "core/public_page.html", {
        "title": "NRI Banking Services",
        "category": "Global Indian Banking",
        "subtitle": "Stay connected to your roots with premium NRE/NRO rupee deposits and foreign currency accounts.",
        "image_url": "images/banking/nri-banking.jpg",
        "cta_url": "/support/",
        "cta_text": "Inquire Online",
        "is_public_page": True,
        "features": [
            {"title": "NRE Rupee Accounts", "description": "Fully repatriable principal and interest, exempt from Indian income tax.", "icon": "bi-globe2"},
            {"title": "NRO Savings", "description": "Manage Indian income (rental, dividends, pensions) securely in rupees.", "icon": "bi-currency-exchange"},
            {"title": "Preferential Remittance", "description": "Zero hidden margins on foreign currency remittances into India.", "icon": "bi-send-check"},
        ]
    })


def rural_banking(request):
    return render(request, "core/public_page.html", {
        "title": "Agricultural & Rural Banking",
        "category": "Strengthening Rural Bharat",
        "subtitle": "Affordable farm credit, solar equipment loans, and grassroots financial inclusion for Indian farmers.",
        "image_url": "images/banking/rural-banking.jpg",
        "cta_url": "/contact/",
        "cta_text": "Visit Rural Branch",
        "is_public_page": True,
        "features": [
            {"title": "Kisan Credit Card (KCC)", "description": "Revolving credit at 7% p.a. with 3% prompt repayment incentive.", "icon": "bi-flower1"},
            {"title": "Farm Mechanization Loans", "description": "Tractor, harvesters, and solar water pump financing with easy EMIs.", "icon": "bi-sun-fill"},
            {"title": "Crop Insurance Assistance", "description": "PMFBY linked risk coverage protecting harvests against natural vagaries.", "icon": "bi-umbrella-fill"},
        ]
    })


def loans_info(request):
    return render(request, "core/public_page.html", {
        "title": "Affordable Loan Solutions",
        "category": "Retail Lending",
        "subtitle": "Fulfill life's greatest milestones with transparent rates, zero prepayment penalties, and quick disbursals.",
        "image_url": "images/loans/home-loan.jpg",
        "cta_url": "/loans/apply/",
        "cta_text": "Apply in Net-Banking",
        "is_public_page": True,
        "features": [
            {"title": "Home Loans from 8.50%", "description": "Low processing charges and tenures extending up to 30 years.", "icon": "bi-house-heart"},
            {"title": "Vehicle Loans from 9.00%", "description": "Financing up to 90% on-road cost for electric and ICE vehicles.", "icon": "bi-car-front"},
            {"title": "Education Loans from 9.50%", "description": "Moratorium period covers course duration plus 1 year post-completion.", "icon": "bi-mortarboard"},
        ]
    })


def deposits_info(request):
    return render(request, "core/public_page.html", {
        "title": "Deposits & Wealth Creation",
        "category": "Guaranteed Returns",
        "subtitle": "Grow your wealth with sovereign assurance, flexible payout intervals, and maximum liquidity.",
        "image_url": "images/products/fixed-deposit.jpg",
        "cta_url": "/deposits/open/",
        "cta_text": "Open Deposit Online",
        "is_public_page": True,
        "features": [
            {"title": "Fixed Deposits (FD)", "description": "Up to 6.80% p.a. with additional 0.50% premium for senior citizens.", "icon": "bi-lock"},
            {"title": "Recurring Deposits (RD)", "description": "Build savings starting from ₹500/month with compounding interest.", "icon": "bi-graph-up-arrow"},
            {"title": "Premature Liquidity", "description": "Instant premature closure facility directly to your linked savings account.", "icon": "bi-lightning-charge"},
        ]
    })


def cards_info(request):
    return render(request, "core/public_page.html", {
        "title": "Debit & Credit Cards",
        "category": "Cards & Payments",
        "subtitle": "Premium cards equipped with EMV chip security, NFC contactless tap, and 24x7 control.",
        "image_url": "images/cards/debit-card.png",
        "cta_url": "/cards/",
        "cta_text": "Manage My Cards",
        "is_public_page": True,
        "features": [
            {"title": "Instant Online Controls", "description": "Toggle ATM, POS, Online, and Contactless switches with 1-click in Net-Banking.", "icon": "bi-sliders"},
            {"title": "Daily Limit Customization", "description": "Set dynamic daily limits for domestic ATMs and online merchants.", "icon": "bi-shield-check"},
            {"title": "Zero Lost Card Liability", "description": "Immediate card block facility via Net-Banking self-service.", "icon": "bi-slash-circle"},
        ]
    })


def digital_info(request):
    return render(request, "core/public_page.html", {
        "title": "Digital Banking Experience",
        "category": "Anytime, Anywhere",
        "subtitle": "Experience frictionless banking from home, work, or on the move with our high-security portal.",
        "image_url": "images/products/digital-banking.jpg",
        "cta_url": "/auth/login/",
        "cta_text": "Sign In to Net-Banking",
        "is_public_page": True,
        "features": [
            {"title": "Simulated Fund Transfers", "description": "Instant fund movement between own accounts and third-party beneficiaries.", "icon": "bi-arrow-repeat"},
            {"title": "Self-Service Security", "description": "2-Factor OTP verification, lockout protections, and audit trail logs.", "icon": "bi-fingerprint"},
            {"title": "Instant E-Statements", "description": "Download periodic account statements in PDF and CSV format on-demand.", "icon": "bi-file-earmark-arrow-down"},
        ]
    })


def security_info(request):
    return render(request, "core/public_page.html", {
        "title": "Security Awareness & Fraud Prevention",
        "category": "Safe Digital Banking",
        "subtitle": "Learn how Bharat Nidhi Bank safeguards your accounts and how to avoid online financial fraud.",
        "image_url": "images/security/security-awareness.jpg",
        "cta_url": "/support/new/",
        "cta_text": "Report Fraudulent Activity",
        "is_public_page": True,
        "features": [
            {"title": "Never Share OTP", "description": "Bank officials will never ask for your 6-digit One Time Password under any circumstances.", "icon": "bi-x-circle-fill"},
            {"title": "Beware Suspicious SMS/Calls", "description": "Never download screen sharing apps (AnyDesk, TeamViewer) on caller instructions.", "icon": "bi-telephone-x-fill"},
            {"title": "Check HTTPS URL", "description": "Always ensure you are accessing the legitimate Bharat Nidhi Bank net-banking portal.", "icon": "bi-link-45deg"},
        ]
    })


def announcements_view(request):
    ann = Announcement.objects.filter(is_active=True).order_by("-published_at", "-id")
    items = [{"title": a.title, "body": a.body, "date": a.published_at.strftime("%d-%m-%Y")} for a in ann]
    return render(request, "core/public_page.html", {
        "title": "Bank Announcements & Press Releases",
        "category": "Notices",
        "subtitle": "Official updates, policy notices, and bank alerts from Bharat Nidhi Bank.",
        "items": items,
        "is_public_page": True
    })


def offers_view(request):
    offers = Offer.objects.filter(is_active=True).order_by("-valid_from")
    items = [{"title": o.title, "body": f"{o.description} (Valid: {o.valid_from} to {o.valid_to})", "date": f"Rate: {o.interest_rate}%" if o.interest_rate else ""} for o in offers]
    return render(request, "core/public_page.html", {
        "title": "Special Offers & Festive Schemes",
        "category": "Seasonal Privileges",
        "subtitle": "Exclusive discount on processing charges and bonus deposit rates for our customers.",
        "items": items,
        "is_public_page": True
    })


def contact_view(request):
    return render(request, "core/public_page.html", {
        "title": "Contact Us & Branch Network",
        "category": "Customer Support",
        "subtitle": "Reach our round-the-clock helpdesk or visit our flagship branches across India.",
        "image_url": "images/banking/branch-banking.jpg",
        "cta_url": "/support/new/",
        "cta_text": "Submit Support Request",
        "is_public_page": True,
        "features": [
            {"title": "Toll-Free Helpline", "description": "1800-000-1947 / 1800-000-2026 (Available 24x7)", "icon": "bi-telephone-fill"},
            {"title": "Corporate Office", "description": "Bharat Nidhi Bhavan, 1 Main Road, Nariman Point, Mumbai - 400021", "icon": "bi-building"},
            {"title": "Email Support", "description": "support@bharatnidhibank.demo (Turnaround time: 24-48 hours)", "icon": "bi-envelope-fill"},
        ]
    })


def about_view(request):
    return render(request, "core/public_page.html", {
        "title": "About Bharat Nidhi Bank",
        "category": "Our Heritage & Mission",
        "subtitle": "Founded on the core ethos of national development, financial empowerment, and trust for every citizen.",
        "image_url": "images/banking/branch-consultation.jpg",
        "is_public_page": True,
        "features": [
            {"title": "Banking for a stronger Bharat", "description": "Committed to nation-building, rural prosperity, and inclusive growth.", "icon": "bi-flag-fill"},
            {"title": "Trusted by Millions", "description": "Fictional banking simulation replicating India's premier public sector institutions.", "icon": "bi-shield-check"},
            {"title": "Cutting-edge Technology", "description": "State-of-the-art secure transactional infrastructure built on Django.", "icon": "bi-cpu-fill"},
        ]
    })


def careers_view(request):
    return render(request, "core/public_page.html", {
        "title": "Careers at Bharat Nidhi Bank",
        "category": "Work With Us",
        "subtitle": "Build an inspiring, nation-shaping career in modern banking, finance, and technology.",
        "is_public_page": True,
        "features": [
            {"title": "Probationary Officers", "description": "Comprehensive leadership development programs across retail and corporate banking.", "icon": "bi-mortarboard-fill"},
            {"title": "Specialist Officers (IT & Cyber)", "description": "Leading technological initiatives in financial infrastructure and security.", "icon": "bi-shield-lock-fill"},
            {"title": "Equal Opportunity Employer", "description": "A merit-based, diverse, and supportive workplace fostering career excellence.", "icon": "bi-people-fill"},
        ]
    })


@customer_required
def dashboard(request):
    cust = request.user.customerprofile
    accounts = BankAccount.objects.filter(customer=cust).select_related("account_type", "branch")
    total = accounts.exclude(status="CLOSED").aggregate(t=Sum("balance"))["t"] or Decimal("0")
    recent = Transaction.objects.filter(account__customer=cust).select_related("transfer", "account").order_by("-created_at", "-id")[:5]
    unread = Notification.objects.filter(user=request.user, is_read=False).count()
    pending = ServiceRequest.objects.filter(customer=cust).exclude(status__in=["RESOLVED", "CLOSED"]).count()
    active_cards = cust.cards.filter(status="ACTIVE").count()
    beneficiaries_count = cust.beneficiaries.filter(is_active=True).count()
    
    return render(request, "core/dashboard.html", {
        "title": f"Dashboard - Welcome, {cust.full_name}",
        "customer": cust,
        "accounts": accounts,
        "total_balance": total,
        "recent_transactions": recent,
        "unread_notifications": unread,
        "pending_requests": pending,
        "active_cards_count": active_cards,
        "beneficiaries_count": beneficiaries_count,
    })

