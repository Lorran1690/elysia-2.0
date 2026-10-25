"""Persist explicit Codex review decisions; never pretend they are human reviews."""
from __future__ import annotations

import json
from pathlib import Path
import shutil

from learning.portuguese_corpus import DEST, ROOT, digest

DECISIONS = {
    "20937d41-2f17-4938-a5e8-b86068fcdd33": ("accepted_candidate", "Sugestão criativa pertinente; não reivindica acesso a ferramentas ou conhecimento privado."),
    "67268a8a-22eb-4b9d-aafa-2f3f9f442b63": ("pending_capability_alignment", "Boa distinção entre assistir e receber transcrição, mas a capacidade de resumo da Elysia ainda não foi demonstrada."),
    "5cdf35f9-e61f-460e-b689-4d415bcfcdf3": ("rejected_response_quality", "Oferece escrever tudo sem pedir o texto ou objetivo da revisão; resposta pouco adequada ao comportamento desejado."),
    "7d85933c-6d37-4f14-8981-892ce9eb6135": ("accepted_candidate", "Sugere brincadeiras pertinentes e simples, sem alegações factuais específicas não verificadas."),
    "a0ccaab6-fad0-4d01-871d-a7a209d5fe0c": ("pending_fact_verification", "Receita de Minecraft depende de tipo de laje e versão; não aceitar como instrução factual revisada sem referência."),
    "359c0497-0d62-4a5a-82fc-6ba84278319a": ("accepted_candidate", "Lista criativa atende ao uso de sublinhados solicitado; sem prometer exclusividade ou disponibilidade dos nomes."),
    "9ceb7765-ccbc-4f5d-9e2c-db41ef1de6a7": ("accepted_candidate", "Dez sugestões de nome pertinentes ao tema de aquários; não oferece orientação de manejo animal."),
    "42c65119-dd67-4356-96f8-7195aacff256": ("pending_dated_fact_verification", "Resposta epistemicamente cautelosa, mas afirma estado científico; precisa de referência datada antes de uso factual."),
    "96719377-17d3-452e-a4b9-0cf358cf0eb5": ("accepted_candidate", "Dez sugestões criativas pertinentes; reconhecer viés de listas e de entretenimento na seleção."),
    "c4fab12b-3e3a-4c2f-9667-276733a5f3a6": ("pending_scientific_review", "Simplifica uso e desuso e hereditariedade; não distingue alteração somática de transmissão hereditária."),
    "978154f4-9c29-4f52-9783-f0ad6a05eef0": ("rejected_incomplete_explanation", "Não explica a distinção de uso entre por que e por quê, que é central à pergunta."),
    "ab5687ce-2be0-42c5-8805-55ac6e2ff7af": ("rejected_factual_error", "Afirma que cães geralmente têm menos dentes que humanos e introduz faixa e anatomia incorretas; excluir."),
    "798cc2bf-2cec-4e7d-afc9-41ff55fcfed8": ("pending_historical_verification", "Cronologia de conde/reinado é internamente confusa e exige referência histórica; não aceitar sem checagem."),
    "d98918ed-1dbf-424f-b578-24fbc1c6e71c": ("rejected_unsupported_nutrition", "Dá calorias e proteína sem quantidades de ingredientes; não sustenta o limite de 200 calorias."),
    "cf0872ec-e587-4d5d-a163-2aa510ff1376": ("rejected_instruction_following", "Pergunta tudo bem e solicita apresentação no mesmo turno, apesar de pedido de uma pergunta por vez."),
    "dd36e2c7-5c9c-45ee-89d0-08339fcc3591": ("accepted_candidate", "Lista de nomes ficcionais atende à solicitação; não representa diversidade conversacional suficiente."),
}


def prepare(output=DEST / "dialogues"):
    if output.exists():
        raise ValueError("Review output already exists")
    source = ROOT / "data/language-pilot/train.json"
    if digest(source.read_bytes()) != "1921dc8e216e281ed82df46c8ae28b90dd678536d23e84a54ad20f7177dc3c82":
        raise ValueError("Source differs from reviewed historical training lot")
    by_id = {r["id"]: r for r in json.loads(source.read_text(encoding="utf-8"))}
    output.mkdir(parents=True)
    accepted, review = [], []
    for key, (decision, rationale) in DECISIONS.items():
        record = by_id[key]
        review.append({"id": key, "tree_id": record["tree_id"], "decision": decision, "rationale": rationale,
                       "messages_sha256": digest(json.dumps(record["messages"], ensure_ascii=False, sort_keys=True).encode())})
        if decision == "accepted_candidate":
            accepted.append({**record, "license": "Apache-2.0", "source": "OpenAssistant/oasst1",
                             "attribution": "OpenAssistant contributors / LAION-AI, 2023"})
    (output / "reviewed-candidates.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in accepted), encoding="utf-8")
    (output / "review-log.json").write_text(json.dumps(review, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.copy2(ROOT / "data/language-pilot/LICENSE-APACHE-2.0.txt", output / "LICENSE-APACHE-2.0.txt")
    manifest = {"source": "OpenAssistant/oasst1", "revision": "fdf72ae0827c1cda404aff25b6603abec9e3399b",
                "original_training_file_sha256": digest(source.read_bytes()), "reviewer": "Codex semantic review, not independent human review",
                "selection": "16 shortest complete examples from distinct historical training trees; length-biased sample",
                "reviewed": len(review), "accepted_candidates": len(accepted), "pending_or_rejected": len(review) - len(accepted),
                "candidate_file_sha256": digest((output / "reviewed-candidates.jsonl").read_bytes()),
                "previously_used_in_language_pilot": True, "new_human_conversations_collected": False,
                "eligible_as_broad_conversational_dataset": False, "neural_training_performed": False,
                "limits": ["Small creative-task concentration; not a conversational curriculum.",
                           "No held-out historical dialogue was moved into training.",
                           "Accepted examples are candidates for future tuning, not evidence of the model's abilities."]}
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEST / "dialogues")
    args = parser.parse_args()
    print(json.dumps(prepare(args.output), ensure_ascii=False, indent=2))
