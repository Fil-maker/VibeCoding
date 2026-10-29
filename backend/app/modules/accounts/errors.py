"""Domain errors of the accounts module; the router maps them to HTTP."""


class EmailTaken(Exception):
    """The email already belongs to a confirmed user."""
