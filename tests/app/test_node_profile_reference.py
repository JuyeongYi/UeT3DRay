"""u4 — NodeProfileReferenceDialog 단위."""
from PySide6.QtWidgets import QTableWidget

from t3dgraph.core.app.node_profiles import NodeProfileTable
from t3dgraph.core.app.node_profile_reference import NodeProfileReferenceDialog


def test_dialog_shows_profile_rows(qtbot, tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(NodeProfileTable, "_user_dir",
                        classmethod(lambda cls: tmp_path))
    table = NodeProfileTable.load()
    dlg = NodeProfileReferenceDialog(table)
    qtbot.addWidget(dlg)
    profile_table = dlg.findChild(QTableWidget, "profile_table")
    assert profile_table is not None
    # 번들에 정의된 6개 클래스 (Variable·Collapse·FunctionRef·Entry·Return·Reroute)
    assert profile_table.rowCount() == len(table._by_suffix)


def test_dialog_columns(qtbot, tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(NodeProfileTable, "_user_dir",
                        classmethod(lambda cls: tmp_path))
    dlg = NodeProfileReferenceDialog(NodeProfileTable.load())
    qtbot.addWidget(dlg)
    profile_table = dlg.findChild(QTableWidget, "profile_table")
    # 컬럼: 클래스 suffix + 5 필드
    assert profile_table.columnCount() == 6


def test_dialog_non_modal(qtbot, tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(NodeProfileTable, "_user_dir",
                        classmethod(lambda cls: tmp_path))
    dlg = NodeProfileReferenceDialog(NodeProfileTable.load())
    qtbot.addWidget(dlg)
    assert dlg.isModal() is False
