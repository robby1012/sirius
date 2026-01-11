"""Authentication dialog for Sirius - API Performance Tester"""

import base64
from typing import Dict, Any, Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QGroupBox, QStackedWidget, QWidget,
    QFormLayout, QTextEdit
)
from PyQt6.QtCore import Qt


class AuthDialog(QDialog):
    """Dialog for configuring API authentication"""

    def __init__(self, parent=None, current_auth: Optional[Dict[str, Any]] = None):
        super().__init__(parent)
        self.auth_config = current_auth or {'type': 'None'}
        self.init_ui()
        self.load_config()

    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Authentication Configuration")
        self.setMinimumSize(500, 400)
        
        layout = QVBoxLayout(self)
        
        # Auth type selector
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Auth Type:"))
        self.auth_type_combo = QComboBox()
        self.auth_type_combo.addItems([
            "None",
            "Basic Auth",
            "Bearer Token",
            "API Key",
            "OAuth 2.0",
            "Digest Auth",
            "AWS Signature"
        ])
        self.auth_type_combo.currentTextChanged.connect(self.on_auth_type_changed)
        type_layout.addWidget(self.auth_type_combo)
        type_layout.addStretch()
        layout.addLayout(type_layout)
        
        # Stacked widget for different auth types
        self.auth_stack = QStackedWidget()
        
        # None
        self.create_none_widget()
        
        # Basic Auth
        self.create_basic_auth_widget()
        
        # Bearer Token
        self.create_bearer_token_widget()
        
        # API Key
        self.create_api_key_widget()
        
        # OAuth 2.0
        self.create_oauth2_widget()
        
        # Digest Auth
        self.create_digest_auth_widget()
        
        # AWS Signature
        self.create_aws_signature_widget()
        
        layout.addWidget(self.auth_stack)
        
        # Preview section
        preview_group = QGroupBox("Preview (Headers/Parameters)")
        preview_layout = QVBoxLayout()
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setMaximumHeight(80)
        preview_layout.addWidget(self.preview_text)
        preview_group.setLayout(preview_layout)
        layout.addWidget(preview_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        preview_btn = QPushButton("Preview")
        preview_btn.clicked.connect(self.update_preview)
        preview_btn.setMinimumWidth(100)
        preview_btn.setStyleSheet("QPushButton { background-color: #1020aa; color: white; padding: 6px; }")
        button_layout.addWidget(preview_btn)
        
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.accept)
        self.save_btn.setMinimumWidth(100)
        self.save_btn.setStyleSheet("QPushButton { background-color: #27ae60; color: white; font-weight: bold; padding: 6px; }")
        button_layout.addWidget(self.save_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setMinimumWidth(100)
        cancel_btn.setStyleSheet("QPushButton { background-color: #ff1133; color: white; padding: 6px; }")
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
    
    def create_none_widget(self):
        """Create widget for no authentication"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        label = QLabel("No authentication will be used.")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)
        layout.addStretch()
        self.auth_stack.addWidget(widget)
    
    def create_basic_auth_widget(self):
        """Create widget for Basic Authentication"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(12)
        
        # Username
        username_layout = QHBoxLayout()
        username_label = QLabel("Username:")
        username_label.setMinimumWidth(100)
        username_layout.addWidget(username_label)
        self.basic_username = QLineEdit()
        self.basic_username.setPlaceholderText("Enter username")
        username_layout.addWidget(self.basic_username, stretch=1)
        layout.addLayout(username_layout)
        
        # Password
        password_layout = QHBoxLayout()
        password_label = QLabel("Password:")
        password_label.setMinimumWidth(100)
        password_layout.addWidget(password_label)
        self.basic_password = QLineEdit()
        self.basic_password.setPlaceholderText("Enter password")
        self.basic_password.setEchoMode(QLineEdit.EchoMode.Password)
        password_layout.addWidget(self.basic_password, stretch=1)
        layout.addLayout(password_layout)
        
        # Info
        info_label = QLabel("Basic Auth will add an 'Authorization: Basic <encoded>' header")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: gray; font-size: 11px; margin-left: 100px;")
        layout.addWidget(info_label)
        layout.addStretch()
        
        self.auth_stack.addWidget(widget)
    
    def create_bearer_token_widget(self):
        """Create widget for Bearer Token Authentication"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(12)
        
        # Token
        token_layout = QHBoxLayout()
        token_label = QLabel("Token:")
        token_label.setMinimumWidth(100)
        token_layout.addWidget(token_label)
        self.bearer_token = QLineEdit()
        self.bearer_token.setPlaceholderText("Enter bearer token")
        token_layout.addWidget(self.bearer_token, stretch=1)
        layout.addLayout(token_layout)
        
        # Info
        info_label = QLabel("Bearer Token will add an 'Authorization: Bearer <token>' header")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: gray; font-size: 11px; margin-left: 100px;")
        layout.addWidget(info_label)
        layout.addStretch()
        
        self.auth_stack.addWidget(widget)
    
    def create_api_key_widget(self):
        """Create widget for API Key Authentication"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(12)
        
        # Key Name
        name_layout = QHBoxLayout()
        name_label = QLabel("Key Name:")
        name_label.setMinimumWidth(100)
        name_layout.addWidget(name_label)
        self.api_key_name = QLineEdit()
        self.api_key_name.setPlaceholderText("e.g., X-API-Key, api_key")
        name_layout.addWidget(self.api_key_name, stretch=1)
        layout.addLayout(name_layout)
        
        # Key Value
        value_layout = QHBoxLayout()
        value_label = QLabel("Key Value:")
        value_label.setMinimumWidth(100)
        value_layout.addWidget(value_label)
        self.api_key_value = QLineEdit()
        self.api_key_value.setPlaceholderText("Enter API key value")
        value_layout.addWidget(self.api_key_value, stretch=1)
        layout.addLayout(value_layout)
        
        # Location
        location_layout = QHBoxLayout()
        location_label = QLabel("Add to:")
        location_label.setMinimumWidth(100)
        location_layout.addWidget(location_label)
        self.api_key_location = QComboBox()
        self.api_key_location.addItems(["Header", "Query Parameter"])
        self.api_key_location.setMaximumWidth(200)
        location_layout.addWidget(self.api_key_location)
        location_layout.addStretch()
        layout.addLayout(location_layout)
        
        # Info
        info_label = QLabel("API Key will be added as a header or query parameter")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: gray; font-size: 11px; margin-left: 100px;")
        layout.addWidget(info_label)
        layout.addStretch()
        
        self.auth_stack.addWidget(widget)
    
    def create_oauth2_widget(self):
        """Create widget for OAuth 2.0 Authentication"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(12)
        
        # Access Token
        token_layout = QHBoxLayout()
        token_label = QLabel("Access Token:")
        token_label.setMinimumWidth(100)
        token_layout.addWidget(token_label)
        self.oauth2_token = QLineEdit()
        self.oauth2_token.setPlaceholderText("Enter access token")
        token_layout.addWidget(self.oauth2_token, stretch=1)
        layout.addLayout(token_layout)
        
        # Prefix
        prefix_layout = QHBoxLayout()
        prefix_label = QLabel("Prefix:")
        prefix_label.setMinimumWidth(100)
        prefix_layout.addWidget(prefix_label)
        self.oauth2_prefix = QComboBox()
        self.oauth2_prefix.addItems(["Bearer", "OAuth", "Token"])
        self.oauth2_prefix.setEditable(True)
        self.oauth2_prefix.setMaximumWidth(200)
        prefix_layout.addWidget(self.oauth2_prefix)
        prefix_layout.addStretch()
        layout.addLayout(prefix_layout)
        
        # Info
        info_label = QLabel("OAuth 2.0 will add an 'Authorization: <prefix> <token>' header\n(Manual token entry - automatic OAuth flow not implemented)")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: gray; font-size: 11px; margin-left: 100px;")
        layout.addWidget(info_label)
        layout.addStretch()
        
        self.auth_stack.addWidget(widget)
    
    def create_digest_auth_widget(self):
        """Create widget for Digest Authentication"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(12)
        
        # Username
        username_layout = QHBoxLayout()
        username_label = QLabel("Username:")
        username_label.setMinimumWidth(100)
        username_layout.addWidget(username_label)
        self.digest_username = QLineEdit()
        self.digest_username.setPlaceholderText("Enter username")
        username_layout.addWidget(self.digest_username, stretch=1)
        layout.addLayout(username_layout)
        
        # Password
        password_layout = QHBoxLayout()
        password_label = QLabel("Password:")
        password_label.setMinimumWidth(100)
        password_layout.addWidget(password_label)
        self.digest_password = QLineEdit()
        self.digest_password.setPlaceholderText("Enter password")
        self.digest_password.setEchoMode(QLineEdit.EchoMode.Password)
        password_layout.addWidget(self.digest_password, stretch=1)
        layout.addLayout(password_layout)
        
        # Info
        info_label = QLabel("Note: Digest Auth requires server challenge. This stores credentials for manual implementation.")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: orange; font-size: 11px; margin-left: 100px;")
        layout.addWidget(info_label)
        layout.addStretch()
        
        self.auth_stack.addWidget(widget)
    
    def create_aws_signature_widget(self):
        """Create widget for AWS Signature Authentication"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(12)
        
        # Access Key
        access_layout = QHBoxLayout()
        access_label = QLabel("Access Key:")
        access_label.setMinimumWidth(100)
        access_layout.addWidget(access_label)
        self.aws_access_key = QLineEdit()
        self.aws_access_key.setPlaceholderText("Enter AWS access key")
        access_layout.addWidget(self.aws_access_key, stretch=1)
        layout.addLayout(access_layout)
        
        # Secret Key
        secret_layout = QHBoxLayout()
        secret_label = QLabel("Secret Key:")
        secret_label.setMinimumWidth(100)
        secret_layout.addWidget(secret_label)
        self.aws_secret_key = QLineEdit()
        self.aws_secret_key.setPlaceholderText("Enter AWS secret key")
        self.aws_secret_key.setEchoMode(QLineEdit.EchoMode.Password)
        secret_layout.addWidget(self.aws_secret_key, stretch=1)
        layout.addLayout(secret_layout)
        
        # Region
        region_layout = QHBoxLayout()
        region_label = QLabel("Region:")
        region_label.setMinimumWidth(100)
        region_layout.addWidget(region_label)
        self.aws_region = QLineEdit()
        self.aws_region.setPlaceholderText("e.g., us-east-1")
        region_layout.addWidget(self.aws_region, stretch=1)
        layout.addLayout(region_layout)
        
        # Service
        service_layout = QHBoxLayout()
        service_label = QLabel("Service:")
        service_label.setMinimumWidth(100)
        service_layout.addWidget(service_label)
        self.aws_service = QLineEdit()
        self.aws_service.setPlaceholderText("e.g., execute-api, s3")
        service_layout.addWidget(self.aws_service, stretch=1)
        layout.addLayout(service_layout)
        
        # Info
        info_label = QLabel("Note: AWS Signature v4 requires complex signing. This stores credentials for manual implementation.")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: orange; font-size: 11px; margin-left: 100px;")
        layout.addWidget(info_label)
        layout.addStretch()
        
        self.auth_stack.addWidget(widget)
    
    def on_auth_type_changed(self, auth_type: str):
        """Handle auth type selection change"""
        index_map = {
            "None": 0,
            "Basic Auth": 1,
            "Bearer Token": 2,
            "API Key": 3,
            "OAuth 2.0": 4,
            "Digest Auth": 5,
            "AWS Signature": 6
        }
        self.auth_stack.setCurrentIndex(index_map.get(auth_type, 0))
        self.update_preview()
    
    def load_config(self):
        """Load existing configuration"""
        auth_type = self.auth_config.get('type', 'None')
        self.auth_type_combo.setCurrentText(auth_type)
        
        if auth_type == 'Basic Auth':
            self.basic_username.setText(self.auth_config.get('username', ''))
            self.basic_password.setText(self.auth_config.get('password', ''))
        elif auth_type == 'Bearer Token':
            self.bearer_token.setText(self.auth_config.get('token', ''))
        elif auth_type == 'API Key':
            self.api_key_name.setText(self.auth_config.get('key_name', ''))
            self.api_key_value.setText(self.auth_config.get('key_value', ''))
            self.api_key_location.setCurrentText(self.auth_config.get('location', 'Header'))
        elif auth_type == 'OAuth 2.0':
            self.oauth2_token.setText(self.auth_config.get('token', ''))
            self.oauth2_prefix.setCurrentText(self.auth_config.get('prefix', 'Bearer'))
        elif auth_type == 'Digest Auth':
            self.digest_username.setText(self.auth_config.get('username', ''))
            self.digest_password.setText(self.auth_config.get('password', ''))
        elif auth_type == 'AWS Signature':
            self.aws_access_key.setText(self.auth_config.get('access_key', ''))
            self.aws_secret_key.setText(self.auth_config.get('secret_key', ''))
            self.aws_region.setText(self.auth_config.get('region', ''))
            self.aws_service.setText(self.auth_config.get('service', ''))
        
        self.update_preview()
    
    def get_config(self) -> Dict[str, Any]:
        """Get the current authentication configuration"""
        auth_type = self.auth_type_combo.currentText()
        config = {'type': auth_type}
        
        if auth_type == 'Basic Auth':
            config['username'] = self.basic_username.text().strip()
            config['password'] = self.basic_password.text()
        elif auth_type == 'Bearer Token':
            config['token'] = self.bearer_token.text().strip()
        elif auth_type == 'API Key':
            config['key_name'] = self.api_key_name.text().strip()
            config['key_value'] = self.api_key_value.text().strip()
            config['location'] = self.api_key_location.currentText()
        elif auth_type == 'OAuth 2.0':
            config['token'] = self.oauth2_token.text().strip()
            config['prefix'] = self.oauth2_prefix.currentText()
        elif auth_type == 'Digest Auth':
            config['username'] = self.digest_username.text().strip()
            config['password'] = self.digest_password.text()
        elif auth_type == 'AWS Signature':
            config['access_key'] = self.aws_access_key.text().strip()
            config['secret_key'] = self.aws_secret_key.text()
            config['region'] = self.aws_region.text().strip()
            config['service'] = self.aws_service.text().strip()
        
        return config
    
    def update_preview(self):
        """Update the preview of what will be added"""
        auth_type = self.auth_type_combo.currentText()
        preview_lines = []
        
        if auth_type == 'None':
            preview_lines.append("No authentication headers will be added.")
        
        elif auth_type == 'Basic Auth':
            username = self.basic_username.text().strip()
            password = self.basic_password.text()
            if username or password:
                credentials = f"{username}:{password}"
                encoded = base64.b64encode(credentials.encode()).decode()
                preview_lines.append("Header:")
                preview_lines.append(f"  Authorization: Basic {encoded}")
            else:
                preview_lines.append("Enter username and password to preview")
        
        elif auth_type == 'Bearer Token':
            token = self.bearer_token.text().strip()
            if token:
                preview_lines.append("Header:")
                preview_lines.append(f"  Authorization: Bearer {token}")
            else:
                preview_lines.append("Enter token to preview")
        
        elif auth_type == 'API Key':
            key_name = self.api_key_name.text().strip()
            key_value = self.api_key_value.text().strip()
            location = self.api_key_location.currentText()
            if key_name and key_value:
                if location == "Header":
                    preview_lines.append("Header:")
                    preview_lines.append(f"  {key_name}: {key_value}")
                else:
                    preview_lines.append("Query Parameter:")
                    preview_lines.append(f"  {key_name}={key_value}")
            else:
                preview_lines.append("Enter key name and value to preview")
        
        elif auth_type == 'OAuth 2.0':
            token = self.oauth2_token.text().strip()
            prefix = self.oauth2_prefix.currentText()
            if token:
                preview_lines.append("Header:")
                preview_lines.append(f"  Authorization: {prefix} {token}")
            else:
                preview_lines.append("Enter access token to preview")
        
        elif auth_type == 'Digest Auth':
            username = self.digest_username.text().strip()
            if username:
                preview_lines.append("Digest Auth Configuration:")
                preview_lines.append(f"  Username: {username}")
                preview_lines.append("  (Digest header will be computed after server challenge)")
            else:
                preview_lines.append("Enter username and password")
        
        elif auth_type == 'AWS Signature':
            access_key = self.aws_access_key.text().strip()
            region = self.aws_region.text().strip()
            service = self.aws_service.text().strip()
            if access_key and region and service:
                preview_lines.append("AWS Signature Configuration:")
                preview_lines.append(f"  Access Key: {access_key}")
                preview_lines.append(f"  Region: {region}")
                preview_lines.append(f"  Service: {service}")
                preview_lines.append("  (Signature headers will be computed per request)")
            else:
                preview_lines.append("Enter all AWS credentials to preview")
        
        self.preview_text.setText("\n".join(preview_lines))
    
    def apply_auth_to_headers(self, headers: Dict[str, str], url: str = "") -> Dict[str, str]:
        """Apply authentication to headers dictionary"""
        config = self.get_config()
        auth_type = config.get('type', 'None')
        
        if auth_type == 'Basic Auth':
            username = config.get('username', '')
            password = config.get('password', '')
            if username or password:
                credentials = f"{username}:{password}"
                encoded = base64.b64encode(credentials.encode()).decode()
                headers['Authorization'] = f'Basic {encoded}'
        
        elif auth_type == 'Bearer Token':
            token = config.get('token', '')
            if token:
                headers['Authorization'] = f'Bearer {token}'
        
        elif auth_type == 'API Key':
            key_name = config.get('key_name', '')
            key_value = config.get('key_value', '')
            location = config.get('location', 'Header')
            if key_name and key_value and location == 'Header':
                headers[key_name] = key_value
        
        elif auth_type == 'OAuth 2.0':
            token = config.get('token', '')
            prefix = config.get('prefix', 'Bearer')
            if token:
                headers['Authorization'] = f'{prefix} {token}'
        
        # Digest Auth and AWS Signature require more complex implementation
        # These would need to be handled in the worker with actual request signing
        
        return headers
    
    def get_query_params(self) -> Dict[str, str]:
        """Get query parameters to add to URL (e.g., for API Key in query)"""
        config = self.get_config()
        params = {}
        
        if config.get('type') == 'API Key':
            location = config.get('location', 'Header')
            if location == 'Query Parameter':
                key_name = config.get('key_name', '')
                key_value = config.get('key_value', '')
                if key_name and key_value:
                    params[key_name] = key_value
        
        return params
