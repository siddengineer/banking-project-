import calendar
import secrets
import string
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from django.utils import timezone

TWO_PLACES = Decimal("0.01")


def random_digits(n):
    """Cryptographically secure numeric string."""
    return "".join(secrets.choice(string.digits) for _ in range(n))


def generate_customer_number():
    return random_digits(12)


def generate_reference(prefix="TXN"):
    """PREFIX + IST timestamp + 40 random bits -> collision-resistant, <= 30 chars."""
    stamp = timezone.localtime().strftime("%Y%m%d%H%M%S")
    return f"{prefix}{stamp}{secrets.token_hex(5).upper()}"


def money(value):
    return Decimal(value).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def inr(value):
    """Indian digit grouping: 1,00,000.00"""
    q = money(value)
    sign = "-" if q < 0 else ""
    whole, frac = f"{abs(q):.2f}".split(".")
    if len(whole) > 3:
        last3, rest, parts = whole[-3:], whole[:-3], []
        while len(rest) > 2:
            parts.insert(0, rest[-2:])
            rest = rest[:-2]
        if rest:
            parts.insert(0, rest)
        whole = ",".join(parts + [last3])
    return f"{sign}₹{whole}.{frac}"


def add_months(d: date, months: int) -> date:
    m = d.month - 1 + months
    y, m = d.year + m // 12, m % 12 + 1
    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))
