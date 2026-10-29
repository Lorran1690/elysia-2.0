"""Export project-owned weights to a portable little-endian float32 bundle.

This is an interchange artifact, not an Android inference runtime.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from learning.generate_text import load_inference_checkpoint


def export(checkpoint, tokenizer, output):
    torch.set_num_threads(2)
    model, vocabulary = load_inference_checkpoint(checkpoint, device=torch.device('cpu'), tokenizer_path=tokenizer)
    output.mkdir(parents=True, exist_ok=True)
    entries = []
    data = bytearray()
    for name, tensor in model.state_dict().items():
        values = tensor.detach().cpu().float().numpy().astype('<f4')
        if not np.isfinite(values).all():
            raise ValueError('Nonfinite weights: ' + name)
        payload = values.tobytes(order='C')
        entries.append({'name': name, 'shape': list(values.shape), 'offset': len(data), 'bytes': len(payload)})
        data.extend(payload)
    # Validate every tensor by reconstructing the exported byte representation.
    restored = {}
    for entry in entries:
        values = np.frombuffer(data, dtype='<f4', count=entry['bytes']//4, offset=entry['offset']).copy().reshape(entry['shape'])
        restored[entry['name']] = torch.from_numpy(values)
        assert torch.equal(restored[entry['name']], model.state_dict()[entry['name']].float())
    model.load_state_dict(restored, strict=True)
    source_hash = hashlib.file_digest(Path(checkpoint).open('rb'), 'sha256').hexdigest()
    manifest = {'format': 'elysia-mobile-tensors-v1', 'dtype': 'float32', 'byte_order': 'little',
                'model_config': model.config_dict(), 'tokenizer': vocabulary.metadata(),
                'checkpoint_sha256': source_hash, 'weights': {'file': 'weights.bin', 'bytes': len(data),
                'sha256': hashlib.sha256(data).hexdigest()}, 'tensors': entries,
                'all_tensors_exact_roundtrip': True, 'android_inference_verified': False,
                'conversation_quality_improved': False}
    (output/'weights.bin').write_bytes(data)
    (output/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print(json.dumps({'tensor_count': len(entries), 'weights_bytes': len(data), 'exact_roundtrip': True}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkpoint', type=Path, default=Path('artifacts/aira-dialogue-v1/run-001/sft-model.pt'))
    parser.add_argument('--tokenizer', type=Path, default=Path('data/corpus-pt-v1/tokenizer/elysia-bpe.json'))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    export(args.checkpoint, args.tokenizer, args.output)
