"""
widgets.py
----------
Shared custom widgets used across the application.
"""

from PySide6.QtWidgets import QComboBox


class StyledComboBox(QComboBox):
    """
    A QComboBox that forces white text in its dropdown popup,
    bypassing Windows/system theme overrides that QSS can't fix.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.view().setStyleSheet(
            "background-color: #ffffff;"
            "color: #000000;"
            "padding: 2px 4px;"
        )
