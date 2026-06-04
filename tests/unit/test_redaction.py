from rag_to_production.ingestion.redaction import scrub_secrets


def test_redacts_an_openai_key_keeping_the_surrounding_text():
    text = 'os.environ["OPENAI_API_KEY"] = "sk-aaaa_FAKE_TEST_KEY_bbbbbbbbbb" then run it'

    scrubbed = scrub_secrets(text)

    assert "FAKE_TEST_KEY" not in scrubbed
    assert scrubbed.startswith('os.environ["OPENAI_API_KEY"] = "')
    assert scrubbed.endswith('" then run it')


def test_redacts_every_key_in_a_thread():
    text = "first sk-cccc_ANOTHER_FAKE_dddddddddd middle sk-eeee_THIRD_FAKE_ffffffffffff last"

    scrubbed = scrub_secrets(text)

    assert "sk-" not in scrubbed
    assert scrubbed.count("[REDACTED-SECRET]") == 2


def test_leaves_ordinary_prose_untouched():
    text = "The sk- prefix alone, or a short sk-123 token, is not a key."

    assert scrub_secrets(text) == text
