from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from apps.core.decorators import customer_required
from apps.core.http import page, paginate

from .models import Notification


@customer_required
def notification_list(request):
    qs = Notification.objects.filter(user=request.user).order_by("-created_at")
    unread_count = qs.filter(is_read=False).count()
    p, qstr = paginate(request, qs, 20)
    return render(request, "notifications/notification_list.html", {
        "page_obj": p,
        "unread_count": unread_count,
        "querystring": qstr,
    })


@customer_required
@require_POST
def mark_read(request):
    qs = Notification.objects.filter(user=request.user, is_read=False)  # only own rows
    if request.POST.get("id", "").isdigit():
        qs = qs.filter(pk=int(request.POST["id"]))
    qs.update(is_read=True)
    return redirect("notifications:list")
