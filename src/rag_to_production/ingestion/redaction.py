import re

# OpenAI-family keys: `sk-`, an optional account-type label, then a long base62 token.
# The left boundary stops `sk-` matching inside hyphenated prose ("risk-", "ask-", "task-");
# base62 (no `-`/`_`) is the key body's real charset and keeps hyphenated slugs out.
_SECRET_PATTERNS = (re.compile(r"(?<![A-Za-z0-9])sk-(?:proj-|svcacct-|admin-)?[A-Za-z0-9]{20,}"),)
_REDACTION = "[REDACTED-SECRET]"


def scrub_secrets(text: str) -> str:
    for pattern in _SECRET_PATTERNS:
        text = pattern.sub(_REDACTION, text)
    return text
