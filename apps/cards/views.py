from datetime import date

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.audit.services import Actions, log_event
from apps.core.decorators import customer_required
from apps.core.http import Link, form_page, page
from apps.notifications.services import notify

from .forms import CardLimitsForm
from .models import Card

TOGGLES = {"toggle_atm": "atm_enabled", "toggle_online": "online_enabled",
           "toggle_international": "international_enabled", "toggle_contactless": "contactless_enabled"}


def _own(user):
    return Card.objects.filter(user__user=user).select_related("account", "account__account_type", "settings")


@customer_required
def card_list(request):
    cards = _own(request.user)
    return render(request, "cards/card_list.html", {"cards": cards})


@customer_required
def card_detail(request, ref):
    c = get_object_or_404(_own(request.user), card_reference=ref)
    return render(request, "cards/card_detail.html", {
        "card": c,
        "settings": c.settings,
    })


@customer_required
@require_POST
def card_action(request, ref):
    c = get_object_or_404(_own(request.user), card_reference=ref)  # ownership checked before every action
    action = request.POST.get("action", "")
    if c.expiry_date < date.today():
        messages.error(request, "Card expired. Request replacement.")
    elif c.status == "BLOCKED":
        messages.error(request, "Blocked cards can only be re-issued by the bank.")
    elif action == "block":
        c.status = "BLOCKED"; c.save(update_fields=["status", "updated_at"])
        log_event(Actions.CARD_BLOCKED, user=request.user, entity_type="Card", entity_id=c.pk, request=request)
        notify(request.user, "Card blocked", f"Card {c.masked_number} was blocked.", "SECURITY")
        messages.success(request, "Card blocked.")
    elif action == "disable" and c.status == "ACTIVE":
        c.status = "TEMPORARILY_DISABLED"; c.save(update_fields=["status", "updated_at"])
        log_event(Actions.CARD_DISABLED, user=request.user, entity_type="Card", entity_id=c.pk, request=request)
        messages.success(request, "Card temporarily disabled.")
    elif action == "enable" and c.status == "TEMPORARILY_DISABLED":
        c.status = "ACTIVE"; c.save(update_fields=["status", "updated_at"])
        log_event(Actions.CARD_ENABLED, user=request.user, entity_type="Card", entity_id=c.pk, request=request)
        messages.success(request, "Card enabled.")
    elif action in TOGGLES and c.status in ("ACTIVE", "TEMPORARILY_DISABLED"):
        field = TOGGLES[action]
        setattr(c.settings, field, not getattr(c.settings, field)); c.settings.save()
        log_event(Actions.CARD_SETTINGS_CHANGED, user=request.user, entity_type="Card", entity_id=c.pk, metadata={"field": field}, request=request)
        messages.success(request, "Card setting updated.")
    else:
        messages.error(request, "Action not allowed.")
    return redirect("cards:detail", ref=ref)


@customer_required
def card_limits(request, ref):
    c = get_object_or_404(_own(request.user), card_reference=ref, status="ACTIVE")
    form = CardLimitsForm(request.POST or None, instance=c.settings)
    if request.method == "POST" and form.is_valid():
        form.save()
        log_event(Actions.CARD_SETTINGS_CHANGED, user=request.user, entity_type="Card", entity_id=c.pk, metadata={"field": "limits"}, request=request)
        return redirect("cards:detail", ref=ref)
    return form_page(request, "Card limits", form)
