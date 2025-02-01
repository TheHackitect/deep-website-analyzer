# ui/main_window.py
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QSlider,
    QLabel, QTableWidget, QTableWidgetItem, QHeaderView, QSplitter, QMessageBox, QFileDialog,
    QLineEdit, QAbstractItemView, QInputDialog, QColorDialog, QScrollArea, QGroupBox, QGridLayout,
    QSizePolicy, QDialog
)


from PyQt6.QtCore import Qt, pyqtSlot, QSize
from utils.plugin_loader import load_plugins
from plugins.base_plugin import BasePlugin
import os
import shutil
import json
from PyQt6.QtPrintSupport import QPrinter
from PyQt6.QtGui import QPixmap
from ui.terminals import TerminalWidget
from PyQt6.QtCore import QThread, pyqtSignal
from utils.json_utils import serialize_json, generate_session_id
from datetime import datetime
import re
import requests


class AnalysisThread(QThread):
    progress = pyqtSignal(str, str)  # message, color
    result = pyqtSignal(str, dict)  # plugin_name, result
    finished = pyqtSignal()

    def __init__(self, plugins, target, logger=None):
        super().__init__()
        self.plugins = plugins
        self.target = target
        self.logger = logger
        self._terminate = False  # Termination flag

    def run(self):
        if self.logger:
            self.logger.info(f"Analysis thread started for target: {self.target}")
        for plugin in self.plugins:
            if self._terminate:
                self.progress.emit("Analysis terminated by user.", "red")
                if self.logger:
                    self.logger.info("Analysis thread terminated by user.")
                self.finished.emit()
                return
            message = f"Running {plugin.name}..."
            self.progress.emit(message, "cyan")
            if self.logger:
                self.logger.info(f"Running plugin: {plugin.name}")
            try:
                result = plugin.run(self.target)
                if self._terminate:
                    self.progress.emit("Analysis terminated by user.", "red")
                    if self.logger:
                        self.logger.info("Analysis thread terminated by user.")
                    self.finished.emit()
                    return
                self.result.emit(plugin.name, result)
                message = f"{plugin.name} completed."
                self.progress.emit(message, "green")
                if self.logger:
                    self.logger.info(f"Plugin '{plugin.name}' completed successfully.")
            except Exception as e:
                message = f"Error in {plugin.name}: {str(e)}"
                self.progress.emit(message, "red")
                if self.logger:
                    self.logger.error(f"Error in plugin '{plugin.name}': {str(e)}")
        if not self._terminate:
            self.progress.emit("Analysis completed.", "green")
            if self.logger:
                self.logger.info("Analysis thread finished.")
        self.finished.emit()

    def terminate_analysis(self):
        self._terminate = True


class ColorSelectionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Export Colors")
        self.selected_background_color = None
        self.selected_text_color = None

        layout = QVBoxLayout()

        # Background Color Selection
        bg_layout = QHBoxLayout()
        bg_label = QLabel("Background Color:")
        self.bg_button = QPushButton("Select Background Color")
        self.bg_button.clicked.connect(self.select_background_color)
        bg_layout.addWidget(bg_label)
        bg_layout.addWidget(self.bg_button)
        layout.addLayout(bg_layout)

        # Text Color Selection
        text_layout = QHBoxLayout()
        text_label = QLabel("Text Color:")
        self.text_button = QPushButton("Select Text Color")
        self.text_button.clicked.connect(self.select_text_color)
        text_layout.addWidget(text_label)
        text_layout.addWidget(self.text_button)
        layout.addLayout(text_layout)

        # Buttons
        buttons_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        cancel_btn = QPushButton("Cancel")
        save_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(save_btn)
        buttons_layout.addWidget(cancel_btn)
        layout.addLayout(buttons_layout)

        self.setLayout(layout)

    def select_background_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.selected_background_color = color.name()
            self.bg_button.setStyleSheet(f"background-color: {self.selected_background_color}")
            self.bg_button.setText(self.selected_background_color)

    def select_text_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.selected_text_color = color.name()
            self.text_button.setStyleSheet(f"background-color: {self.selected_text_color}")
            self.text_button.setText(self.selected_text_color)

class MainWindow(QMainWindow):
    CONFIG_FILE = "config.json"
    CACHE_DIR = "cache"  # Directory to store cached sessions

    def __init__(self, logger=None):
        super().__init__()
        self.logger = logger
        self.setWindowTitle("Deep Website Analyzer")
        self.resize(1250, 750)  # Reduced size for user adjustment
        self.center_window()
        self.typing_speed_label = QLabel("Terminal Typing Speed: 50")

        # Load config
        self.api_keys = self.load_config()

        # Ensure the cache directory exists
        if not os.path.exists(self.CACHE_DIR):
            os.makedirs(self.CACHE_DIR)
            if self.logger:
                self.logger.info(f"Cache directory created at {self.CACHE_DIR}")

        # Main Widget and Layout
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

        # Main Splitter between Left and Right Panels
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_splitter.setStyleSheet("QSplitter::handle { background-color: black }")  # Blue splitter handles

        # Left Panel: Tools and Settings
        left_widget = QWidget()
        left_panel = QVBoxLayout()
        left_widget.setLayout(left_panel)

        # Right Panel: Input and Terminals
        right_widget = QWidget()
        right_layout = QVBoxLayout()
        right_widget.setLayout(right_layout)

        # Create scroll areas
        left_scroll_area = QScrollArea()
        left_scroll_area.setWidgetResizable(True)
        left_scroll_area.setWidget(left_widget)

        right_scroll_area = QScrollArea()
        right_scroll_area.setWidgetResizable(True)
        right_scroll_area.setWidget(right_widget)

        # Add scroll areas to main_splitter
        main_splitter.addWidget(left_scroll_area)
        main_splitter.addWidget(right_scroll_area)

        # Set the initial sizes of the panels
        main_splitter.setSizes([600, 800])  # Adjust the sizes as needed

        main_splitter.setStretchFactor(0, 1)
        main_splitter.setStretchFactor(1, 3)

        # Add main_splitter to main_layout
        main_layout.addWidget(main_splitter)

        # Left Panel Sections
        # Tools Section
        tools_label = QLabel("Available Tools")
        tools_label.setStyleSheet("font-weight: bold; font-size: 16px; border-bottom: 2px solid #000;")
        self.tools_table = QTableWidget()
        # Modify columns: Name, Description, Enable, Requires API, Edit API Keys
        self.tools_table.setColumnCount(5)
        self.tools_table.setHorizontalHeaderLabels(["Name", "Description", "Enable", "Requires API", "Edit API Keys"])
        self.tools_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.tools_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tools_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tools_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tools_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)  # Make table scalable
        self.tools_table.setMinimumHeight(200)

        # Search bar
        search_layout = QHBoxLayout()
        search_label = QLabel("Search:")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search tools...")
        self.search_input.textChanged.connect(self.filter_tools)
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_input)

        # Toggle All Button
        self.toggle_all_btn = QPushButton("Toggle All")
        self.toggle_all_btn.clicked.connect(self.toggle_all_tools)
        self.toggle_all_btn.setFixedWidth(150)

        # Tools Section Widget
        tools_section_widget = QWidget()
        tools_section_layout = QVBoxLayout()
        tools_section_layout.addWidget(tools_label)
        tools_section_layout.addLayout(search_layout)
        tools_section_layout.addWidget(self.tools_table)
        tools_section_layout.addWidget(self.toggle_all_btn)
        tools_section_widget.setLayout(tools_section_layout)

        # Settings Section
        settings_label = QLabel("Settings")
        settings_label.setStyleSheet("font-weight: bold; font-size: 16px; border-bottom: 2px solid #000;")

        # Create a grid layout for settings buttons
        settings_layout = QGridLayout()
        row = 0
        column = 0

        # Define settings buttons
        buttons = [
            ("Toggle Dark Mode", self.toggle_dark_mode),
            ("Terminal Typing Speed", None),  # Slider handled separately
            ("Export Data", self.export_data),
            ("Refresh Tools", self.refresh_tools),
            ("Clear Data", self.clear_data),
            ("Clear Logs", self.clear_logs),
            ("Clear Terminals", self.clear_terminals),
            ("Developer Contact", self.show_dev_contact),
            ("Terminate Analysis", self.terminate_analysis),  # New Terminate button
        ]

        # Typing Speed Slider and Label
        self.typing_speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.typing_speed_slider.setMinimum(10)
        self.typing_speed_slider.setMaximum(200)
        self.typing_speed_slider.setValue(100)  # Default value
        self.typing_speed_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.typing_speed_slider.setTickInterval(10)
        self.typing_speed_slider.valueChanged.connect(self.update_typing_speed)

        self.typing_speed_label = QLabel("Terminal Typing Speed: 100")
        self.typing_speed_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Add buttons to the grid layout
        for label, slot in buttons:
            if label == "Terminal Typing Speed":
                # Handle slider separately
                settings_layout.addWidget(self.typing_speed_label, row, column, 1, 2)
                settings_layout.addWidget(self.typing_speed_slider, row + 1, column, 1, 2)
                row += 2
                continue

            btn = QPushButton(label)
            btn.clicked.connect(slot)
            btn.setFixedWidth(150)
            settings_layout.addWidget(btn, row, column)
            column += 1
            if column > 1:
                column = 0
                row += 1

        # Typing Effect Toggle Button
        self.typing_toggle_btn = QPushButton("Disable Typing Effect")
        self.typing_toggle_btn.setCheckable(True)
        self.typing_toggle_btn.setChecked(True)  # Default is enabled
        self.typing_toggle_btn.clicked.connect(self.toggle_typing_effect)
        self.typing_toggle_btn.setFixedWidth(150)
        settings_layout.addWidget(self.typing_toggle_btn, row, column)
        column += 1
        if column > 1:
            column = 0
            row += 1

        # Settings Container
        settings_container = QWidget()
        settings_container.setLayout(settings_layout)

        # Settings Section Widget
        settings_section_widget = QWidget()
        settings_section_layout = QVBoxLayout()
        settings_section_layout.addWidget(settings_label)
        settings_section_layout.addWidget(settings_container)
        settings_section_widget.setLayout(settings_section_layout)

        # Cached Sessions Section
        cached_label = QLabel("Cached Analysis Sessions")
        cached_label.setStyleSheet("font-weight: bold; font-size: 16px; border-bottom: 2px solid #000;")

        # Create the Cached Sessions Table
        self.cached_table = QTableWidget()
        self.cached_table.setColumnCount(4)
        self.cached_table.setColumnWidth(3, 200)
        self.cached_table.setHorizontalHeaderLabels(["Session ID", "Target", "Timestamp", "Actions"])
        self.cached_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.cached_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.cached_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.cached_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.cached_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)  # Make table scalable
        self.cached_table.setMinimumHeight(150)

        # Populate the Cached Sessions Table
        self.load_cached_sessions()

        # Cached Sessions Section Widget
        cached_section_widget = QWidget()
        cached_section_layout = QVBoxLayout()
        cached_section_layout.addWidget(cached_label)
        cached_section_layout.addWidget(self.cached_table)
        cached_section_widget.setLayout(cached_section_layout)

        # Gallery Section in Settings
        gallery_label = QLabel("Detected Images Preview")
        gallery_label.setStyleSheet("font-weight: bold; font-size: 16px; border-bottom: 2px solid #000;")

        self.gallery_group = QGroupBox()
        self.gallery_layout = QGridLayout()
        self.gallery_group.setLayout(self.gallery_layout)

        # Scroll Area for Gallery
        self.gallery_scroll = QScrollArea()
        self.gallery_scroll.setWidgetResizable(True)
        self.gallery_scroll.setWidget(self.gallery_group)
        self.gallery_scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)  # Make gallery scalable
        self.gallery_scroll.setMinimumHeight(200)

        # Clear Gallery Button
        self.clear_gallery_btn = QPushButton("Clear Gallery")
        self.clear_gallery_btn.clicked.connect(self.clear_gallery)
        self.clear_gallery_btn.setFixedWidth(150)

        # Gallery Section Widget
        gallery_section_widget = QWidget()
        gallery_section_layout = QVBoxLayout()
        gallery_section_layout.addWidget(gallery_label)
        gallery_section_layout.addWidget(self.gallery_scroll)
        gallery_section_layout.addWidget(self.clear_gallery_btn)
        gallery_section_widget.setLayout(gallery_section_layout)

        # Left Splitter
        left_splitter = QSplitter(Qt.Orientation.Vertical)
        left_splitter.setStyleSheet("QSplitter::handle { background-color: black }")  # Blue splitter handles
        left_splitter.addWidget(tools_section_widget)
        left_splitter.addWidget(settings_section_widget)
        left_splitter.addWidget(cached_section_widget)
        left_splitter.addWidget(gallery_section_widget)
        

        # Add left_splitter to left_panel
        left_panel.addWidget(left_splitter)

        # Initialize image counter
        self.image_count = 0

        # Set max images per row
        self.max_images_per_row = 3

        # Create a list to keep track of image widgets
        self.image_widgets = []

        # Right Panel: Input and Terminals
        # Input Section
        input_layout = QHBoxLayout()
        self.target_input = QLineEdit()
        self.target_input.setPlaceholderText("Enter URL, IP, or Domain Name")
        self.run_btn = QPushButton("Run Analysis")
        self.run_btn.clicked.connect(self.run_analysis)
        self.run_btn.setFixedWidth(120)
        input_layout.addWidget(QLabel("Target:"))
        input_layout.addWidget(self.target_input)
        input_layout.addWidget(self.run_btn)

        right_layout.addLayout(input_layout)

        # Terminals Splitter
        terminals_splitter = QSplitter(Qt.Orientation.Vertical)
        terminals_splitter.setStyleSheet("QSplitter::handle { background-color: black }")  # Blue splitter handles

        # Terminal 1 (Log Output)
        terminal1_widget = QWidget()
        terminal1_layout = QVBoxLayout()
        terminal1_label = QLabel("Terminal 1 (Log Output)")
        terminal1_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.terminal1 = TerminalWidget(mode="colorful", typing_speed=50, logger=self.logger, max_lines=1000)
        terminal1_layout.addWidget(terminal1_label)
        terminal1_layout.addWidget(self.terminal1)
        terminal1_widget.setLayout(terminal1_layout)

        # Terminal 2 (Results)
        terminal2_widget = QWidget()
        terminal2_layout = QVBoxLayout()
        terminal2_label = QLabel("Terminal 2 (Results)")
        terminal2_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.terminal2 = TerminalWidget(mode="tabular", typing_speed=50, logger=self.logger, max_lines=1000)
        terminal2_layout.addWidget(terminal2_label)
        terminal2_layout.addWidget(self.terminal2)
        terminal2_widget.setLayout(terminal2_layout)

        # Add terminals to terminals_splitter
        terminals_splitter.addWidget(terminal1_widget)
        terminals_splitter.addWidget(terminal2_widget)
        terminals_splitter.setStretchFactor(0, 1)
        terminals_splitter.setStretchFactor(1, 1)

        # Add terminals_splitter to right_layout
        right_layout.addWidget(terminals_splitter)

        # Load Plugins
        self.load_plugins_into_table()

        # Initialize Analysis Thread
        self.analysis_thread = None

    def center_window(self):
        """Centers the window on the screen."""
        frame_gm = self.frameGeometry()
        screen = self.screen().availableGeometry().center()
        frame_gm.moveCenter(screen)
        self.move(frame_gm.topLeft())

    def toggle_all_tools(self):
        all_on = all(
            self.tools_table.cellWidget(row, 2).isChecked()
            for row in range(self.tools_table.rowCount())
        )
        new_state = not all_on
        for row in range(self.tools_table.rowCount()):
            btn = self.tools_table.cellWidget(row, 2)
            btn.setChecked(new_state)
            btn.setText("ON" if new_state else "OFF")

    def load_config(self):
        if os.path.exists(self.CONFIG_FILE):
            try:
                with open(self.CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                if self.logger:
                    self.logger.info("Configuration loaded successfully.")
                return config
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Failed to load configuration: {str(e)}")
                return {}
        else:
            return {}

    def save_config(self):
        try:
            with open(self.CONFIG_FILE, 'w') as f:
                json.dump(self.api_keys, f, indent=4)
            if self.logger:
                self.logger.info("Configuration saved successfully.")
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to save configuration: {str(e)}")

    def load_plugins_into_table(self):
        self.plugins = load_plugins('plugins', logger=self.logger)
        self.tools_table.setRowCount(len(self.plugins))
        for row, plugin in enumerate(self.plugins):
            name_item = QTableWidgetItem(plugin.name)
            name_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            desc_item = QTableWidgetItem(plugin.description)
            desc_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            
            # Enable toggle button
            toggle_btn = QPushButton("OFF")
            toggle_btn.setCheckable(True)
            toggle_btn.clicked.connect(self.toggle_tool)
            toggle_btn.setFixedWidth(60)

            # Check if plugin requires API keys
            requires_api = "Yes" if plugin.required_api_keys else "No"
            requires_api_item = QTableWidgetItem(requires_api)
            requires_api_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            requires_api_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            # Edit API Keys button
            edit_api_btn = QPushButton("Edit")
            edit_api_btn.setFixedWidth(60)
            edit_api_btn.clicked.connect(self.edit_api_keys)
            # Store the plugin's name in the button's property for reference
            edit_api_btn.setProperty("plugin_name", plugin.name)

            # Set tooltips
            name_item.setToolTip(plugin.description)
            desc_item.setToolTip(plugin.description)

            self.tools_table.setItem(row, 0, name_item)
            self.tools_table.setItem(row, 1, desc_item)
            self.tools_table.setCellWidget(row, 2, toggle_btn)
            self.tools_table.setItem(row, 3, requires_api_item)
            self.tools_table.setCellWidget(row, 4, edit_api_btn)

    def toggle_tool(self):
        button = self.sender()
        if not isinstance(button, QPushButton):
            return
        if button.isChecked():
            button.setText("ON")
            row = self.tools_table.indexAt(button.pos()).row()
            plugin = self.plugins[row]
            if plugin.required_api_keys:
                # Check if API keys are already provided
                if plugin.name in self.api_keys and all(k in self.api_keys[plugin.name] for k in plugin.required_api_keys):
                    pass  # API keys already provided
                else:
                    # Prompt user to enter API keys
                    keys = {}
                    for key_name in plugin.required_api_keys:
                        key, ok = QInputDialog.getText(self, "API Key Required", f"Enter API key for {key_name}:")
                        if ok and key:
                            keys[key_name] = key
                        else:
                            QMessageBox.warning(self, "API Key Missing", f"API key for {key_name} is required to enable this plugin.")
                            button.setChecked(False)
                            button.setText("OFF")
                            return
                    # Save the keys
                    self.api_keys[plugin.name] = keys
                    self.save_config()
            if self.logger:
                self.logger.info(f"Plugin '{plugin.name}' enabled.")
        else:
            button.setText("OFF")
            row = self.tools_table.indexAt(button.pos()).row()
            plugin = self.plugins[row]
            # Optionally, remove API keys when plugin is disabled
            # Or keep them for future use
            # self.api_keys.pop(plugin.name, None)
            # self.save_config()
            if self.logger:
                self.logger.info(f"Plugin '{plugin.name}' disabled.")

    def edit_api_keys(self):
        button = self.sender()
        if not isinstance(button, QPushButton):
            return
        plugin_name = button.property("plugin_name")
        if not plugin_name:
            return
        plugin = next((p for p in self.plugins if p.name == plugin_name), None)
        if not plugin or not plugin.required_api_keys:
            QMessageBox.information(self, "No API Keys", "This plugin does not require API keys.")
            return

        # Get existing keys
        existing_keys = self.api_keys.get(plugin_name, {})

        # Create a dialog to edit keys
        dialog = QWidget()
        dialog_layout = QVBoxLayout()

        input_fields = {}
        for key_name in plugin.required_api_keys:
            h_layout = QHBoxLayout()
            label = QLabel(f"{key_name}:")
            line_edit = QLineEdit()
            line_edit.setEchoMode(QLineEdit.EchoMode.Password)
            if key_name in existing_keys:
                line_edit.setText(existing_keys[key_name])
            h_layout.addWidget(label)
            h_layout.addWidget(line_edit)
            dialog_layout.addLayout(h_layout)
            input_fields[key_name] = line_edit

        # Buttons
        buttons_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        cancel_btn = QPushButton("Cancel")
        buttons_layout.addWidget(save_btn)
        buttons_layout.addWidget(cancel_btn)
        dialog_layout.addLayout(buttons_layout)

        dialog.setLayout(dialog_layout)

        # Create a QMessageBox as a modal dialog
        msg_box = QMessageBox()
        msg_box.setWindowTitle("Edit API Keys")
        msg_box.setTextFormat(Qt.TextFormat.RichText)
        msg_box.setText(
            "Enter API keys for the selected plugin:"
        )
        msg_box.layout().addWidget(dialog, 1, 0, 1, msg_box.layout().columnCount())

        # Connect buttons
        def on_save():
            new_keys = {}
            for key_name, line_edit in input_fields.items():
                key_value = line_edit.text().strip()
                if not key_value:
                    QMessageBox.warning(msg_box, "Input Error", f"{key_name} cannot be empty.")
                    return
                new_keys[key_name] = key_value
            self.api_keys[plugin_name] = new_keys
            self.save_config()
            msg_box.accept()
            if self.logger:
                self.logger.info(f"API keys for plugin '{plugin_name}' updated.")

        def on_cancel():
            msg_box.reject()

        save_btn.clicked.connect(on_save)
        cancel_btn.clicked.connect(on_cancel)

        msg_box.exec()

    def filter_tools(self):
        search_text = self.search_input.text().lower()
        for row in range(self.tools_table.rowCount()):
            match = False
            for column in [0,1]:
                item = self.tools_table.item(row, column)
                if item and search_text in item.text().lower():
                    match = True
                    break
            self.tools_table.setRowHidden(row, not match)

    def clear_data(self):
        try:
            cache_dir = "data/cache/"
            if os.path.exists(cache_dir):
                shutil.rmtree(cache_dir)
                os.makedirs(cache_dir)
            self.terminal1.append_text("Cached data cleared.\n", color="green")
            if self.logger:
                self.logger.info("Cached data cleared.")
        except Exception as e:
            self.terminal1.append_text(f"Failed to clear data: {str(e)}\n", color="red")
            if self.logger:
                self.logger.error(f"Failed to clear data: {str(e)}")

    def clear_logs(self):
        try:
            log_dir = "logs/"
            if os.path.exists(log_dir):
                shutil.rmtree(log_dir)
                os.makedirs(log_dir)
            self.terminal1.append_text("Logs cleared.\n", color="green")
            if self.logger:
                self.logger.info("Logs cleared.")
        except Exception as e:
            self.terminal1.append_text(f"Failed to clear logs: {str(e)}\n", color="red")
            if self.logger:
                self.logger.error(f"Failed to clear logs: {str(e)}")

    def clear_terminals(self):
        self.terminal1.clear()
        self.terminal2.clear()
        self.logger.info("Terminals cleared.")
        self.terminal1.append_text("Terminals cleared.\n", color="green")

    def toggle_dark_mode(self):
        if hasattr(self, 'dark_mode') and self.dark_mode:
            self.setStyleSheet("")  # Reset to default (light)
            self.dark_mode = False
            if self.logger:
                self.logger.info("Switched to light mode.")
        else:
            try:
                with open("resources/styles/dark.qss", "r") as f:
                    dark_style = f.read()
                self.setStyleSheet(dark_style)
                self.dark_mode = True
                if self.logger:
                    self.logger.info("Switched to dark mode.")
            except FileNotFoundError:
                self.terminal1.append_text("Dark theme stylesheet not found.\n", color="red")
                if self.logger:
                    self.logger.error("Dark theme stylesheet not found.")

    def update_typing_speed(self, value):
        self.typing_speed_label.setText(f"Terminal Typing Speed: {value}")
        self.terminal1.typing_speed = value
        self.terminal2.typing_speed = value
        self.terminal1.char_interval = max(1, 1000 // value)
        self.terminal2.char_interval = max(1, 1000 // value)
        if self.logger:
            self.logger.info(f"Updated typing speed to {value}.")
        # Restart the timer with new interval
        if self.terminal1.timer.isActive():
            self.terminal1.timer.setInterval(self.terminal1.char_interval)
        if self.terminal2.timer.isActive():
            self.terminal2.timer.setInterval(self.terminal2.char_interval)

    def toggle_typing_effect(self):
        """Toggle the typing effect in the terminal."""
        if self.typing_toggle_btn.isChecked():
            self.typing_toggle_btn.setText("Disable Typing Effect")
            self.terminal2.toggle_typing(True)
            if self.logger:
                self.logger.info("Typing effect enabled.")
        else:
            self.typing_toggle_btn.setText("Enable Typing Effect")
            self.terminal2.toggle_typing(False)
            if self.logger:
                self.logger.info("Typing effect disabled.")

    def validate_color_contrast(self, bg_color, text_color):
        """Simple contrast validation based on luminance."""
        def hex_to_rgb(hex_color):
            hex_color = hex_color.lstrip('#')
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

        def luminance(rgb):
            return 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]

        bg_rgb = hex_to_rgb(bg_color)
        text_rgb = hex_to_rgb(text_color)

        bg_lum = luminance(bg_rgb)
        text_lum = luminance(text_rgb)

        contrast_ratio = abs(bg_lum - text_lum)

        # Simple threshold; for better results, use WCAG contrast ratio
        return contrast_ratio > 50



    def export_data(self):
        try:
            # Ask user to select export format
            formats = "JSON Files (*.json);;HTML Files (*.html);;PDF Files (*.pdf)"
            file_path, selected_filter = QFileDialog.getSaveFileName(
                self,
                "Export Data",
                "",
                formats,
                options=QFileDialog.Option.DontUseNativeDialog
            )
            if file_path:
                # Initialize color selections
                background_color = None
                text_color = "white"  # Default text color

                if file_path.endswith(".html") or file_path.endswith(".pdf"):
                    # Open the custom color selection dialog
                    color_dialog = ColorSelectionDialog(self)
                    if color_dialog.exec() == QDialog.DialogCode.Accepted:
                        background_color = color_dialog.selected_background_color or "#000000"  # Default to black
                        text_color = color_dialog.selected_text_color or "#FFFFFF"  # Default to white

                        # Optional: Validate color contrast
                        if not self.validate_color_contrast(background_color, text_color):
                            QMessageBox.warning(
                                self,
                                "Color Contrast Warning",
                                "The selected text and background colors may result in poor readability. Please choose contrasting colors."
                            )

                    else:
                        # User cancelled color selection
                        self.terminal1.append_text("Export cancelled: Color selection was aborted.\n", color="red")
                        return

                if file_path.endswith(".json"):
                    self.export_to_json(file_path)
                elif file_path.endswith(".html"):
                    self.export_to_html(path=file_path, background_color=background_color, text_color=text_color)
                elif file_path.endswith(".pdf"):
                    self.export_to_pdf(path=file_path, background_color=background_color, text_color=text_color)
                else:
                    self.terminal1.append_text("Unsupported file format.\n", color="red")
                    if self.logger:
                        self.logger.warning(f"Attempted to export unsupported file format: {file_path}")
        except Exception as e:
            self.terminal1.append_text(f"Export failed: {str(e)}\n", color="red")
            if self.logger:
                self.logger.error(f"Export failed: {str(e)}")


    def export_to_json(self, path):
        data = self.terminal2.get_all_data()
        try:
            with open(path, 'w') as f:
                json.dump(data, f, indent=4, default=serialize_json)
            self.terminal1.append_text(f"Data exported to {path}\n", color="green")
            if self.logger:
                self.logger.info(f"Data exported to {path}")
        except Exception as e:
            self.terminal1.append_text(f"Failed to export JSON: {str(e)}\n", color="red")
            if self.logger:
                self.logger.error(f"Failed to export JSON to {path}: {str(e)}")

    def export_to_html(self, path, background_color, text_color):
        try:
            # Get HTML content from terminal2
            html_content = self.terminal2.text_edit.toHtml()
            # Inject background and text colors into HTML
            html_with_colors = f"""
            <html>
                <head>
                    <style>
                        body {{ background-color: {background_color}; color: {text_color}; }}
                        table {{ width: 100%; border-collapse: collapse; }}
                        th, td {{ border: 1px solid #ddd; padding: 8px; }}
                        th {{ background-color: #4CAF50; color: {text_color}; }}
                    </style>
                </head>
                <body>
                    {html_content}
                </body>
            </html>
            """
            with open(path, 'w', encoding='utf-8') as f:
                f.write(html_with_colors)
            self.terminal1.append_text(f"Data exported to {path}\n", color="green")
            if self.logger:
                self.logger.info(f"Data exported to {path}")
        except Exception as e:
            self.terminal1.append_text(f"Failed to export HTML: {str(e)}\n", color="red")
            if self.logger:
                self.logger.error(f"Failed to export HTML to {path}: {str(e)}")

    def export_to_pdf(self, path, background_color, text_color):
        try:
            # Get HTML content from terminal2
            html_content = self.terminal2.text_edit.toHtml()
            # Inject background and text colors into HTML
            html_with_colors = f"""
            <html>
                <head>
                    <style>
                        body {{ background-color: {background_color}; color: {text_color}; }}
                        table {{ width: 100%; border-collapse: collapse; }}
                        th, td {{ border: 1px solid #ddd; padding: 8px; }}
                        th {{ background-color: #4CAF50; color: {text_color}; }}
                    </style>
                </head>
                <body>
                    {html_content}
                </body>
            </html>
            """
            # Temporarily set the terminal's HTML to include background and text colors
            original_html = self.terminal2.text_edit.toHtml()
            self.terminal2.text_edit.setHtml(html_with_colors)

            # Print to PDF using the correct method in PyQt6
            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
            printer.setOutputFileName(path)
            self.terminal2.text_edit.document().print(printer)

            # Restore original HTML
            self.terminal2.text_edit.setHtml(original_html)

            self.terminal1.append_text(f"Data exported to {path}\n", color="green")
            if self.logger:
                self.logger.info(f"Data exported to {path}")
        except Exception as e:
            self.terminal1.append_text(f"Failed to export PDF: {str(e)}\n", color="red")
            if self.logger:
                self.logger.error(f"Failed to export PDF to {path}: {str(e)}")


    def refresh_tools(self):
        try:
            cache_dir = "data/cache/"
            if os.path.exists(cache_dir):
                shutil.rmtree(cache_dir)
                os.makedirs(cache_dir)
                if self.logger:
                    self.logger.info("Cleared cache directory.")
            self.tools_table.setRowCount(0)
            self.load_plugins_into_table()
            self.terminal1.append_text("Tools refreshed.\n", color="green")
            if self.logger:
                self.logger.info("Tools refreshed.")
        except Exception as e:
            self.terminal1.append_text(f"Failed to refresh tools: {str(e)}\n", color="red")
            if self.logger:
                self.logger.error(f"Failed to refresh tools: {str(e)}")

    def run_analysis(self):
        target = self.target_input.text().strip()
        if not target:
            self.terminal1.append_text("Please enter a target.\n", color="red")
            if self.logger:
                self.logger.warning("Run analysis attempted without a target.")
            return

        enabled_plugins = [
            plugin for plugin, row in zip(self.plugins, range(self.tools_table.rowCount()))
            if self.tools_table.cellWidget(row, 2).isChecked()
        ]

        if not enabled_plugins:
            self.terminal1.append_text("No tools enabled.\n", color="red")
            if self.logger:
                self.logger.warning("Run analysis attempted without any enabled tools.")
            return

        self.terminal1.append_text(f"Starting analysis on {target}...\n", color="green")
        if self.logger:
            self.logger.info(f"Starting analysis on {target}.")

        # Disable run button to prevent multiple runs
        self.run_btn.setEnabled(False)
        if self.logger:
            self.logger.info("Run button disabled to prevent multiple analysis runs.")

        # Start analysis thread
        self.analysis_thread = AnalysisThread(enabled_plugins, target, logger=self.logger)
        self.analysis_thread.progress.connect(self.append_text_with_color)
        self.analysis_thread.result.connect(self.handle_plugin_result)
        self.analysis_thread.finished.connect(self.analysis_finished)
        self.analysis_thread.start()

    @pyqtSlot(str, str)
    def append_text_with_color(self, message, color):
        self.terminal1.append_text(message, color)

    @pyqtSlot(str, dict)
    def handle_plugin_result(self, plugin_name, result):
        self.terminal2.append_json(plugin_name, result)
        # Scan the result for image URLs
        image_urls = self.extract_image_urls(result)
        for url in image_urls:
            self.add_image_to_gallery(url)

    def extract_image_urls(self, data):
        """Recursively extract image URLs from a nested dict."""
        image_urls = []
        if isinstance(data, dict):
            for value in data.values():
                image_urls.extend(self.extract_image_urls(value))
        elif isinstance(data, list):
            for item in data:
                image_urls.extend(self.extract_image_urls(item))
        elif isinstance(data, str):
            # Regex to find image URLs
            matches = re.findall(r'(https?://\S+\.(?:png|jpg|jpeg|gif|bmp))', data, re.IGNORECASE)
            image_urls.extend(matches)
        return image_urls

    @pyqtSlot()
    def analysis_finished(self):
        self.run_btn.setEnabled(True)
        self.terminal1.append_text("Analysis completed.\n", color="green")
        if self.logger:
            self.logger.info("Analysis completed.")
        # Save the session to cache
        self.save_session_to_cache()

    def save_session_to_cache(self):
        """Save the current analysis session to the cache."""
        session_id = generate_session_id()
        session_data = self.terminal2.get_all_data()
        session_data["Target"] = self.target_input.text().strip()
        session_data["Timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        session_path = os.path.join(self.CACHE_DIR, f"session_{session_id}.json")
        try:
            with open(session_path, 'w') as f:
                json.dump(session_data, f, default=serialize_json, indent=4)
            self.terminal1.append_text(f"Session saved to cache with ID: {session_id}\n", color="green")
            if self.logger:
                self.logger.info(f"Session saved to cache with ID: {session_id}")
            # Reload cached sessions table
            self.load_cached_sessions()
        except Exception as e:
            self.terminal1.append_text(f"Failed to save session to cache: {str(e)}\n", color="red")
            if self.logger:
                self.logger.error(f"Failed to save session to cache: {str(e)}")

    def load_cached_sessions(self):
        """Load all cached sessions into the table."""
        self.cached_table.setRowCount(0)  # Clear existing rows
        sessions = sorted(os.listdir(self.CACHE_DIR), reverse=True)
        for session_file in sessions:
            if session_file.endswith(".json"):
                session_path = os.path.join(self.CACHE_DIR, session_file)
                try:
                    with open(session_path, 'r') as f:
                        session_data = json.load(f)
                except json.JSONDecodeError as e:
                    if hasattr(self, 'terminal1'):
                        self.terminal1.append_text(f"Failed to read session {session_file}: {str(e)}\n", color="red")
                    if self.logger:
                        self.logger.error(f"Failed to read session {session_file}: {str(e)}")
                    # Optionally delete the malformed file:
                    os.remove(session_path)
                    continue
                except Exception as e:
                    if hasattr(self, 'terminal1'):
                        self.terminal1.append_text(f"Failed to read session {session_file}: {str(e)}\n", color="red")
                    else:
                        print(f"Failed to read session {session_file}: {str(e)}")
                    if self.logger:
                        self.logger.error(f"Failed to read session {session_file}: {str(e)}")
                    continue

                session_id = session_file.replace(".json", "")
                target = session_data.get("Target", "N/A")
                timestamp = session_data.get("Timestamp", "N/A")

                row_position = self.cached_table.rowCount()
                self.cached_table.insertRow(row_position)

                # Session ID
                session_id_item = QTableWidgetItem(session_id)
                self.cached_table.setItem(row_position, 0, session_id_item)

                # Target
                target_item = QTableWidgetItem(target)
                self.cached_table.setItem(row_position, 1, target_item)

                # Timestamp
                timestamp_item = QTableWidgetItem(timestamp)
                self.cached_table.setItem(row_position, 2, timestamp_item)

                # Actions (Export, Delete, Preview)
                actions_widget = QWidget()
                actions_layout = QHBoxLayout()
                actions_layout.setContentsMargins(0, 0, 0, 0)

                export_btn = QPushButton("Export")
                export_btn.setFixedWidth(60)
                export_btn.clicked.connect(lambda _, s=session_id: self.export_cached_session(s))

                delete_btn = QPushButton("Delete")
                delete_btn.setFixedWidth(60)
                delete_btn.clicked.connect(lambda _, s=session_id: self.delete_cached_session(s))

                preview_btn = QPushButton("Preview")
                preview_btn.setFixedWidth(60)
                preview_btn.clicked.connect(lambda _, s=session_id: self.preview_cached_session(s))

                actions_layout.addWidget(export_btn)
                actions_layout.addWidget(delete_btn)
                actions_layout.addWidget(preview_btn)
                actions_widget.setLayout(actions_layout)

                self.cached_table.setCellWidget(row_position, 3, actions_widget)
        if self.logger:
            self.logger.info("Cached sessions loaded into the table.")

    def export_cached_session(self, session_id):
        """Export a cached session."""
        session_file = os.path.join(self.CACHE_DIR, f"{session_id}.json")
        if not os.path.exists(session_file):
            self.terminal1.append_text(f"Session {session_id} does not exist.\n", color="red")
            if self.logger:
                self.logger.warning(f"Export attempted for non-existent session: {session_id}")
            return

        try:
            with open(session_file, 'r') as f:
                session_data = json.load(f)
        except Exception as e:
            self.terminal1.append_text(f"Failed to read session {session_id}: {str(e)}\n", color="red")
            if self.logger:
                self.logger.error(f"Failed to read session {session_id}: {str(e)}")
            return

        # Ask user to select export format
        try:
            formats = "JSON Files (*.json);;HTML Files (*.html);;PDF Files (*.pdf)"
            file_path, selected_filter = QFileDialog.getSaveFileName(
                self,
                f"Export Session {session_id}",
                "",
                formats,
                options=QFileDialog.Option.DontUseNativeDialog
            )
            if file_path:
                # Ask user to select background color if exporting to HTML or PDF
                background_color = None
                if file_path.endswith(".html") or file_path.endswith(".pdf"):
                    color = QColorDialog.getColor()
                    if color.isValid():
                        background_color = color.name()  # Hex color code
                    else:
                        # User cancelled color selection
                        self.terminal1.append_text("Export cancelled: No background color selected.\n", color="red")
                        return
                if file_path.endswith(".json"):
                    with open(file_path, 'w') as f:
                        json.dump(session_data, f, indent=4, default=serialize_json)
                    self.terminal1.append_text(f"Session {session_id} exported to {file_path}\n", color="green")
                    if self.logger:
                        self.logger.info(f"Session {session_id} exported to {file_path}")
                elif file_path.endswith(".html"):
                    # Generate HTML content
                    html_content = ""
                    for plugin, data in session_data.items():
                        if plugin in ["Target", "Timestamp"]:
                            continue
                        html_content += f"<h3 style='color:#4CAF50;'>{plugin} Results</h3><table border='1' cellspacing='0' cellpadding='5' style='color: white;'>"
                        html_content += "<tr style='background-color:#333;'><th>Key</th><th>Value</th></tr>"
                        for key, value in data.items():
                            try:
                                serialized_value = serialize_json(value)
                            except TypeError as e:
                                serialized_value = f"Unserializable data: {str(e)}"
                            html_content += f"<tr><td>{key}</td><td>{serialized_value}</td></tr>"
                        html_content += "</table><br>"
                    # Inject background color
                    html_with_bg = f"""
                    <html>
                        <head>
                            <style>
                                body {{ background-color: {background_color}; color: white; }}
                                table {{ width: 100%; border-collapse: collapse; }}
                                th, td {{ border: 1px solid #ddd; padding: 8px; }}
                                th {{ background-color: #4CAF50; color: white; }}
                            </style>
                        </head>
                        <body>
                            {html_content}
                        </body>
                    </html>
                    """
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(html_with_bg)
                    self.terminal1.append_text(f"Session {session_id} exported to {file_path}\n", color="green")
                    if self.logger:
                        self.logger.info(f"Session {session_id} exported to {file_path}")
                elif file_path.endswith(".pdf"):
                    # Generate HTML content
                    html_content = ""
                    for plugin, data in session_data.items():
                        if plugin in ["Target", "Timestamp"]:
                            continue
                        html_content += f"<h3 style='color:#4CAF50;'>{plugin} Results</h3><table border='1' cellspacing='0' cellpadding='5' style='color: white;'>"
                        html_content += "<tr style='background-color:#333;'><th>Key</th><th>Value</th></tr>"
                        for key, value in data.items():
                            try:
                                serialized_value = serialize_json(value)
                            except TypeError as e:
                                serialized_value = f"Unserializable data: {str(e)}"
                            html_content += f"<tr><td>{key}</td><td>{serialized_value}</td></tr>"
                        html_content += "</table><br>"
                    # Inject background color
                    html_with_bg = f"""
                    <html>
                        <head>
                            <style>
                                body {{ background-color: {background_color}; color: white; }}
                                table {{ width: 100%; border-collapse: collapse; }}
                                th, td {{ border: 1px solid #ddd; padding: 8px; }}
                                th {{ background-color: #4CAF50; color: white; }}
                            </style>
                        </head>
                        <body>
                            {html_content}
                        </body>
                    </html>
                    """
                    # Temporarily set the terminal's HTML to include background color
                    original_html = self.terminal2.text_edit.toHtml()
                    self.terminal2.text_edit.setHtml(html_with_bg)

                    # Print to PDF using the correct method in PyQt6
                    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
                    printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
                    printer.setOutputFileName(file_path)
                    self.terminal2.text_edit.document().print(printer)  # Changed from print_ to print

                    # Restore original HTML
                    self.terminal2.text_edit.setHtml(original_html)

                    self.terminal1.append_text(f"Session {session_id} exported to {file_path}\n", color="green")
                    if self.logger:
                        self.logger.info(f"Session {session_id} exported to {file_path}")
        except Exception as e:
            self.terminal1.append_text(f"Failed to export session {session_id}: {str(e)}\n", color="red")
            if self.logger:
                self.logger.error(f"Failed to export session {session_id}: {str(e)}")

    def delete_cached_session(self, session_id):
        """Delete a cached session."""
        session_file = os.path.join(self.CACHE_DIR, f"{session_id}.json")
        if not os.path.exists(session_file):
            self.terminal1.append_text(f"Session {session_id} does not exist.\n", color="red")
            if self.logger:
                self.logger.warning(f"Delete attempted for non-existent session: {session_id}")
            return

        try:
            os.remove(session_file)
            self.terminal1.append_text(f"Session {session_id} deleted from cache.\n", color="green")
            if self.logger:
                self.logger.info(f"Session {session_id} deleted from cache.")
            self.load_cached_sessions()
        except Exception as e:
            self.terminal1.append_text(f"Failed to delete session {session_id}: {str(e)}\n", color="red")
            if self.logger:
                self.logger.error(f"Failed to delete session {session_id}: {str(e)}")

    def preview_cached_session(self, session_id):
        """Preview a cached session by rendering it in the terminal."""
        session_file = os.path.join(self.CACHE_DIR, f"{session_id}.json")
        if not os.path.exists(session_file):
            self.terminal1.append_text(f"Session {session_id} does not exist.\n", color="red")
            if self.logger:
                self.logger.warning(f"Preview attempted for non-existent session: {session_id}")
            return

        try:
            with open(session_file, 'r') as f:
                session_data = json.load(f)
        except Exception as e:
            self.terminal1.append_text(f"Failed to read session {session_id}: {str(e)}\n", color="red")
            if self.logger:
                self.logger.error(f"Failed to read session {session_id}: {str(e)}")
            return

        # Clear current terminal content
        self.terminal2.clear()
        self.terminal1.append_text(f"Previewing session {session_id}...\n", color="green")
        if self.logger:
            self.logger.info(f"Previewing session {session_id}.")

        # Render the cached data into the terminal
        for plugin, data in session_data.items():
            if plugin in ["Target", "Timestamp"]:
                continue
            self.terminal2.append_json(plugin, data)

    def save_session_to_cache(self):
        """Save the current analysis session to the cache."""
        session_id = generate_session_id()
        session_data = self.terminal2.get_all_data()
        session_data["Target"] = self.target_input.text().strip()
        session_data["Timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if self.logger:
            self.logger.debug(f"Session Data: {session_data}")
        session_path = os.path.join(self.CACHE_DIR, f"session_{session_id}.json")
        try:
            with open(session_path, 'w') as f:
                json.dump(session_data, f, default=serialize_json, indent=4)
            self.terminal1.append_text(f"Session saved to cache with ID: {session_id}\n", color="green")
            if self.logger:
                self.logger.info(f"Session saved to cache with ID: {session_id}")
            # Reload cached sessions table
            self.load_cached_sessions()
        except Exception as e:
            self.terminal1.append_text(f"Failed to save session to cache: {str(e)}\n", color="red")
            if self.logger:
                self.logger.error(f"Failed to save session to cache: {str(e)}")

    def show_dev_contact(self):
        msg = QMessageBox()
        msg.setWindowTitle("Developer Contact")
        msg.setTextFormat(Qt.TextFormat.RichText)
        msg.setText(
            "Developed by <b>Thehackitect</b>.<br><br>"
            "Social Links:<br>"
            "- <a href='https://twitter.com/Thehackitect'>Twitter</a><br>"
            "- <a href='https://github.com/Thehackitect'>GitHub</a>"
        )
        msg.exec()

    def terminate_analysis(self):
        if self.analysis_thread and self.analysis_thread.isRunning():
            self.analysis_thread.terminate_analysis()
            self.terminal1.append_text("Terminating analysis...\n", color="red")
            if self.logger:
                self.logger.info("User requested analysis termination.")
        else:
            self.terminal1.append_text("No analysis is currently running.\n", color="yellow")
            if self.logger:
                self.logger.warning("Terminate button pressed but no analysis is running.")

    def add_image_to_gallery(self, image_url):
        """Download and add an image to the gallery."""
        try:
            response = requests.get(image_url, stream=True, timeout=10)
            if response.status_code == 200 and 'image' in response.headers.get('Content-Type', ''):
                image_data = response.content
                pixmap = QPixmap()
                pixmap.loadFromData(image_data)
                if pixmap.isNull():
                    raise ValueError("Failed to load image data.")
                
                # Create QLabel to display the image
                image_label = QLabel()
                image_label.setPixmap(pixmap.scaled(QSize(150, 150), Qt.AspectRatioMode.KeepAspectRatio))
                image_label.setFixedSize(150, 150)
                image_label.setToolTip(image_url)
                
                # Create View and Download buttons
                view_btn = QPushButton("View")
                view_btn.setFixedWidth(60)
                view_btn.clicked.connect(lambda _, url=image_url: self.view_image(url))
                
                download_btn = QPushButton("Download")
                download_btn.setFixedWidth(60)
                download_btn.clicked.connect(lambda _, url=image_url: self.download_image(url))
                
                # Layout for buttons
                btn_layout = QHBoxLayout()
                btn_layout.addWidget(view_btn)
                btn_layout.addWidget(download_btn)
                
                # Create a container widget for image and buttons
                container = QWidget()
                container_layout = QVBoxLayout()
                container_layout.addWidget(image_label)
                container_layout.addLayout(btn_layout)
                container.setLayout(container_layout)
                
                # Add to gallery layout
                row = self.image_count // self.max_images_per_row
                col = self.image_count % self.max_images_per_row
                self.gallery_layout.addWidget(container, row, col)
                self.image_widgets.append(container)
                self.image_count += 1

                self.terminal1.append_text(f"Detected image: {image_url}\n", color="blue")
                if self.logger:
                    self.logger.info(f"Detected and added image: {image_url}")
            else:
                self.terminal1.append_text(f"Invalid image URL or content type: {image_url}\n", color="orange")
                if self.logger:
                    self.logger.warning(f"Invalid image URL or content type: {image_url}")
        except Exception as e:
            self.terminal1.append_text(f"Failed to add image {image_url}: {str(e)}\n", color="red")
            if self.logger:
                self.logger.error(f"Failed to add image {image_url}: {str(e)}")

    def view_image(self, url):
        """Open the image in the default image viewer."""
        try:
            image_path = self.download_image(url, save=False)
            if image_path:
                if os.name == 'nt':  # Windows
                    os.startfile(image_path)
                elif os.name == 'posix':  # macOS or Linux
                    import subprocess
                    subprocess.call(['open' if sys.platform == 'darwin' else 'xdg-open', image_path])
        except Exception as e:
            self.terminal1.append_text(f"Failed to view image {url}: {str(e)}\n", color="red")
            if self.logger:
                self.logger.error(f"Failed to view image {url}: {str(e)}")

    def download_image(self, url, save=True):
        """Download the image to a temporary location or prompt user to save."""
        try:
            response = requests.get(url, stream=True, timeout=10)
            if response.status_code == 200 and 'image' in response.headers.get('Content-Type', ''):
                image_data = response.content
                if save:
                    save_path, _ = QFileDialog.getSaveFileName(
                        self,
                        "Download Image",
                        "",
                        "Images (*.png *.jpg *.jpeg *.bmp *.gif)",
                        options=QFileDialog.Option.DontUseNativeDialog
                    )
                    if save_path:
                        with open(save_path, 'wb') as f:
                            f.write(image_data)
                        self.terminal1.append_text(f"Image downloaded to {save_path}\n", color="green")
                        if self.logger:
                            self.logger.info(f"Image downloaded to {save_path}")
                        return save_path
                    else:
                        return None
                else:
                    # Save to a temporary file
                    import tempfile
                    tmp_dir = tempfile.gettempdir()
                    filename = os.path.join(tmp_dir, os.path.basename(url))
                    with open(filename, 'wb') as f:
                        f.write(image_data)
                    return filename
            else:
                self.terminal1.append_text(f"Invalid image URL or content type: {url}\n", color="orange")
                if self.logger:
                    self.logger.warning(f"Invalid image URL or content type: {url}")
                return None
        except Exception as e:
            self.terminal1.append_text(f"Failed to download image {url}: {str(e)}\n", color="red")
            if self.logger:
                self.logger.error(f"Failed to download image {url}: {str(e)}")
            return None

    def clear_gallery(self):
        """Clear all images from the gallery."""
        for widget in self.image_widgets:
            self.gallery_layout.removeWidget(widget)
            widget.deleteLater()
        self.image_widgets.clear()
        self.image_count = 0
        self.logger.info("Image gallery cleared.")
        self.terminal1.append_text("Image gallery cleared.\n", color="green")
