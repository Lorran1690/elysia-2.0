import pytest
import torch
from brain.model import ElysiaTransformer,ModelConfig
from learning.foundation_preflight import architecture_count,benchmark


def test_meta_parameter_count_matches_real_small_architecture():
    config={'vocab_size':259,'block_size':64,'num_layers':1,'embedding_dim':16,
            'num_heads':2,'feedforward_dim':32,'positional_embedding':'rope',
            'norm_type':'rmsnorm','feedforward_type':'swiglu','attention_backend':'sdpa'}
    assert architecture_count(config)==ElysiaTransformer(ModelConfig(**config)).num_parameters()


def test_gpu_calibration_refuses_to_fall_back_to_cpu(monkeypatch):
    monkeypatch.setattr(torch.cuda,'is_available',lambda:False)
    with pytest.raises(RuntimeError,match='no CPU fallback'):
        benchmark({},2)


@pytest.mark.parametrize('steps,context,precision,reason',[
    (21,512,'auto','fixed budget'),
    (2,0,'auto','Unsupported calibration context'),
    (2,512,'invalid','Unknown precision'),
])
def test_invalid_calibration_is_rejected_before_gpu_allocation(monkeypatch,steps,context,precision,reason):
    # Mock only the availability check; these invalid requests never allocate a GPU model.
    monkeypatch.setattr(torch.cuda,'is_available',lambda:True)
    profile={'calibration':{'maximum_steps':20,'context':512},'model':{'block_size':2048}}
    with pytest.raises(ValueError,match=reason):
        benchmark(profile,steps,context=context,precision=precision)
