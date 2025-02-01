# main.py
import sys
from PyQt6.QtWidgets import QApplication
from ui.main_window import MainWindow
from utils.logger import setup_logger

def main():
    logger = setup_logger()
    app = QApplication(sys.argv)
    window = MainWindow(logger=logger)  # Pass the logger to MainWindow
    window.show()
    logger.info("Application started.")
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
