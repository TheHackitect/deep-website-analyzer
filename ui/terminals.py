# ui/terminals.py
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QLabel
from PyQt6.QtGui import QTextCursor  # Ensure QTextCursor is imported
from PyQt6.QtCore import QTimer, Qt
import json
from utils.json_utils import serialize_json


class TerminalWidget(QWidget):
    def __init__(self, mode="colorful", typing_speed=50, logger=None, max_lines=1000):
        super().__init__()
        self.logger = logger
        self.layout = QVBoxLayout()
        self.label = QLabel("Terminal Output")  # Label for the terminal
        self.label.setStyleSheet("font-weight: bold;")
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setStyleSheet("""
            QTextEdit {
                background-color: black;
                color: white;
                font-family: Consolas, 'Courier New', monospace;
                font-size: 12pt;
            }
        """)
        self.layout.addWidget(self.label)
        self.layout.addWidget(self.text_edit)
        self.setLayout(self.layout)

        self.typing_speed = typing_speed
        self.char_interval = max(1, 1000 // self.typing_speed)  # milliseconds per character
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_text)
        self.buffer = ""
        self.data = {}
        self.current_text = ""
        self.collected_data = {}
        self.auto_scroll = True  # Flag to control auto-scrolling
        self.max_lines = max_lines
        self.line_count = 0  # To keep track of the number of lines

        self.typing_enabled = True  # Flag for typing effect

        self.current_index = 0

        # Connect scrollbar to control auto-scroll
        self.text_edit.verticalScrollBar().valueChanged.connect(self.handle_scroll)

    def toggle_typing(self, enabled: bool):
        """Toggle the typing effect."""
        self.typing_enabled = enabled
        if not enabled and self.timer.isActive():
            # If typing is disabled during typing, finish typing immediately
            self.timer.stop()
            remaining_text = self.buffer[self.current_index:]
            self.current_text += remaining_text
            self.text_edit.setHtml(self.current_text)  # Correctly update text_edit
            self.buffer = ""
            self.current_index = 0
            if self.logger:
                self.logger.debug("Typing effect disabled. Rendered remaining text instantly.")

    def handle_scroll(self, value):
        # Check if scrollbar is at the bottom
        scroll_bar = self.text_edit.verticalScrollBar()
        if value < scroll_bar.maximum():
            self.auto_scroll = False
        else:
            self.auto_scroll = True

    def append_text(self, text: str, color: str = "white"):
        # Add color formatting and typewriting effect with newline
        colored_text = f'<span style="color:{color}">{text}</span><br>'
        self.buffer += colored_text
        if not self.timer.isActive():
            self.timer.start(self.char_interval)
        if self.logger:
            self.logger.debug(f"Appended text: {text}")

    def append_json(self, plugin_name: str, data: dict):
        """Append JSON result in a table format."""
        self.data[plugin_name] = data  # Store data for export
        # Format JSON data in a tabular form with color
        table_html = f"<h3 style='color:#4CAF50;'>{plugin_name} Results</h3><table border='1' cellspacing='0' cellpadding='5' style='color: white;'>"
        table_html += "<tr style='background-color:#333;'><th>Key</th><th>Value</th></tr>"
        for key, value in data.items():
            # Serialize the value using the custom serializer
            try:
                serialized_value = serialize_json(value)
            except TypeError as e:
                serialized_value = f"Unserializable data: {str(e)}"
            table_html += f"<tr><td>{key}</td><td>{serialized_value}</td></tr>"
        table_html += "</table><br>"
        self.buffer += table_html
        if self.typing_enabled:
            if not self.timer.isActive():
                self.timer.start(self.char_interval)
        else:
            self.append_html(table_html)
            if self.logger:
                self.logger.debug("Typing effect is disabled. Rendered content instantly.")
        if self.logger:
            self.logger.debug(f"Appended JSON data for plugin: {plugin_name}")

    def update_text(self):
        if self.buffer:
            next_char = self.buffer[0]
            self.current_text += next_char
            self.text_edit.setHtml(self.current_text)
            self.buffer = self.buffer[1:]
            # Auto-scroll only if enabled
            if self.auto_scroll:
                self.text_edit.verticalScrollBar().setValue(
                    self.text_edit.verticalScrollBar().maximum()
                )
            # Count lines and remove old lines if exceeding max_lines
            self.line_count = self.current_text.count('<br>')
            if self.line_count > self.max_lines:
                # Remove first half of the lines
                half_lines = self.max_lines // 2
                # Split by <br> to get lines
                lines = self.current_text.split('<br>')
                # Remove first half
                lines = lines[half_lines:]
                # Reconstruct the HTML
                self.current_text = '<br>'.join(lines)
                self.text_edit.setHtml(self.current_text)
        else:
            self.timer.stop()

    def get_all_data(self):
        return self.data  # Return the data containing analysis results

    def append_html(self, html: str):
        """Append HTML content to the text edit."""
        self.text_edit.moveCursor(QTextCursor.MoveOperation.End)  # Corrected
        self.text_edit.insertHtml(html)
        self.text_edit.moveCursor(QTextCursor.MoveOperation.End)  # Corrected
        self.text_edit.ensureCursorVisible()  # Corrected

    def clear(self):
        self.current_text = ""
        self.buffer = ""
        self.text_edit.clear()
        self.data = {}
        self.line_count = 0
        if self.logger:
            self.logger.debug("Terminal cleared.")