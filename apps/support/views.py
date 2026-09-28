from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.audit.services import Actions, log_event
from apps.core.decorators import customer_required, employee_of, staff_required
from apps.core.http import Link, form_page, page
from apps.core.utils import random_digits
from apps.notifications.services import notify

from .forms import ServiceRequestForm, StaffTicketForm
from .models import ServiceRequest


def new_ticket_number():
    for _ in range(20):
        n = "SR-" + random_digits(6)
        if not ServiceRequest.objects.filter(ticket_number=n).exists():
            return n
    raise RuntimeError("ticket number allocation failed")


@customer_required
def ticket_list(request):
    tickets = ServiceRequest.objects.filter(customer__user=request.user).order_by("-created_at")
    return render(request, "support/ticket_list.html", {"tickets": tickets})


@customer_required
def ticket_new(request):
    form = ServiceRequestForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        t = form.save(commit=False)
        t.customer, t.ticket_number = request.user.customerprofile, new_ticket_number()
        t.save()
        log_event(Actions.SERVICE_REQUEST_CREATED, user=request.user, entity_type="ServiceRequest", entity_id=t.pk, request=request)
        messages.success(request, f"Request created. Reference {t.ticket_number}")
        return redirect("support:detail", ticket=t.ticket_number)
    return render(request, "support/ticket_new.html", {"form": form})


@customer_required
def ticket_detail(request, ticket):
    t = get_object_or_404(ServiceRequest, ticket_number=ticket, customer__user=request.user)
    return render(request, "support/ticket_detail.html", {"ticket": t})


@staff_required()
def staff_ticket_list(request):
    rows = [[Link(t.ticket_number, f"/support/staff/{t.ticket_number}/"), t.customer.full_name, t.get_category_display(), t.status,
             str(t.assigned_to or "-")] for t in ServiceRequest.objects.select_related("customer", "assigned_to__user").exclude(status="CLOSED")]
    return page(request, "Support queue", table={"headers": ["Ticket", "Customer", "Category", "Status", "Assigned"], "rows": rows})


@staff_required()
def staff_ticket_update(request, ticket):
    t = get_object_or_404(ServiceRequest, ticket_number=ticket)
    emp = employee_of(request.user)
    form = StaffTicketForm(request.POST or None, initial={"status": t.status, "priority": t.priority, "admin_response": t.admin_response})
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        t.status, t.priority, t.admin_response = d["status"], d["priority"], d["admin_response"]
        if t.assigned_to is None and emp:
            t.assigned_to = emp
        if t.status in ("RESOLVED", "CLOSED") and not t.resolved_at:
            t.resolved_at = timezone.now()
        t.save()
        log_event(Actions.SERVICE_REQUEST_UPDATED, user=request.user, entity_type="ServiceRequest", entity_id=t.pk, metadata={"status": t.status}, request=request)
        notify(t.customer.user, "Service request updated", f"{t.ticket_number} is now {t.get_status_display()}.", "GENERAL")
        return redirect("support:staff_list")
    return form_page(request, f"Update {t.ticket_number}", form, details=[("Customer", t.customer.full_name), ("Subject", t.subject), ("Description", t.description)])
