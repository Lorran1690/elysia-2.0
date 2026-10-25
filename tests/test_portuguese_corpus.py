import json
import shutil
import subprocess

import pytest

from learning.audit_portuguese_corpus import audit
from learning.corpus_tokenizer import prepare as prepare_tokenizer, rows, sha_file
from learning.portuguese_corpus import DEST, PII, ROOT, digest, mdn_prose, portuguese_paragraph, rst_prose, topic_group


def test_markdown_extraction_keeps_reference_terms_but_excludes_code_and_images():
    source = '''---
title: Teste
---
{{APIRef("HTTP")}}
O cabeçalho {{HTTPHeader("Content-Type")}} informa o tipo do recurso e pode ser usado nas respostas do servidor.

O valor `null` indica que a informação não está disponível e precisa ser verificada pelo programa.

```js
secret_code_should_not_be_in_prose();
```

![imagem que não faz parte do texto](https://example.org/image.png)
'''
    title, paragraphs = mdn_prose(source)
    text = " ".join(paragraphs)
    assert title == "Teste"
    assert "Content-Type" in text and "null" in text
    assert "secret_code_should_not" not in text and "image.png" not in text and "APIRef" not in text


def test_rst_code_rejection_and_language_checks():
    assert rst_prose("Exemplo::\n\n    print('código')") is None
    assert rst_prose(".. code-block:: python\n    x = 1") is None
    assert "cmd" in rst_prose("Você pode procurar por ``cmd`` para abrir o terminal do Windows.")
    assert portuguese_paragraph("Esta documentação explica como você pode organizar os arquivos de uma pasta para facilitar o trabalho.")
    assert not portuguese_paragraph("The statement ensures that the code will be executed when the object is released by the application.")


def test_topic_groups_keep_api_families_and_whole_books_together():
    assert topic_group("mdn", "web/api/window/open/index.md") == topic_group("mdn", "web/api/window/close/index.md")
    assert topic_group("mdn", "web/javascript/reference/global_objects/array/map/index.md") == topic_group("mdn", "web/javascript/reference/global_objects/array/filter/index.md")
    assert topic_group("python", "library/asyncio-eventloop.po") == topic_group("python", "library/asyncio-task.po")
    assert topic_group("python", "tutorial/introduction.po") == topic_group("python", "tutorial/classes.po")
    assert topic_group("enap", "chapter-1") == topic_group("enap", "chapter-2")


@pytest.mark.parametrize("text", ["contato@exemplo.com", "111.444.777-35", "(11) 99999-1234"])
def test_identifier_patterns_are_detected(text):
    assert PII.search(text)


def test_fast_bpe_is_fit_on_train_only_and_exports_losslessly(tmp_path):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    content = {"train": "Uma frase sobre café e arquivos. " * 40,
               "validation": "zzzzzzzzzzzzzzzzzzzz café",
               "test": "zzzzzzzzzzzzzzzzzzzz outra frase"}
    partitions = {}
    for split, text in content.items():
        record = {"id": split, "family": "fixture", "group_id": split, "text": text, "sha256": digest(text.encode())}
        path = corpus / f"{split}.jsonl"
        path.write_text(json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8")
        partitions[split] = {"sha256": sha_file(path)}
    (corpus / "manifest.json").write_text(json.dumps({"partitions": partitions}))
    result = prepare_tokenizer(corpus, 512)
    from brain.bpe_tokenizer import ByteBPETokenizer
    tokenizer = ByteBPETokenizer.load(corpus / "tokenizer/elysia-bpe.json")
    assert b"zz" not in tokenizer._token_bytes  # Frequent held-out text never fitted.
    assert result["fit_partition"] == "train only"
    assert result["all_documents_round_trip_checked"]
    for text in content.values():
        assert tokenizer.decode(tokenizer.encode(text)) == text


def test_actual_corpus_audit_separates_integrity_from_general_conversation_readiness():
    result = audit()
    assert result["integrity_checks_passed"]
    assert result["documents_verified"] >= 2000
    assert result["cross_partition_group_overlap"] == 0
    assert result["cross_partition_exact_paragraph_overlap"] == 0
    assert result["total_bpe_tokens"] >= 2000000
    assert not result["ready_as_broad_conversation_corpus"]
    assert not result["neural_weights_updated"]


def test_audit_rejects_modified_manifest_even_if_still_valid_json(tmp_path):
    (tmp_path / "tokenizer").mkdir()
    shutil.copy2(DEST / "tokenizer/manifest.json", tmp_path / "tokenizer/manifest.json")
    (tmp_path / "manifest.json").write_bytes((DEST / "manifest.json").read_bytes() + b" ")
    with pytest.raises(ValueError, match="Source manifest hash mismatch"):
        audit(tmp_path)


def test_reviewed_dialogues_use_only_previous_training_trees_and_keep_gold_unconsumed():
    accepted = list(rows(DEST / "dialogues/reviewed-candidates.jsonl"))
    old_train = json.loads((ROOT / "data/language-pilot/train.json").read_text(encoding='utf-8'))
    heldout = json.loads((ROOT / "data/language-pilot/validation.json").read_text(encoding='utf-8')) + json.loads((ROOT / "data/language-pilot/test.json").read_text(encoding='utf-8'))
    assert len(accepted) == 6
    assert {r["id"] for r in accepted} <= {r["id"] for r in old_train}
    assert not {r["tree_id"] for r in accepted} & {r["tree_id"] for r in heldout}
    evaluation = json.loads((ROOT / "evaluation/portuguese-v1.json").read_text(encoding='utf-8'))
    assert len(evaluation["cases"]) == 24 and evaluation["evaluation_count"] == 0
    assert evaluation["not_for_training"]


def test_source_recovery_pins_revision_and_refuses_dirty_cache(tmp_path):
    from learning.fetch_corpus_sources import git_source
    original = tmp_path / "original"
    original.mkdir()
    subprocess.run(["git", "init", "--quiet"], cwd=original, check=True)
    (original / "files/pt-br").mkdir(parents=True)
    (original / "files/pt-br/example.md").write_text("Texto português de teste.")
    (original / "LICENSE.md").write_text("Public fixture license")
    subprocess.run(["git", "add", "."], cwd=original, check=True)
    subprocess.run(["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                    "commit", "--quiet", "-m", "fixture"], cwd=original, check=True)
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=original, text=True).strip()
    recovered = tmp_path / "recovered"
    git_source(recovered, str(original), revision, "files/pt-br")
    assert (recovered / "files/pt-br/example.md").read_text(encoding='utf-8') == "Texto português de teste."
    assert (recovered / "LICENSE.md").exists()
    git_source(recovered, str(original), revision, "files/pt-br")
    (recovered / "files/pt-br/example.md").write_text("Modificação que não pode ser sobrescrita.")
    with pytest.raises(ValueError, match="will not overwrite"):
        git_source(recovered, str(original), revision, "files/pt-br")


def test_prepared_store_loads_into_existing_batch_contract_without_resplitting():
    import torch
    from learning.dataset import make_batch
    from learning.prepared_corpus import load_partition
    store = load_partition("train", for_training=True)
    x, y = make_batch(store, batch_size=2, block_size=32, device=torch.device("cpu"),
                      generator=torch.Generator().manual_seed(13))
    assert x.shape == y.shape == (2, 32)
    assert int(x.min()) >= 0 and int(x.max()) < 2048
    assert torch.equal(x[:, 1:], y[:, :-1])


def test_prepared_store_refuses_heldout_partition_for_weight_updates():
    from learning.prepared_corpus import load_partition
    with pytest.raises(ValueError, match="Only train"):
        load_partition("test", for_training=True)
    with pytest.raises(ValueError, match="Unknown partition"):
        load_partition("../test")
