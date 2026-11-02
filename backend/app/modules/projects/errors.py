"""Domain errors of the projects module; the router maps them to HTTP."""


class ProjectExists(Exception):
    """The user already has a project whose name differs only in letter case."""


class ChainNotInProject(Exception):
    """The chain to take out is already out of projects or was never in one."""
