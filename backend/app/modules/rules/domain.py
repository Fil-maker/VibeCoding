"""Pure logic of rules: the limit, what a rule matches and which rule wins."""

import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.modules.rules.schemas import RuleCondition

# A word is a run of letters and digits (the underscore is not one of them).
_WORD = re.compile(r"[^\W_]+")
RULE_LIMIT = 200
_PRIORITY = {RuleCondition.ADDRESS: 0, RuleCondition.DOMAIN: 1, RuleCondition.SUBJECT: 2}


@dataclass(frozen=True)
class MatchRule:
    """A rule as the matching reads it; `value` is as stored (normalised on input)."""

    id: UUID
    condition: RuleCondition
    value: str
    project_id: UUID
    thread_name: str | None
    created_at: datetime


def priority_key(rule: MatchRule) -> tuple[int, datetime, UUID]:
    """The total order in which rules win: address, domain, subject words; then older; then id."""
    return (_PRIORITY[rule.condition], rule.created_at, rule.id)


def subject_words(text: str) -> list[str]:
    """Words of a subject: lower case, «ё» read as «е», split on anything but letters and digits."""
    return _WORD.findall(text.lower().replace("ё", "е"))


def _matches_domain(sender: str, domain: str) -> bool:
    host = sender.rpartition("@")[2]
    return bool(host) and (host == domain or host.endswith("." + domain))


def _matches(rule: MatchRule, senders: Sequence[str], subject: str) -> bool:
    value = rule.value.lower()
    if rule.condition is RuleCondition.ADDRESS:
        return any(sender.lower() == value for sender in senders)
    if rule.condition is RuleCondition.DOMAIN:
        return any(_matches_domain(sender.lower(), value) for sender in senders)
    wanted = subject_words(rule.value)
    if not wanted:
        return False
    words = subject_words(subject)
    return all(any(word.startswith(part) for word in words) for part in wanted)


def winning_rule(
    rules: Sequence[MatchRule], senders: Sequence[str], subject: str
) -> MatchRule | None:
    """The first matching rule in priority order, whatever order `rules` come in."""
    for rule in sorted(rules, key=priority_key):
        if _matches(rule, senders, subject):
            return rule
    return None
