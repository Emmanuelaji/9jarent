# accounts/signals.py
"""
Signal handlers for the accounts app.

NOTE: Platform notification auto-triggers (agent/property/inspection/message
events) live in ``notifications.signals`` and are registered by the
notifications app's ``ready()``. They must NOT be duplicated here — doing so
double-registers every receiver (duplicate notifications) and, because this
module resolves ``.models`` to ``accounts.models``, breaks app startup with
``ImportError: cannot import name 'Notification'``.

Account-specific signals (e.g. future email-OTP-on-signup triggers) belong
in this module.
"""
