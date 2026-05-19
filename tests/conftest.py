from pathlib import Path
import pytest

FIXTURES = Path(__file__).parent / "fixtures"
ORION = FIXTURES / "orion"


@pytest.fixture
def orion_dir() -> Path:
    """11개 실제 .t3d.txt 파일이 있는 디렉터리."""
    return ORION
