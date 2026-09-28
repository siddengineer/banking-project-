from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.accounts.models import BankAccount
from apps.core.decorators import customer_required, employee_of, is_manager, staff_required
from apps.core.http import Link, form_page, page
from apps.core.utils import inr

from .forms import LoanApplicationForm, ReviewForm
from .models import LoanApplication
from .services import LoanError, disburse_loan, review_application, submit_application


@customer_required
def loan_list(request):
    loans = LoanApplication.objects.filter(customer__user=request.user).select_related("loan_type")
    return render(request, "loans/loan_list.html", {"loans": loans})


@customer_required
def loan_apply(request):
    form = LoanApplicationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        try:
            a = submit_application(customer=request.user.customerprofile, loan_type=d["loan_type"], amount=d["amount_requested"],
                                   tenure=d["tenure_months"], purpose=d["purpose"].strip(), request=request)
            messages.success(request, f"Application submitted: LA-{a.pk}")
            return redirect("loans:detail", pk=a.pk)
        except LoanError as e:
            form.add_error(None, str(e))
    return render(request, "loans/loan_apply.html", {"form": form})


@customer_required
def loan_detail(request, pk):
    a = get_object_or_404(LoanApplication.objects.select_related("loan_type", "loan_account"), pk=pk, customer__user=request.user)
    return render(request, "loans/loan_detail.html", {"loan": a})


@staff_required()
def staff_queue(request):
    qs = LoanApplication.objects.select_related("customer", "loan_type").filter(status__in=["SUBMITTED", "UNDER_REVIEW", "APPROVED"], loan_account__isnull=True)
    rows = [[Link(f"LA-{a.pk}", f"/loans/staff/{a.pk}/"), a.customer.full_name, a.loan_type.name, inr(a.amount_requested), a.status] for a in qs]
    return page(request, "Loan queue", table={"headers": ["Application", "Customer", "Type", "Amount", "Status"], "rows": rows})


@staff_required()
def staff_review(request, pk):
    a = get_object_or_404(LoanApplication.objects.select_related("customer", "loan_type"), pk=pk)
    info = [("Customer", a.customer.full_name), ("Type", a.loan_type.name), ("Requested", inr(a.amount_requested)),
            ("Tenure", a.tenure_months), ("Purpose", a.purpose), ("Status", a.status)]
    if a.status == "APPROVED":
        accts = BankAccount.objects.filter(customer=a.customer, status="ACTIVE")
        return page(request, f"Disburse LA-{a.pk}", details=info + [("Sanctioned", inr(a.sanctioned_amount))],
                    post_actions=[{"label": f"Disburse to {x.masked_number}", "url": f"/loans/staff/{a.pk}/disburse/", "fields": {"account": x.pk}} for x in accts] if is_manager(request.user) else [])
    if not is_manager(request.user):
        return page(request, f"LA-{a.pk} (read only)", details=info)
    form = ReviewForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        try:
            review_application(application_id=a.pk, employee=employee_of(request.user), reviewer_user=request.user,
                               approve=d["decision"] == "APPROVE", sanctioned_amount=d["sanctioned_amount"], sanctioned_rate=d["sanctioned_rate"],
                               remarks=d["admin_remarks"], rejection_reason=d["rejection_reason"], request=request)
            messages.success(request, "Decision recorded.")
            return redirect("loans:staff_queue")
        except LoanError as e:
            form.add_error(None, str(e))
    return form_page(request, f"Review LA-{a.pk}", form, details=info)


@staff_required(manager=True)
@require_POST
def staff_disburse(request, pk):
    a = get_object_or_404(LoanApplication, pk=pk)
    acct = get_object_or_404(BankAccount, pk=request.POST.get("account") or 0, customer=a.customer)
    try:
        disburse_loan(application_id=a.pk, account=acct, reviewer_user=request.user, request=request)
        messages.success(request, "Loan disbursed.")
    except LoanError as e:
        messages.error(request, str(e))
    return redirect("loans:staff_queue")
