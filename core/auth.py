import hashlib
import hmac
from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse

SESSION_KEY = "is_authed"


def hash_pin(pin: str) -> str:
    # simple SHA256. Bisa kita upgrade jadi PBKDF2 nanti.
    return hashlib.sha256(pin.encode("utf-8")).hexdigest()


def verify_login(access_code: str, pin: str) -> bool:
    if not settings.PIN_HASH:
        return False

    if access_code != settings.ACCESS_CODE:
        return False

    pin_h = hash_pin(pin)
    return hmac.compare_digest(pin_h, settings.PIN_HASH)


def require_auth(view_func):
    def _wrapped(request, *args, **kwargs):
        if request.session.get(SESSION_KEY):
            return view_func(request, *args, **kwargs)
        return redirect(reverse("login"))
    return _wrapped