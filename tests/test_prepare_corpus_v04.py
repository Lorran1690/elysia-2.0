from learning.prepare_corpus_v04 import clean_gutenberg_text


def test_gutenberg_cleaner_removes_only_technical_wrappers() -> None:
    raw = (
        "technical header\n"
        "*** START OF THE PROJECT GUTENBERG EBOOK TEST ***\n"
        "Título\n\nTexto com ação.\n"
        "*** END OF THE PROJECT GUTENBERG EBOOK TEST ***\n"
        "license footer\n"
    )
    cleaned = clean_gutenberg_text(raw)
    assert cleaned == "Título\n\nTexto com ação.\n"
    assert "technical header" not in cleaned
    assert "license footer" not in cleaned
