import re

# OpenAI-family keys: an `sk-` prefix followed by a long opaque token. The 20-char
# floor avoids redacting prose like "sk-123" while catching sk-proj / sk-harmony variants.
_SECRET_PATTERNS = (re.compile(r"sk-[A-Za-z0-9_-]{20,}"),)
_REDACTION = "[REDACTED-SECRET]"


def scrub_secrets(text: str) -> str:
    for pattern in _SECRET_PATTERNS:
        text = pattern.sub(_REDACTION, text)
    return text
