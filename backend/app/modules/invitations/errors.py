"""Domain errors of the invitations module; the router maps them to HTTP."""


class InvalidInvitation(Exception):
    """The invitation link is wrong, used, revoked, replaced or expired."""


class InvitationExists(Exception):
    """The organization already has an open invitation for this email."""


class InvitationNotOpen(Exception):
    """The invitation is already accepted, revoked or expired."""


class InvalidCursor(Exception):
    """The page cursor is not one this API issued."""
