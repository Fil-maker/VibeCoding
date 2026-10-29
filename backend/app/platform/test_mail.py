"""Unit tests of the fake mail sender."""

import pytest

from app.platform.mail import FakeMailSender, MailDeliveryError, OutgoingEmail


def email(to: str = "anna@romashka.test") -> OutgoingEmail:
    """A small email."""
    return OutgoingEmail(to=to, subject="Тема", text="Текст")


async def test_fake_records_what_was_sent_in_order() -> None:
    sender = FakeMailSender()

    await sender.send(email("a@romashka.test"))
    await sender.send(email("b@romashka.test"))

    assert [sent.to for sent in sender.sent] == ["a@romashka.test", "b@romashka.test"]
    assert sender.sent[0].subject == "Тема"
    assert sender.sent[0].text == "Текст"


async def test_fail_next_fails_exactly_that_many_sends_then_recovers() -> None:
    sender = FakeMailSender()
    sender.fail_next(2)

    with pytest.raises(MailDeliveryError):
        await sender.send(email())
    with pytest.raises(MailDeliveryError):
        await sender.send(email())
    await sender.send(email("c@romashka.test"))

    assert sender.sent[-1].to == "c@romashka.test"
