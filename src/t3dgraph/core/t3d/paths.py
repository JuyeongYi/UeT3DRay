"""DEPRECATED — core/base/paths로 이동(2026-05-21 batch ③ slice α).

batch ④에서 본 파일은 제거 예정. 신규 import는 모두 core/base/paths를 사용.
"""
from ..base.paths import (  # noqa: F401
    node_of,
    pin_segment,
    pin_rel_path,
    type_suffix,
)

__all__ = ["node_of", "pin_segment", "pin_rel_path", "type_suffix"]
