"""Domain errors of the attachments module; the router maps them to HTTP."""


class AttachmentMailboxDisconnected(Exception):
    """No connected mailbox of the user holds a copy of the email."""


class AttachmentEmailGone(Exception):
    """Every connected copy of the email is gone from its mailbox."""


class AttachmentSignInFailed(Exception):
    """The server refused the sign-in while fetching the attachment."""


class AttachmentServerUnreachable(Exception):
    """The server did not answer while fetching the attachment."""
