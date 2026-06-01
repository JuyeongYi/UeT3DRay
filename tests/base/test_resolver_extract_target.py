"""α (ρ-A1) — UE ref 경로 추출 정규식 강도."""
from __future__ import annotations
from t3dgraph.core.t3d.resolver import AssetResolver

def test_extract_class_pattern() -> None:
    r = AssetResolver()
    assert r._extract_target_path("Class'/Game/Lib.Lib:RigVMModel.F'") == "/Game/Lib.Lib:RigVMModel.F"

def test_extract_redirect_chain_takes_last_quoted() -> None:
    r = AssetResolver()
    raw = "Redirect'/Old.Old:RigVMModel.G'->'/Game/Lib.Lib:RigVMModel.F'"
    assert r._extract_target_path(raw) == "/Game/Lib.Lib:RigVMModel.F"

def test_extract_class_pattern_in_redirect() -> None:
    r = AssetResolver()
    raw = "Redirect'/Old.Old:RigVMModel.G'->'Class'/Game/Lib.Lib:RigVMModel.F''"
    assert r._extract_target_path(raw) == "/Game/Lib.Lib:RigVMModel.F"

def test_extract_raw_path_no_quotes() -> None:
    r = AssetResolver()
    assert r._extract_target_path("/Game/Lib.Lib:RigVMModel.F") == "/Game/Lib.Lib:RigVMModel.F"

def test_extract_invalid_returns_none() -> None:
    assert AssetResolver()._extract_target_path("not a ref") is None

def test_extract_empty_string() -> None:
    assert AssetResolver()._extract_target_path("") is None
