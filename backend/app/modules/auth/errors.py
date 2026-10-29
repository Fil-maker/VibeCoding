"""Domain errors of the auth module; the router maps them to HTTP."""


class InvalidLink(Exception):
    """The emailed link is wrong, used or expired."""


class SignInRefused(Exception):
    """Base of the reasons a sign-in is refused."""


class InvalidCredentials(SignInRefused):
    """Wrong password or unknown email; the same answer for both."""


class EmailNotConfirmed(SignInRefused):
    """The registrant has not followed the confirmation link."""


class SignInLocked(SignInRefused):
    """Too many failed attempts for this email."""


class NotSignedIn(Exception):
    """No valid session."""
