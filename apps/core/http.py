from collections import namedtuple

from django.core.paginator import Paginator
from django.shortcuts import render

Link = namedtuple("Link", "text url")


def page(request, title, **ctx):
    """Minimal generic page renderer (frontend engineer replaces templates later)."""
    ctx["title"] = title
    return render(request, "generic/page.html", ctx)


def form_page(request, title, form, submit="Submit", **ctx):
    return render(request, "generic/form.html", {"title": title, "form": form, "submit": submit, **ctx})


def paginate(request, qs, per_page=20):
    p = Paginator(qs, per_page).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)
    return p, params.urlencode()
