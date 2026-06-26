"""L1 behavior model tests for ThorTensorCore."""

import pytest

from thor_gpu.modules.tensor_core import tc_mma_reference
from thor_gpu.modules.common.utils import (
    _pack_i8_matrix, _unpack_i32_matrix,
)


class TestTensorCoreBehavior:
    def test_identity_matrix(self):
        I = [[1 if i == j else 0 for j in range(8)] for i in range(8)]
        X = [[i * 8 + j for j in range(8)] for i in range(8)]
        res = tc_mma_reference(_pack_i8_matrix(I), _pack_i8_matrix(X), acc_en=0)["result"]
        assert _unpack_i32_matrix(res) == X  # I * X = X

    def test_all_ones_self_product(self):
        ones = [[1] * 8 for _ in range(8)]
        res = tc_mma_reference(_pack_i8_matrix(ones), _pack_i8_matrix(ones), acc_en=0)["result"]
        # each element = sum of 8 ones = 8
        m = _unpack_i32_matrix(res)
        assert m == [[8] * 8 for _ in range(8)]

    def test_negative_int8(self):
        neg = [[-1] * 8 for _ in range(8)]
        ones = [[1] * 8 for _ in range(8)]
        res = tc_mma_reference(_pack_i8_matrix(neg), _pack_i8_matrix(ones), acc_en=0)["result"]
        m = _unpack_i32_matrix(res)
        # _unpack_i32_matrix returns signed values; -1*1 summed 8x = -8.
        assert m == [[-8] * 8 for _ in range(8)]

    def test_accumulate(self):
        ones = [[1] * 8 for _ in range(8)]
        c = [[100] * 8 for _ in range(8)]
        from thor_gpu.modules.common.utils import _pack_i32_matrix
        res = tc_mma_reference(_pack_i8_matrix(ones), _pack_i8_matrix(ones),
                               _pack_i32_matrix(c), acc_en=1)["result"]
        m = _unpack_i32_matrix(res)
        assert m == [[108] * 8 for _ in range(8)]  # 8 + 100

    def test_no_accumulate(self):
        ones = [[1] * 8 for _ in range(8)]
        c = [[100] * 8 for _ in range(8)]
        from thor_gpu.modules.common.utils import _pack_i32_matrix
        res = tc_mma_reference(_pack_i8_matrix(ones), _pack_i8_matrix(ones),
                               _pack_i32_matrix(c), acc_en=0)["result"]
        m = _unpack_i32_matrix(res)
        assert m == [[8] * 8 for _ in range(8)]  # c ignored


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
