"""Main window for Sirius - API Performance Tester GUI"""

import json
import os
import sys
from datetime import datetime
from typing import Dict, Any, Optional

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit, QSpinBox, QComboBox,
    QGroupBox, QTabWidget, QTableWidget, QTableWidgetItem, QFileDialog,
    QProgressBar, QMessageBox, QHeaderView, QStackedWidget, QApplication
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

# Import the performance testing logic from parent directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sirius import (
    summarize, compute_time_series,
    write_request_log_csv, write_summary_csv, write_timeseries_csv,
    generate_html_report
)

from worker import TestWorker
from widgets import MatplotlibWidget
from auth_dialog import AuthDialog

try:
    import matplotlib
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False


class PerformanceTesterGUI(QMainWindow):
    """Main window for Sirius - API Performance Tester"""

    def __init__(self):
        super().__init__()
        self.results = None
        self.summary = None
        self.timeseries = None
        self.worker = None
        self.auth_config = {'type': 'None'}  # Store authentication configuration
        
        self.init_ui()
        
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Sirius - API Performance Tester")
        self.setMinimumSize(900, 700)
        
        # Get screen geometry and set window to use max height
        screen = QApplication.primaryScreen().availableGeometry()
        # Use 90% of screen width (or max 1400px) and 95% of screen height
        width = min(int(screen.width() * 0.5), 1400)
        height = int(screen.height())
        self.resize(width, height)
        
        # Center the window on screen
        self.move(
            (screen.width() - width) // 2,
            (screen.height() - height) // 2
        )
        
        # Central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Input section
        input_group = self.create_input_section()
        main_layout.addWidget(input_group)
        
        # Control buttons
        button_layout = self.create_button_section()
        main_layout.addLayout(button_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)
        
        # Results section (tabbed)
        self.results_tabs = QTabWidget()
        self.create_results_tabs()
        main_layout.addWidget(self.results_tabs)
        
    def create_input_section(self) -> QGroupBox:
        """Create the input fields section"""
        group = QGroupBox("Test Configuration")
        layout = QVBoxLayout()
        
        # URL and Method in a single row
        url_method_layout = QHBoxLayout()
        url_method_layout.addWidget(QLabel("URL:"))
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://api.example.com/endpoint")
        url_method_layout.addWidget(self.url_input, stretch=3)
        
        self.method_combo = QComboBox()
        self.method_combo.addItems(["GET", "POST", "PUT", "DELETE", "PATCH"])
        self.method_combo.setCurrentText("GET")
        self.method_combo.setMaximumWidth(100)
        url_method_layout.addWidget(self.method_combo)
        layout.addLayout(url_method_layout)
        
        # Tabs for Headers and Body
        self.request_tabs = QTabWidget()
        
        # Headers Tab
        headers_tab = self.create_headers_tab()
        self.request_tabs.addTab(headers_tab, "Headers")
        
        # Body Tab
        body_tab = self.create_body_tab()
        self.request_tabs.addTab(body_tab, "Body")
        
        # Add with stretch to maximize height
        layout.addWidget(self.request_tabs, stretch=1)
        
        # Number of requests and concurrency
        params_layout = QHBoxLayout()
        
        params_layout.addWidget(QLabel("Requests:"))
        self.num_requests = QSpinBox()
        self.num_requests.setMinimum(1)
        self.num_requests.setMaximum(100000)
        self.num_requests.setValue(100)
        params_layout.addWidget(self.num_requests)
        
        params_layout.addWidget(QLabel("Concurrency:"))
        self.concurrency = QSpinBox()
        self.concurrency.setMinimum(1)
        self.concurrency.setMaximum(1000)
        self.concurrency.setValue(10)
        params_layout.addWidget(self.concurrency)
        
        params_layout.addWidget(QLabel("Timeout (s):"))
        self.timeout = QSpinBox()
        self.timeout.setMinimum(1)
        self.timeout.setMaximum(300)
        self.timeout.setValue(30)
        params_layout.addWidget(self.timeout)
        
        params_layout.addStretch()
        layout.addLayout(params_layout)
        
        group.setLayout(layout)
        return group
    
    def create_headers_tab(self) -> QWidget:
        """Create the Headers tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(5, 5, 5, 5)
        
        self.headers_table = QTableWidget()
        self.headers_table.setColumnCount(3)
        self.headers_table.setHorizontalHeaderLabels(["Key", "Value", ""])
        self.headers_table.horizontalHeader().setStretchLastSection(False)
        self.headers_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.headers_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.headers_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.headers_table.setColumnWidth(2, 30)
        # Add default header rows with predefined keys
        self.add_header_row("Accept")
        self.add_header_row("Content-Type")
        self.add_header_row("User-Agent")
        # Add with stretch to maximize height
        layout.addWidget(self.headers_table, stretch=1)
        
        # Add header button and Auth button
        header_buttons_layout = QHBoxLayout()
        add_header_btn = QPushButton("+ Add Header")
        add_header_btn.clicked.connect(self.add_header_row)
        header_buttons_layout.addWidget(add_header_btn)
        
        self.auth_btn = QPushButton("🔒 Authentication")
        self.auth_btn.clicked.connect(self.open_auth_dialog)
        self.auth_btn.setStyleSheet("QPushButton { background-color: #3498db; color: white; font-weight: bold; }")
        header_buttons_layout.addWidget(self.auth_btn)
        
        header_buttons_layout.addStretch()
        layout.addLayout(header_buttons_layout)
        
        return widget
    
    def create_body_tab(self) -> QWidget:
        """Create the Body tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Body type selector
        body_type_layout = QHBoxLayout()
        body_type_layout.addWidget(QLabel("Body Type:"))
        self.body_type_combo = QComboBox()
        self.body_type_combo.addItems(["None", "JSON / Raw", "Form Data (multipart/form-data)", "Form URL Encoded (application/x-www-form-urlencoded)"])
        self.body_type_combo.currentIndexChanged.connect(self.on_body_type_changed)
        body_type_layout.addWidget(self.body_type_combo)
        body_type_layout.addStretch()
        layout.addLayout(body_type_layout)
        
        # Body input stack (switches between text and form data)
        self.body_stack = QStackedWidget()
        
        # Raw/JSON body widget
        raw_body_widget = QWidget()
        raw_body_layout = QVBoxLayout(raw_body_widget)
        raw_body_layout.setContentsMargins(0, 0, 0, 0)
        self.body_input = QTextEdit()
        self.body_input.setPlaceholderText('{"key": "value"} or raw text')
        raw_body_layout.addWidget(self.body_input)
        self.body_stack.addWidget(raw_body_widget)
        
        # Form data widget
        form_data_widget = QWidget()
        form_data_layout = QVBoxLayout(form_data_widget)
        form_data_layout.setContentsMargins(0, 0, 0, 0)
        
        self.formdata_table = QTableWidget()
        self.formdata_table.setColumnCount(4)
        self.formdata_table.setHorizontalHeaderLabels(["Key", "Value", "Type", ""])
        self.formdata_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.formdata_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.formdata_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.formdata_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.formdata_table.setColumnWidth(0, 150)
        self.formdata_table.setColumnWidth(2, 100)
        self.formdata_table.setColumnWidth(3, 30)
        form_data_layout.addWidget(self.formdata_table)
        
        add_formdata_btn = QPushButton("+ Add Field")
        add_formdata_btn.clicked.connect(self.add_formdata_row)
        form_data_layout.addWidget(add_formdata_btn)
        
        self.body_stack.addWidget(form_data_widget)
        
        # Form URL Encoded widget
        urlencoded_widget = QWidget()
        urlencoded_layout = QVBoxLayout(urlencoded_widget)
        urlencoded_layout.setContentsMargins(0, 0, 0, 0)
        
        self.urlencoded_table = QTableWidget()
        self.urlencoded_table.setColumnCount(3)
        self.urlencoded_table.setHorizontalHeaderLabels(["Key", "Value", ""])
        self.urlencoded_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.urlencoded_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.urlencoded_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.urlencoded_table.setColumnWidth(2, 30)
        urlencoded_layout.addWidget(self.urlencoded_table)
        
        add_urlencoded_btn = QPushButton("+ Add Field")
        add_urlencoded_btn.clicked.connect(self.add_urlencoded_row)
        urlencoded_layout.addWidget(add_urlencoded_btn)
        
        self.body_stack.addWidget(urlencoded_widget)
        
        # Add with stretch to maximize height
        layout.addWidget(self.body_stack, stretch=1)
        self.body_stack.setVisible(False)  # Initially hidden
        
        return widget
    
    def add_header_row(self, key: str = ""):
        """Add a new row to the headers table"""
        row = self.headers_table.rowCount()
        self.headers_table.insertRow(row)
        
        # Key input
        key_item = QTableWidgetItem(key)
        self.headers_table.setItem(row, 0, key_item)
        
        # Value input
        value_item = QTableWidgetItem("")
        self.headers_table.setItem(row, 1, value_item)
        
        # Delete button
        delete_btn = QPushButton("×")
        delete_btn.setMaximumWidth(30)
        delete_btn.clicked.connect(lambda: self.remove_header_row(row))
        self.headers_table.setCellWidget(row, 2, delete_btn)
    
    def remove_header_row(self, row: int):
        """Remove a row from the headers table"""
        self.headers_table.removeRow(row)
        # Ensure at least one empty row
        if self.headers_table.rowCount() == 0:
            self.add_header_row()
    
    def get_headers_from_table(self) -> Dict[str, str]:
        """Extract headers from the table"""
        headers = {}
        for row in range(self.headers_table.rowCount()):
            key_item = self.headers_table.item(row, 0)
            value_item = self.headers_table.item(row, 1)
            if key_item and value_item:
                key = key_item.text().strip()
                value = value_item.text().strip()
                if key and value:
                    headers[key] = value
        return headers
    
    def open_auth_dialog(self):
        """Open the authentication configuration dialog"""
        dialog = AuthDialog(self, self.auth_config)
        if dialog.exec():
            self.auth_config = dialog.get_config()
            # Update button text to show auth is configured
            auth_type = self.auth_config.get('type', 'None')
            if auth_type == 'None':
                self.auth_btn.setText("🔒 Authentication")
                self.auth_btn.setStyleSheet("QPushButton { background-color: #3498db; color: white; font-weight: bold; }")
            else:
                self.auth_btn.setText(f"🔒 Auth: {auth_type}")
                self.auth_btn.setStyleSheet("QPushButton { background-color: #27ae60; color: white; font-weight: bold; }")
    
    def apply_auth_to_headers(self, headers: Dict[str, str], url: str = "") -> Dict[str, str]:
        """Apply authentication configuration to headers"""
        if self.auth_config.get('type', 'None') == 'None':
            return headers
        
        # Create a temporary auth dialog instance to use its apply method
        temp_dialog = AuthDialog(self, self.auth_config)
        return temp_dialog.apply_auth_to_headers(headers, url)
    
    def get_auth_query_params(self) -> Dict[str, str]:
        """Get query parameters from auth (e.g., API Key in query)"""
        if self.auth_config.get('type', 'None') == 'None':
            return {}
        
        temp_dialog = AuthDialog(self, self.auth_config)
        return temp_dialog.get_query_params()
    
    def on_body_type_changed(self, index: int):
        """Handle body type selection change"""
        if index == 0:  # None
            self.body_stack.setVisible(False)
        elif index == 1:  # JSON/Raw
            self.body_stack.setVisible(True)
            self.body_stack.setCurrentIndex(0)
        elif index == 2:  # Form Data
            self.body_stack.setVisible(True)
            self.body_stack.setCurrentIndex(1)
            # Add initial row if empty
            if self.formdata_table.rowCount() == 0:
                self.add_formdata_row()
        elif index == 3:  # Form URL Encoded
            self.body_stack.setVisible(True)
            self.body_stack.setCurrentIndex(2)
            # Add initial row if empty
            if self.urlencoded_table.rowCount() == 0:
                self.add_urlencoded_row()
    
    def add_formdata_row(self):
        """Add a new row to the form data table"""
        row = self.formdata_table.rowCount()
        self.formdata_table.insertRow(row)
        
        # Key input
        key_item = QTableWidgetItem("")
        self.formdata_table.setItem(row, 0, key_item)
        
        # Value input (or file path)
        value_item = QTableWidgetItem("")
        self.formdata_table.setItem(row, 1, value_item)
        
        # Type selector
        type_combo = QComboBox()
        type_combo.addItems(["Text", "File"])
        type_combo.currentTextChanged.connect(lambda text, r=row: self.on_formdata_type_changed(r, text))
        self.formdata_table.setCellWidget(row, 2, type_combo)
        
        # Delete button
        delete_btn = QPushButton("×")
        delete_btn.setMaximumWidth(30)
        delete_btn.clicked.connect(lambda: self.remove_formdata_row(row))
        self.formdata_table.setCellWidget(row, 3, delete_btn)
    
    def remove_formdata_row(self, row: int):
        """Remove a row from the form data table"""
        self.formdata_table.removeRow(row)
    
    def on_formdata_type_changed(self, row: int, type_text: str):
        """Handle form data type change (Text/File)"""
        if type_text == "File":
            # Add a browse button to the value cell
            file_widget = QWidget()
            file_layout = QHBoxLayout(file_widget)
            file_layout.setContentsMargins(0, 0, 0, 0)
            
            file_path_edit = QLineEdit()
            file_path_edit.setPlaceholderText("Select file...")
            file_layout.addWidget(file_path_edit)
            
            browse_btn = QPushButton("...")
            browse_btn.setMaximumWidth(30)
            browse_btn.clicked.connect(lambda: self.browse_file_for_formdata(row, file_path_edit))
            file_layout.addWidget(browse_btn)
            
            self.formdata_table.setCellWidget(row, 1, file_widget)
        else:
            # Restore regular text input
            self.formdata_table.removeCellWidget(row, 1)
            value_item = QTableWidgetItem("")
            self.formdata_table.setItem(row, 1, value_item)
    
    def browse_file_for_formdata(self, row: int, line_edit: QLineEdit):
        """Open file browser for form data file selection"""
        file_path, _ = QFileDialog.getOpenFileName(self, "Select File")
        if file_path:
            line_edit.setText(file_path)
    
    def get_formdata_from_table(self) -> Optional[Dict[str, Any]]:
        """Extract form data from the table"""
        formdata = {}
        for row in range(self.formdata_table.rowCount()):
            key_item = self.formdata_table.item(row, 0)
            if not key_item:
                continue
            key = key_item.text().strip()
            if not key:
                continue
            
            type_combo = self.formdata_table.cellWidget(row, 2)
            if isinstance(type_combo, QComboBox):
                type_text = type_combo.currentText()
                
                if type_text == "File":
                    # Get file path from widget
                    file_widget = self.formdata_table.cellWidget(row, 1)
                    if file_widget:
                        file_path_edit = file_widget.findChild(QLineEdit)
                        if file_path_edit:
                            file_path = file_path_edit.text().strip()
                            if file_path and os.path.exists(file_path):
                                with open(file_path, 'rb') as f:
                                    formdata[key] = {
                                        'file': f.read(),
                                        'filename': os.path.basename(file_path)
                                    }
                else:
                    # Text value
                    value_item = self.formdata_table.item(row, 1)
                    if value_item:
                        value = value_item.text().strip()
                        if value:
                            formdata[key] = value
        
        return formdata if formdata else None
    
    def add_urlencoded_row(self):
        """Add a new row to the URL encoded table"""
        row = self.urlencoded_table.rowCount()
        self.urlencoded_table.insertRow(row)
        
        # Key input
        key_item = QTableWidgetItem("")
        self.urlencoded_table.setItem(row, 0, key_item)
        
        # Value input
        value_item = QTableWidgetItem("")
        self.urlencoded_table.setItem(row, 1, value_item)
        
        # Delete button
        delete_btn = QPushButton("×")
        delete_btn.setMaximumWidth(30)
        delete_btn.clicked.connect(lambda: self.remove_urlencoded_row(row))
        self.urlencoded_table.setCellWidget(row, 2, delete_btn)
    
    def remove_urlencoded_row(self, row: int):
        """Remove a row from the URL encoded table"""
        self.urlencoded_table.removeRow(row)
    
    def get_urlencoded_from_table(self) -> Optional[Dict[str, str]]:
        """Extract URL encoded data from the table"""
        urlencoded = {}
        for row in range(self.urlencoded_table.rowCount()):
            key_item = self.urlencoded_table.item(row, 0)
            value_item = self.urlencoded_table.item(row, 1)
            if key_item and value_item:
                key = key_item.text().strip()
                value = value_item.text().strip()
                if key:
                    urlencoded[key] = value
        return urlencoded if urlencoded else None
    
    def create_button_section(self) -> QHBoxLayout:
        """Create control buttons"""
        layout = QHBoxLayout()
        
        self.run_button = QPushButton("Run Test")
        self.run_button.setMinimumWidth(100)
        self.run_button.clicked.connect(self.run_test)
        self.run_button.setStyleSheet("QPushButton { background-color: #27ae60; color: white; font-weight: bold; padding: 8px; }")
        layout.addWidget(self.run_button)
        
        self.stop_button = QPushButton("Stop")
        self.stop_button.setMinimumWidth(100)
        self.stop_button.clicked.connect(self.stop_test)
        self.stop_button.setEnabled(False)
        self.stop_button.setStyleSheet("QPushButton { background-color: #e74c3c; color: white; font-weight: bold; padding: 8px; }")
        layout.addWidget(self.stop_button)
        
        layout.addStretch()
        
        self.export_json_button = QPushButton("Export JSON")
        self.export_json_button.clicked.connect(lambda: self.export_results('json'))
        self.export_json_button.setEnabled(False)
        layout.addWidget(self.export_json_button)
        
        self.export_csv_button = QPushButton("Export CSV")
        self.export_csv_button.clicked.connect(lambda: self.export_results('csv'))
        self.export_csv_button.setEnabled(False)
        layout.addWidget(self.export_csv_button)
        
        self.export_html_button = QPushButton("Export HTML Report")
        self.export_html_button.clicked.connect(lambda: self.export_results('html'))
        self.export_html_button.setEnabled(False)
        layout.addWidget(self.export_html_button)
        
        return layout
    
    def create_results_tabs(self):
        """Create tabs for displaying results"""
        # Summary tab
        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        self.summary_text.setFont(QFont("Courier", 10))
        self.results_tabs.addTab(self.summary_text, "Summary")
        
        # Summary table tab
        self.summary_table = QTableWidget()
        self.summary_table.setColumnCount(2)
        self.summary_table.setHorizontalHeaderLabels(["Metric", "Value"])
        self.summary_table.horizontalHeader().setStretchLastSection(True)
        self.results_tabs.addTab(self.summary_table, "Summary Table")
        
        # Time series tab
        self.timeseries_table = QTableWidget()
        self.results_tabs.addTab(self.timeseries_table, "Time Series")
        
        # Chart tab (if matplotlib is available)
        if MATPLOTLIB_AVAILABLE:
            self.chart_widget = MatplotlibWidget()
            self.results_tabs.addTab(self.chart_widget, "Chart")
        else:
            no_chart_label = QLabel("Matplotlib not installed. Install with: pip install matplotlib")
            no_chart_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.results_tabs.addTab(no_chart_label, "Chart")
        
        # Console tab for debugging
        self.console_text = QTextEdit()
        self.console_text.setReadOnly(True)
        self.console_text.setFont(QFont("Courier", 9))
        self.console_text.setStyleSheet("QTextEdit { background-color: #1e1e1e; color: #d4d4d4; }")
        self.results_tabs.addTab(self.console_text, "Console")
    
    def run_test(self):
        """Start the performance test"""
        # Validate inputs
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Input Error", "Please enter a URL")
            return
        
        # Get headers from table
        headers = self.get_headers_from_table()
        
        # Apply authentication to headers
        headers = self.apply_auth_to_headers(headers, url)
        
        # Get auth query parameters (e.g., for API Key in query)
        auth_params = self.get_auth_query_params()
        if auth_params:
            # Append query parameters to URL
            separator = '&' if '?' in url else '?'
            query_string = '&'.join([f"{k}={v}" for k, v in auth_params.items()])
            url = f"{url}{separator}{query_string}"
        
        # Determine body type and prepare data
        body_bytes = None
        formdata = None
        urlencoded = None
        body_type_index = self.body_type_combo.currentIndex()
        
        if body_type_index == 1:  # JSON/Raw
            body_text = self.body_input.toPlainText().strip()
            if body_text:
                try:
                    js = json.loads(body_text)
                    body_bytes = json.dumps(js).encode('utf-8')
                    if 'Content-Type' not in headers:
                        headers['Content-Type'] = 'application/json'
                except:
                    body_bytes = body_text.encode('utf-8')
        
        elif body_type_index == 2:  # Form Data
            formdata = self.get_formdata_from_table()
            if not formdata:
                QMessageBox.warning(self, "Input Error", "Please add at least one form data field")
                return
        
        elif body_type_index == 3:  # Form URL Encoded
            urlencoded = self.get_urlencoded_from_table()
            if not urlencoded:
                QMessageBox.warning(self, "Input Error", "Please add at least one URL encoded field")
                return
        
        method = self.method_combo.currentText()
        total = self.num_requests.value()
        concurrency = min(self.concurrency.value(), total)
        timeout = float(self.timeout.value())
        
        # Update UI
        self.run_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.summary_text.setText("Running test...\n")
        
        # Clear console
        self.console_text.clear()
        self.log_to_console("Console ready. Starting test...\n")
        
        # Start worker thread
        self.worker = TestWorker(url, method, body_bytes, headers, total, concurrency, timeout, formdata, urlencoded)
        self.worker.finished.connect(self.on_test_finished)
        self.worker.error.connect(self.on_test_error)
        self.worker.log.connect(self.log_to_console)
        self.worker.start()
    
    def stop_test(self):
        """Stop the running test"""
        if self.worker and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait()
            self.on_test_stopped()
    
    def on_test_finished(self, result: dict):
        """Handle test completion"""
        self.results = result
        self.summary = summarize(result['results'], result['total_time'])
        self.timeseries = compute_time_series(result['results'], result['total_time'])
        
        # Update UI
        self.run_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.export_json_button.setEnabled(True)
        self.export_csv_button.setEnabled(True)
        self.export_html_button.setEnabled(True)
        
        # Log completion
        self.log_to_console("")
        self.log_to_console("=== Test Complete ===")
        self.log_to_console(f"Results computed and displayed in tabs")
        self.log_to_console(f"Export options are now available")
        
        # Display results
        self.display_summary()
        self.display_summary_table()
        self.display_timeseries()
        if MATPLOTLIB_AVAILABLE:
            self.chart_widget.plot_timeseries(self.timeseries)
    
    def on_test_error(self, error_msg: str):
        """Handle test error"""
        self.run_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.log_to_console(f"ERROR: {error_msg}")
        QMessageBox.critical(self, "Test Error", f"An error occurred:\n{error_msg}")
    
    def on_test_stopped(self):
        """Handle test stopped by user"""
        self.run_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.summary_text.append("\nTest stopped by user.")
        self.log_to_console("Test stopped by user.")
    
    def log_to_console(self, message: str):
        """Append a message to the console tab"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        self.console_text.append(f"[{timestamp}] {message}")
    
    def display_summary(self):
        """Display summary in text format"""
        if not self.summary:
            return
        
        text = "=== API Performance Summary ===\n\n"
        text += f"Total requests: {self.summary['total_requests']}\n"
        text += f"Successful: {self.summary['successful_requests']}\n"
        text += f"Failed: {self.summary['failed_requests']}\n"
        text += f"Total duration: {self.summary.get('total_duration_ms', 0):.3f} ms\n"
        text += f"Requests/sec: {self.summary['requests_per_second']:.2f}\n"
        
        if self.summary.get('min_ms') is not None:
            text += "\nLatency (ms):\n"
            text += f"  min:    {self.summary['min_ms']:.3f}\n"
            text += f"  mean:   {self.summary['mean_ms']:.3f}\n"
            text += f"  median: {self.summary['median_ms']:.3f}\n"
            text += f"  max:    {self.summary['max_ms']:.3f}\n"
            text += f"  stdev:  {self.summary['stdev_ms']:.3f}\n"
            text += f"  p50:    {self.summary['p50_ms']:.3f}\n"
            text += f"  p90:    {self.summary['p90_ms']:.3f}\n"
            text += f"  p95:    {self.summary['p95_ms']:.3f}\n"
            text += f"  p99:    {self.summary['p99_ms']:.3f}\n"
        
        text += "\nStatus codes:\n"
        for status, count in sorted(self.summary['status_counts'].items()):
            text += f"  {status}: {count}\n"
        
        self.summary_text.setText(text)
    
    def display_summary_table(self):
        """Display summary in table format"""
        if not self.summary:
            return
        
        self.summary_table.setRowCount(len(self.summary))
        row = 0
        for key, value in sorted(self.summary.items()):
            self.summary_table.setItem(row, 0, QTableWidgetItem(str(key)))
            if isinstance(value, float):
                self.summary_table.setItem(row, 1, QTableWidgetItem(f"{value:.3f}"))
            else:
                self.summary_table.setItem(row, 1, QTableWidgetItem(str(value)))
            row += 1
        
        self.summary_table.resizeColumnToContents(0)
    
    def display_timeseries(self):
        """Display time series data in table"""
        if not self.timeseries:
            return
        
        # Set up columns
        columns = ['second', 'count', 'successes', 'failures', 'rps', 'avg_latency_ms', 'p50_ms', 'p90_ms']
        self.timeseries_table.setColumnCount(len(columns))
        self.timeseries_table.setHorizontalHeaderLabels(columns)
        self.timeseries_table.setRowCount(len(self.timeseries))
        
        for row, entry in enumerate(self.timeseries):
            self.timeseries_table.setItem(row, 0, QTableWidgetItem(str(entry.get('second', ''))))
            self.timeseries_table.setItem(row, 1, QTableWidgetItem(str(entry.get('count', ''))))
            self.timeseries_table.setItem(row, 2, QTableWidgetItem(str(entry.get('successes', ''))))
            self.timeseries_table.setItem(row, 3, QTableWidgetItem(str(entry.get('failures', ''))))
            self.timeseries_table.setItem(row, 4, QTableWidgetItem(str(entry.get('requests_per_second', ''))))
            
            avg_lat = entry.get('avg_latency_ms')
            self.timeseries_table.setItem(row, 5, QTableWidgetItem(f"{avg_lat:.3f}" if avg_lat is not None else ''))
            
            p50 = entry.get('p50_ms')
            self.timeseries_table.setItem(row, 6, QTableWidgetItem(f"{p50:.3f}" if p50 is not None else ''))
            
            p90 = entry.get('p90_ms')
            self.timeseries_table.setItem(row, 7, QTableWidgetItem(f"{p90:.3f}" if p90 is not None else ''))
        
        self.timeseries_table.resizeColumnsToContents()
    
    def export_results(self, format_type: str):
        """Export results in specified format"""
        if not self.results or not self.summary:
            QMessageBox.warning(self, "Export Error", "No results to export")
            return
        
        if format_type == 'json':
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Export JSON", "", "JSON Files (*.json)"
            )
            if file_path:
                self.export_json(file_path)
        
        elif format_type == 'csv':
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Export CSV", "", "CSV Files (*.csv)"
            )
            if file_path:
                self.export_csv(file_path)
        
        elif format_type == 'html':
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Export HTML Report", "", "HTML Files (*.html)"
            )
            if file_path:
                self.export_html(file_path)
    
    def export_json(self, file_path: str):
        """Export results as JSON"""
        try:
            self.log_to_console(f"Exporting results to JSON: {file_path}")
            output = {
                'summary': self.summary,
                'timeseries': self.timeseries,
                'total_time_s': self.results['total_time'],
            }
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(output, f, indent=2)
            self.log_to_console(f"JSON export successful")
            QMessageBox.information(self, "Export Success", f"Results exported to:\n{file_path}")
        except Exception as e:
            self.log_to_console(f"JSON export failed: {str(e)}")
            QMessageBox.critical(self, "Export Error", f"Failed to export JSON:\n{str(e)}")
    
    def export_csv(self, file_path: str):
        """Export results as CSV"""
        try:
            self.log_to_console(f"Exporting results to CSV: {file_path}")
            # Export summary CSV
            base_path = file_path.rsplit('.', 1)[0]
            summary_path = f"{base_path}_summary.csv"
            timeseries_path = f"{base_path}_timeseries.csv"
            requests_path = f"{base_path}_requests.csv"
            
            write_summary_csv(self.summary, summary_path)
            write_timeseries_csv(self.timeseries, timeseries_path)
            write_request_log_csv(self.results['results'], requests_path)
            
            self.log_to_console(f"CSV export successful (3 files created)")
            msg = f"Results exported to:\n{summary_path}\n{timeseries_path}\n{requests_path}"
            QMessageBox.information(self, "Export Success", msg)
        except Exception as e:
            self.log_to_console(f"CSV export failed: {str(e)}")
            QMessageBox.critical(self, "Export Error", f"Failed to export CSV:\n{str(e)}")
    
    def export_html(self, file_path: str):
        """Export results as HTML report"""
        try:
            self.log_to_console(f"Generating HTML report: {file_path}")
            generate_html_report(
                file_path,
                self.summary,
                self.timeseries,
                request_log=None,
                timeseries_json=None,
                summary_json=None,
                summary_csv=None,
                timeseries_csv=None,
                plot_png=None
            )
            self.log_to_console(f"HTML report generated successfully")
            QMessageBox.information(self, "Export Success", f"HTML report exported to:\n{file_path}")
        except Exception as e:
            self.log_to_console(f"HTML export failed: {str(e)}")
            QMessageBox.critical(self, "Export Error", f"Failed to export HTML:\n{str(e)}")
