"""Domain errors of the rules module; the router maps them to HTTP."""


class RuleExists(Exception):
    """The user already has a rule with this condition and a value that differs only in case."""


class TooManyRules(Exception):
    """The user already has the most rules allowed."""
