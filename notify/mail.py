"""Sending email through AgentMail (C-09). The SDK is imported only when a real send happens, so
the website and the tests never need it — it lives in the ``alerts`` dependency group."""


class AgentMailSender:
    def __init__(self, api_key: str, inbox_id: str):
        from agentmail import AgentMail

        self.client, self.inbox_id = AgentMail(api_key=api_key), inbox_id

    def send(self, to: str, subject: str, text: str, html: str, key: str) -> None:
        # the idempotency key makes a re-run of the same update deliver nothing new (EC-58)
        self.client.inboxes.messages.send(
            self.inbox_id, to=to, subject=subject, text=text, html=html, idempotency_key=key
        )


class PrintSender:
    """A dry run: the emails on standard output, nothing sent (EC-59)."""

    def send(self, to: str, subject: str, text: str, html: str, key: str) -> None:
        print(f"To: {to}\nSubject: {subject}\nKey: {key}\n\n{text}\n")
