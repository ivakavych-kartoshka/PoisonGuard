import numpy as np
import pytest
from poisonguard.models.adapters import apply_lora


def test_lora_equation_and_dimensions() -> None:
    w = np.zeros((2, 3)); a = np.ones((1, 3)); b = np.ones((2, 1))
    assert np.allclose(apply_lora(w, a, b, 2), np.full((2, 3), 2.0))
    with pytest.raises(ValueError):
        apply_lora(w, np.ones((2, 4)), b, 1)
