import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

TURNSTILE_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"

ERROR_MESSAGES = {
    "missing-input-secret": "Verification service configuration error.",
    "invalid-input-secret": "Verification service configuration error.",
    "missing-input-response": "Verification is required.",
    "invalid-input-response": "Verification failed. Please refresh the page and try again.",
    "bad-request": "Verification failed. Please try again.",
    "timeout-or-duplicate": "Verification expired. Please refresh the page and try again.",
    "internal-error": "Verification service is temporarily unavailable. Please try again.",
}


def verify_turnstile(token, remote_ip=None):
    """
    Verify a Cloudflare Turnstile token.

    Returns:
        (True, None)
        (False, user_friendly_message)
    """

    # Feature flag
    if not settings.TURNSTILE_ENABLED:
        return True, None

    # Missing token
    if not token:
        return False, "Verification is required."

    payload = {
        "secret": settings.TURNSTILE_SECRET_KEY,
        "response": token,
    }

    if remote_ip:
        payload["remoteip"] = remote_ip

    try:
        response = requests.post(
            TURNSTILE_VERIFY_URL,
            data=payload,
            timeout=5
        )

        response.raise_for_status()

        result = response.json()

        if result.get("success"):
            return True, None

        error_codes = result.get("error-codes", [])

        # Log actual Cloudflare errors for developers
        logger.warning(
            "Turnstile verification failed. Error codes: %s",
            error_codes
        )

        if error_codes:
            return False, ERROR_MESSAGES.get(
                error_codes[0],
                "Verification failed. Please try again."
            )

        return False, "Verification failed. Please try again."

    except requests.Timeout:
        logger.exception("Turnstile request timed out.")
        return False, "Verification service timed out. Please try again."

    except requests.RequestException:
        logger.exception("Turnstile request failed.")
        return False, "Verification service is unavailable. Please try again."