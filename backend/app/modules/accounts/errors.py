"""Domain errors of the accounts module; the router maps them to HTTP."""


class EmailTaken(Exception):
    """The email already belongs to a confirmed user."""


class MemberNotFound(Exception):
    """No confirmed member with this id in the administrator's organization."""


class CannotDeactivateSelf(Exception):
    """An administrator asked to deactivate their own account."""


class LastAdministrator(Exception):
    """The change would leave the organization without an active administrator."""


class MemberInactive(Exception):
    """The member is deactivated, so they cannot be made an administrator."""


class InvalidCursor(Exception):
    """The page cursor is not one this API issued."""
