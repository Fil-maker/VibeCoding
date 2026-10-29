"""Domain errors of the mailboxes module; the router maps them to HTTP."""


class MailboxExists(Exception):
    """The user has already connected this login on this server."""


class MailboxSignInRefused(Exception):
    """The server refused the login or the password at the connect check."""


class MailboxServerUnreachable(Exception):
    """The server did not answer at the connect check."""

    def __init__(self, server: str) -> None:
        super().__init__("the mail server did not answer")
        self.server = server
