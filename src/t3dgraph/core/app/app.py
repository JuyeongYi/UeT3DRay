"""뷰어 진입점 — QApplication 조립."""
from __future__ import annotations
import sys
from PySide6.QtWidgets import QApplication
from .controller import AppController, load_ref
from .main_window import MainWindow


def main() -> None:
    app = QApplication(sys.argv)

    view_cls = MainWindow
    controller_cls = AppController

    window = view_cls()
    controller = controller_cls(window)
    window.set_open_handler(controller.open_file)
    window.show()

    if len(sys.argv) > 1:
        controller.open_file(sys.argv[1])

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
