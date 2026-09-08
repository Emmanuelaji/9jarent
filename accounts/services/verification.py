# accounts/services/verification.py
"""
Identity verification service layer for agent/landlord onboarding.

CURRENT STATE: manual review only. Nothing in this file calls a live
verification API - there is no IDENTITY_VERIFICATION_API_KEY configured,
and no such setting exists yet. An AgentVerification submission (NIN/BVN/
CAC numbers + uploaded documents) is reviewed by an admin looking at the
documents directly (see dashboard views: verifications_list,
verification_detail, approve_verification, reject_verification).

FUTURE STATE (not implemented): once a provider is chosen (e.g. Prembly/
Identitypass, Smile ID), wire the functions below to real API calls, add
the corresponding settings (IDENTITY_VERIFICATION_API_KEY,
IDENTITY_VERIFICATION_APP_ID, IDENTITY_VERIFICATION_ENV), and update the
submission view to call these automatically instead of only queueing the
submission for manual review. Keeping this as a separate service module
now means that wiring is a contained change here plus one call-site in the
view, not a rewrite of the model/view/template layer.
"""


class VerificationAPIError(Exception):
    """Raised by verify_* functions once they call a real API. Unused today
    since none of them make a real call yet."""
    pass


def verify_nin(nin_number, user):
    """
    Verify a National Identification Number against a real registry API and
    confirm the returned name matches `user`.

    NOT YET IMPLEMENTED - no verification API is configured. Submissions
    are queued for manual admin review instead of calling this. When a
    provider is wired in, this should return a dict like
    {'verified': bool, 'match_score': float, 'raw_response': dict} and raise
    VerificationAPIError on a request/provider failure.
    """
    raise NotImplementedError(
        "Automated NIN verification is not yet implemented. "
        "This submission should be reviewed manually via the admin dashboard instead."
    )


def verify_bvn(bvn_number, user):
    """
    Verify a Bank Verification Number against a real registry API and
    confirm the returned name matches `user`. NOT YET IMPLEMENTED - see
    verify_nin() docstring; same status and same manual-review fallback.
    """
    raise NotImplementedError(
        "Automated BVN verification is not yet implemented. "
        "This submission should be reviewed manually via the admin dashboard instead."
    )


def verify_cac(rc_number, user):
    """
    Verify a CAC (Corporate Affairs Commission) registration number against
    the real business registry. NOT YET IMPLEMENTED - see verify_nin()
    docstring; same status and same manual-review fallback.
    """
    raise NotImplementedError(
        "Automated CAC verification is not yet implemented. "
        "This submission should be reviewed manually via the admin dashboard instead."
    )


def fuzzy_name_match(name_a, name_b, threshold=85):
    """
    Compare two names and return True if similar enough to be considered a
    match (used once a real verification API returns a name to compare
    against the account holder's name). Implemented now (no external API
    needed for this part) so it's ready to use the moment verify_nin/
    verify_bvn/verify_cac return real data - currently unused since nothing
    calls those functions yet.
    """
    import difflib
    a = (name_a or '').strip().lower()
    b = (name_b or '').strip().lower()
    if not a or not b:
        return False
    ratio = difflib.SequenceMatcher(None, a, b).ratio() * 100
    return ratio >= threshold