import torch

from brain.attention import causal_mask


def test_causal_mask_hides_future_positions() -> None:
    mask = causal_mask(4)
    expected = torch.tensor(
        [
            [False, True, True, True],
            [False, False, True, True],
            [False, False, False, True],
            [False, False, False, False],
        ]
    )
    assert torch.equal(mask, expected)
