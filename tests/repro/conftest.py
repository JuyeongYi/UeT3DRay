"""tests/repro fixtures — Orion 샘플 경로 주입·skip 가드."""
from __future__ import annotations
import os
from pathlib import Path

import pytest

from t3dgraph.core.t3d.document import T3DDocument, parse_document
from t3dgraph.core.t3d.encoding import read_t3d_text


def _orion_path() -> Path | None:
    env = os.environ.get("T3DGRAPH_ORION_SAMPLE")
    if env:
        p = Path(env)
        return p if p.exists() else None
    # 기본 1: tests/fixtures/orion/ 에서 RigVMModel 파일
    fixtures_orion = Path(__file__).resolve().parents[1] / "fixtures" / "orion"
    if fixtures_orion.exists():
        candidates = list(fixtures_orion.glob("*RigVMModel*.t3d.txt"))
        if candidates:
            return candidates[0]
        candidates = list(fixtures_orion.glob("*.t3d.txt"))
        if candidates:
            return candidates[0]
    # 기본 2: 레포 루트의 Orion_WorkStation_Rig_Analysis/.../sample.t3d.txt
    repo_root = Path(__file__).resolve().parents[2]
    candidates = list((repo_root / "Orion_WorkStation_Rig_Analysis").rglob("*.t3d.txt"))
    return candidates[0] if candidates else None


@pytest.fixture(scope="session")
def orion_sample_path() -> Path:
    p = _orion_path()
    if p is None:
        pytest.skip("Orion 샘플 미발견 (T3DGRAPH_ORION_SAMPLE 환경변수 또는 "
                    "Orion_WorkStation_Rig_Analysis/ 디렉터리 필요)")
    return p


@pytest.fixture(scope="session")
def orion_doc(orion_sample_path: Path) -> T3DDocument:
    text = read_t3d_text(orion_sample_path)
    return parse_document(text)
