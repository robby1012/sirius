#!/usr/bin/env python3
"""
Sirius - API Performance Tester (GUI Version)
A PyQt6-based graphical user interface for testing API performance.

Author: Robby Sitanala

Version: 0.0.1
"""

import sys
from PyQt6.QtWidgets import QApplication
from main_window import PerformanceTesterGUI


def main():
    """Main entry point for the GUI application"""
    app = QApplication(sys.argv)
    window = PerformanceTesterGUI()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()