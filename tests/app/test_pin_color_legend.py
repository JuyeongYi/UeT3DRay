"""u3 — PinColorLegendDialog 단위."""
from PySide6.QtWidgets import QTableWidget

from t3dgraph.core.app.pin_colors import PinColorTable
from t3dgraph.core.app.pin_color_legend import PinColorLegendDialog


def test_dialog_shows_palette_rows(qtbot, tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(PinColorTable, "_user_dir",
                        classmethod(lambda cls: tmp_path))
    table = PinColorTable.load()
    dlg = PinColorLegendDialog(table)
    qtbot.addWidget(dlg)
    palette_table = dlg.findChild(QTableWidget, "palette_table")
    assert palette_table is not None
    assert palette_table.rowCount() == len(table._palette)


def test_dialog_shows_bucket_rows(qtbot, tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(PinColorTable, "_user_dir",
                        classmethod(lambda cls: tmp_path))
    table = PinColorTable.load()
    dlg = PinColorLegendDialog(table)
    qtbot.addWidget(dlg)
    bucket_table = dlg.findChild(QTableWidget, "bucket_table")
    assert bucket_table is not None
    assert bucket_table.rowCount() == len(table._bucket)


def test_dialog_is_non_modal(qtbot, tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(PinColorTable, "_user_dir",
                        classmethod(lambda cls: tmp_path))
    dlg = PinColorLegendDialog(PinColorTable.load())
    qtbot.addWidget(dlg)
    assert dlg.isModal() is False
