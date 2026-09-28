from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.audit.services import Actions, log_event
from apps.core.decorators import customer_required
from apps.core.http import Link, form_page, page
from apps.notifications.services import notify

from .forms import BeneficiaryEditForm, BeneficiaryForm
from .models import Beneficiary


def _own(user):
    return Beneficiary.objects.filter(owner__user=user)


@customer_required
def beneficiary_list(request):
    bens = _own(request.user)
    return render(request, "beneficiaries/beneficiary_list.html", {"beneficiaries": bens})


@customer_required
def beneficiary_add(request):
    form = BeneficiaryForm(request.POST or None, customer=request.user.customerprofile)
    if request.method == "POST" and form.is_valid():
        b = form.save()
        log_event(Actions.BENEFICIARY_CREATED, user=request.user, entity_type="Beneficiary", entity_id=b.pk,
                  metadata={"type": b.beneficiary_type, "ifsc": b.ifsc_code}, request=request)
        notify(request.user, "Beneficiary added", f"{b.beneficiary_name} was added.", "SECURITY")
        messages.success(request, "Beneficiary added and verified (simulated).")
        return redirect("beneficiaries:list")
    return render(request, "beneficiaries/beneficiary_form.html", {"title": "Add Beneficiary", "form": form})


@customer_required
def beneficiary_edit(request, pk):
    b = get_object_or_404(_own(request.user), pk=pk, is_active=True)
    form = BeneficiaryEditForm(request.POST or None, instance=b)
    if request.method == "POST" and form.is_valid():
        form.save()
        log_event(Actions.BENEFICIARY_UPDATED, user=request.user, entity_type="Beneficiary", entity_id=b.pk, request=request)
        messages.success(request, "Beneficiary updated.")
        return redirect("beneficiaries:list")
    post_actions = [{"label": "Disable beneficiary", "url": f"/beneficiaries/{b.pk}/disable/", "fields": {}}]
    return render(request, "beneficiaries/beneficiary_form.html", {
        "title": "Edit Beneficiary",
        "form": form,
        "beneficiary": b,
        "post_actions": post_actions,
    })


@customer_required
@require_POST
def beneficiary_disable(request, pk):
    b = get_object_or_404(_own(request.user), pk=pk)
    b.is_active = False
    b.save(update_fields=["is_active", "updated_at"])
    log_event(Actions.BENEFICIARY_DISABLED, user=request.user, entity_type="Beneficiary", entity_id=b.pk, request=request)
    messages.success(request, "Beneficiary disabled.")
    return redirect("beneficiaries:list")
