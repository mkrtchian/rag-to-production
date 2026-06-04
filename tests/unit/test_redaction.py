import pytest

from rag_to_production.ingestion.redaction import scrub_secrets

_LEGACY_KEY = "sk-" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8S9t0U1v2"
_PROJECT_KEY = "sk-proj-" + "Ab12Cd34Ef56Gh78Ij90Kl12Mn34"
_SERVICE_KEY = "sk-svcacct-" + "Zy98Xw76Vu54Ts32Rq10Po98Nm76"


def test_redacts_an_openai_key_keeping_the_surrounding_text():
    text = f'os.environ["OPENAI_API_KEY"] = "{_LEGACY_KEY}" then run it'

    scrubbed = scrub_secrets(text)

    assert _LEGACY_KEY not in scrubbed
    assert scrubbed == 'os.environ["OPENAI_API_KEY"] = "[REDACTED-SECRET]" then run it'


@pytest.mark.parametrize("key", [_LEGACY_KEY, _PROJECT_KEY, _SERVICE_KEY])
def test_redacts_every_openai_key_shape(key: str):
    assert scrub_secrets(f"here is {key} ok") == "here is [REDACTED-SECRET] ok"


def test_redacts_every_key_in_a_thread():
    text = f"first {_LEGACY_KEY} middle {_PROJECT_KEY} last"

    scrubbed = scrub_secrets(text)

    assert "sk-" not in scrubbed
    assert scrubbed.count("[REDACTED-SECRET]") == 2


def test_leaves_ordinary_prose_untouched():
    text = "The sk- prefix alone, or a short sk-123 token, is not a key."

    assert scrub_secrets(text) == text


def test_leaves_hyphenated_prose_untouched():
    text = "risk-assessment-framework-for-production-agents and ask-the-model-to-think-first"

    assert scrub_secrets(text) == text
