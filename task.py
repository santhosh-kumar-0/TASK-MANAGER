import sys
import json
import os
import hashlib # For password hashing
from datetime import datetime, timedelta

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QTextEdit, QPushButton, QListWidget,
    QListWidgetItem, QLabel, QDateTimeEdit, QMessageBox,
    QStackedWidget, QComboBox, QFrame, QSizePolicy
)
from PyQt5.QtCore import Qt, QDateTime, QTimer, QSize
from PyQt5.QtGui import QFont, QIcon

# Imports for email notification (standard Python libraries)
import smtplib
import ssl
from email.mime.text import MIMEText

# Imports for SMS notification (Twilio)
# Make sure to install: pip install twilio
try:
    from twilio.rest import Client
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False
    print("Twilio library not found. SMS notifications will not be available. Please install it using 'pip install twilio'.")

# Imports for Native Desktop Notifications (Plyer)
# Make sure to install: pip install plyer
try:
    from plyer import notification
    PLYER_AVAILABLE = True
except ImportError:
    PLYER_AVAILABLE = False
    print("Plyer library not found. Native desktop notifications will not be available. Please install it using 'pip install plyer'.")


# --- Task Data Model ---
class Task:
    """
    Represents a single task with its properties.
    Includes attributes for name, due date, description, next step, priority,
    completion status, and a 'reminded' flag to prevent multiple time-based reminders.
    """
    def __init__(self, name, due_date, description="", next_step="", priority="Medium", completed=False, reminded=False):
        self.name = name
        self.due_date = due_date  # Stored as a string (e.g., "yyyy-MM-dd HH:mm")
        self.description = description
        self.next_step = next_step
        self.priority = priority # "High", "Medium", "Low"
        self.completed = completed
        self.reminded = reminded # True if a time-based reminder has been sent for this task

    def to_dict(self):
        """
        Converts the task object to a dictionary for JSON serialization.
        """
        return {
            "name": self.name,
            "due_date": self.due_date,
            "description": self.description,
            "next_step": self.next_step,
            "priority": self.priority,
            "completed": self.completed,
            "reminded": self.reminded
        }

    @classmethod
    def from_dict(cls, data):
        """
        Creates a Task object from a dictionary (e.g., loaded from JSON).
        Uses .get() for optional fields to handle older data structures gracefully.
        """
        return cls(
            data["name"],
            data["due_date"],
            data.get("description", ""),
            data.get("next_step", ""),
            data.get("priority", "Medium"),
            data.get("completed", False),
            data.get("reminded", False)
        )


# --- Custom UI Components ---
class CustomMessageBox(QMessageBox):
    """
    Custom styled QMessageBox for consistent UI across the application.
    Applies a dark theme to the message box itself and its buttons.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QMessageBox {
                background-color: #3c3c3c;
                color: #e0e0e0;
                font-family: "Segoe UI", Arial, sans-serif;
                font-size: 14px;
            }
            QMessageBox QLabel {
                color: #e0e0e0;
            }
            QMessageBox QPushButton {
                background-color: #6a9de3;
                border: none;
                border-radius: 5px;
                padding: 7px 15px;
                color: #ffffff;
                font-weight: bold;
            }
            QMessageBox QPushButton:hover {
                background-color: #7ab0ff;
            }
            QMessageBox QPushButton:pressed {
                background-color: #5d8edb;
            }
        """)

# --- Login Window ---
class LoginWindow(QWidget):
    def __init__(self, main_app_stacked_widget):
        super().__init__()
        self.main_app_stacked_widget = main_app_stacked_widget
        self.users_file = "users.json"
        self.init_ui()
        self.apply_stylesheet()

    def init_ui(self):
        self.setWindowTitle("Login")
        self.setGeometry(100, 100, 400, 300)

        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        main_layout.setAlignment(Qt.AlignCenter)

        login_frame = QFrame()
        login_frame.setObjectName("loginFrame")
        login_layout = QVBoxLayout(login_frame)
        login_layout.setContentsMargins(30, 30, 30, 30)
        login_layout.setSpacing(15)
        main_layout.addWidget(login_frame)

        title_label = QLabel("Welcome Back!")
        title_label.setObjectName("loginTitle")
        login_layout.addWidget(title_label, alignment=Qt.AlignCenter)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username")
        self.username_input.setFont(QFont("Segoe UI", 12))
        login_layout.addWidget(self.username_input)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setFont(QFont("Segoe UI", 12))
        login_layout.addWidget(self.password_input)

        login_button = QPushButton("Login")
        login_button.setObjectName("primaryButton")
        login_button.setFont(QFont("Segoe UI", 12, QFont.Bold))
        login_button.clicked.connect(self.login_user)
        login_layout.addWidget(login_button)

        signup_prompt_layout = QHBoxLayout()
        signup_prompt_layout.setAlignment(Qt.AlignCenter)
        signup_label = QLabel("Don't have an account?")
        signup_label.setObjectName("loginPrompt")
        signup_prompt_layout.addWidget(signup_label)

        signup_button = QPushButton("Sign Up")
        signup_button.setObjectName("tertiaryButtonSmall")
        signup_button.clicked.connect(self.show_signup_page)
        signup_prompt_layout.addWidget(signup_button)
        login_layout.addLayout(signup_prompt_layout)

        main_layout.addStretch()

    def apply_stylesheet(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
                color: #e0e0e0;
                font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
                font-size: 14px;
            }
            QFrame#loginFrame {
                background-color: #3c3c3c;
                border-radius: 15px;
                padding: 20px;
                min-width: 300px;
            }
            QLabel#loginTitle {
                font-size: 24px;
                font-weight: bold;
                color: #6a9de3;
                margin-bottom: 20px;
            }
            QLabel#loginPrompt {
                font-size: 13px;
                color: #bbbbbb;
            }
            QLineEdit {
                background-color: #4a4a4a;
                border: 1px solid #5c5c5c;
                border-radius: 8px;
                padding: 10px;
                color: #e0e0e0;
                selection-background-color: #6a9de3;
            }
            QLineEdit:focus {
                border: 1px solid #6a9de3;
                background-color: #404040;
            }
            QPushButton#primaryButton {
                background-color: #6a9de3;
                border: none;
                border-radius: 8px;
                padding: 12px 20px;
                color: #ffffff;
                font-weight: bold;
            }
            QPushButton#primaryButton:hover {
                background-color: #7ab0ff;
            }
            QPushButton#primaryButton:pressed {
                background-color: #5d8edb;
            }
            QPushButton#tertiaryButtonSmall {
                background-color: transparent;
                border: none;
                color: #7a6ae3;
                font-weight: bold;
                padding: 5px;
            }
            QPushButton#tertiaryButtonSmall:hover {
                color: #8f7aff;
                text-decoration: underline;
            }
        """)

    def show_message_box(self, title, message, icon=QMessageBox.Information, buttons=QMessageBox.Ok):
        msg = CustomMessageBox(self)
        msg.setWindowTitle(title)
        msg.setText(message)
        msg.setIcon(icon)
        msg.setStandardButtons(buttons)
        return msg.exec_()

    def hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()

    def load_users(self):
        try:
            with open(self.users_file, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
        except json.JSONDecodeError:
            self.show_message_box("Error", "Error reading user data file. Starting with no users.", QMessageBox.Critical)
            return {}

    def login_user(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()

        if not username or not password:
            self.show_message_box("Login Error", "Please enter both username and password.", QMessageBox.Warning)
            return

        users = self.load_users()
        hashed_password = self.hash_password(password)

        if username in users and users[username]["password"] == hashed_password:
            self.show_message_box("Login Success", f"Welcome, {username}!", QMessageBox.Information)
            # Find the MainTaskManagerUI instance and set the current user
            self.main_app_stacked_widget.findChild(MainTaskManagerUI).set_current_user(username)
            self.main_app_stacked_widget.setCurrentIndex(2) # Show MainTaskManagerUI
            self.username_input.clear()
            self.password_input.clear()
        else:
            self.show_message_box("Login Failed", "Invalid username or password.", QMessageBox.Critical)

    def show_signup_page(self):
        self.main_app_stacked_widget.setCurrentIndex(1) # Show SignUpWindow
        self.username_input.clear()
        self.password_input.clear()

# --- Sign Up Window ---
class SignUpWindow(QWidget):
    def __init__(self, main_app_stacked_widget):
        super().__init__()
        self.main_app_stacked_widget = main_app_stacked_widget
        self.users_file = "users.json"
        self.init_ui()
        self.apply_stylesheet()

    def init_ui(self):
        self.setWindowTitle("Sign Up")
        self.setGeometry(100, 100, 450, 450)

        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        main_layout.setAlignment(Qt.AlignCenter)

        signup_frame = QFrame()
        signup_frame.setObjectName("signupFrame")
        signup_layout = QVBoxLayout(signup_frame)
        signup_layout.setContentsMargins(30, 30, 30, 30)
        signup_layout.setSpacing(10)
        main_layout.addWidget(signup_frame)

        title_label = QLabel("Create Your Account")
        title_label.setObjectName("signupTitle")
        signup_layout.addWidget(title_label, alignment=Qt.AlignCenter)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username")
        self.username_input.setFont(QFont("Segoe UI", 11))
        signup_layout.addWidget(self.username_input)

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Email Address (Optional)")
        self.email_input.setFont(QFont("Segoe UI", 11))
        signup_layout.addWidget(self.email_input)

        # New: Phone number input field
        self.phone_number_input = QLineEdit()
        self.phone_number_input.setPlaceholderText("Mobile Number (e.g., +1234567890)")
        self.phone_number_input.setFont(QFont("Segoe UI", 11))
        signup_layout.addWidget(self.phone_number_input)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setFont(QFont("Segoe UI", 11))
        signup_layout.addWidget(self.password_input)

        self.retype_password_input = QLineEdit()
        self.retype_password_input.setPlaceholderText("Retype Password")
        self.retype_password_input.setEchoMode(QLineEdit.Password)
        self.retype_password_input.setFont(QFont("Segoe UI", 11))
        signup_layout.addWidget(self.retype_password_input)

        signup_button = QPushButton("Sign Up")
        signup_button.setObjectName("primaryButton")
        signup_button.setFont(QFont("Segoe UI", 12, QFont.Bold))
        signup_button.clicked.connect(self.register_user)
        signup_layout.addWidget(signup_button)

        back_button = QPushButton("Back to Login")
        back_button.setObjectName("tertiaryButtonSmall")
        back_button.clicked.connect(self.show_login_page)
        signup_layout.addWidget(back_button, alignment=Qt.AlignCenter)

        main_layout.addStretch()

    def apply_stylesheet(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
                color: #e0e0e0;
                font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
                font-size: 14px;
            }
            QFrame#signupFrame {
                background-color: #3c3c3c;
                border-radius: 15px;
                padding: 20px;
                min-width: 350px;
            }
            QLabel#signupTitle {
                font-size: 24px;
                font-weight: bold;
                color: #e39d6a; /* Orange highlight for signup */
                margin-bottom: 20px;
            }
            QLineEdit {
                background-color: #4a4a4a;
                border: 1px solid #5c5c5c;
                border-radius: 8px;
                padding: 10px;
                color: #e0e0e0;
                selection-background-color: #6a9de3;
            }
            QLineEdit:focus {
                border: 1px solid #6a9de3;
                background-color: #404040;
            }
            QPushButton#primaryButton {
                background-color: #6a9de3;
                border: none;
                border-radius: 8px;
                padding: 12px 20px;
                color: #ffffff;
                font-weight: bold;
            }
            QPushButton#primaryButton:hover {
                background-color: #7ab0ff;
            }
            QPushButton#primaryButton:pressed {
                background-color: #5d8edb;
            }
            QPushButton#tertiaryButtonSmall {
                background-color: transparent;
                border: none;
                color: #7a6ae3;
                font-weight: bold;
                padding: 5px;
            }
            QPushButton#tertiaryButtonSmall:hover {
                color: #8f7aff;
                text-decoration: underline;
            }
        """)

    def show_message_box(self, title, message, icon=QMessageBox.Information, buttons=QMessageBox.Ok):
        msg = CustomMessageBox(self)
        msg.setWindowTitle(title)
        msg.setText(message)
        msg.setIcon(icon)
        msg.setStandardButtons(buttons)
        return msg.exec_()

    def hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()

    def load_users(self):
        try:
            with open(self.users_file, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
        except json.JSONDecodeError:
            self.show_message_box("Error", "Error reading user data file. Starting with no users.", QMessageBox.Critical)
            return {}

    def save_users(self, users_data):
        try:
            with open(self.users_file, "w") as f:
                json.dump(users_data, f, indent=4)
        except Exception as e:
            self.show_message_box("Error", f"Failed to save user data: {e}", QMessageBox.Critical)

    def register_user(self):
        username = self.username_input.text().strip()
        email = self.email_input.text().strip()
        phone_number = self.phone_number_input.text().strip() # Get phone number
        password = self.password_input.text().strip()
        retype_password = self.retype_password_input.text().strip()

        if not username or not password or not retype_password:
            self.show_message_box("Sign Up Error", "Username, Password, and Retype Password are required.", QMessageBox.Warning)
            return
        if password != retype_password:
            self.show_message_box("Sign Up Error", "Passwords do not match.", QMessageBox.Warning)
            return
        if len(password) < 6:
            self.show_message_box("Sign Up Error", "Password must be at least 6 characters long.", QMessageBox.Warning)
            return

        users = self.load_users()
        if username in users:
            self.show_message_box("Sign Up Error", "Username already exists. Please choose a different one.", QMessageBox.Warning)
            return

        hashed_password = self.hash_password(password)
        # Store phone number with user data
        users[username] = {"password": hashed_password, "email": email, "phone_number": phone_number}
        self.save_users(users)
        self.show_message_box("Sign Up Success", "Account created successfully! You can now log in.", QMessageBox.Information)
        self.show_login_page() # Go back to login page after successful signup

    def show_login_page(self):
        self.main_app_stacked_widget.setCurrentIndex(0) # Show LoginWindow
        self.username_input.clear()
        self.email_input.clear()
        self.phone_number_input.clear() # Clear phone number field
        self.password_input.clear()
        self.retype_password_input.clear()


# --- Main Task Manager UI (Encapsulated) ---
class MainTaskManagerUI(QWidget):
    """
    This class contains the actual UI and logic for the task manager.
    It is now a child widget managed by the main TaskManagerApp (QStackedWidget).
    """
    def __init__(self):
        super().__init__()
        self.tasks = []
        self.current_user = None # To hold the logged-in username
        self.data_file_prefix = "_tasks.json" # Tasks file will be like "username_tasks.json"
        
        self.init_ui()
        self.apply_stylesheet()
        self.setup_reminder_timer() # Setup timer for time-based reminders

        # --- IMPORTANT: Configure your email and Twilio credentials here ---
        # For email: You'll need a Gmail account and an App Password (not your main password).
        # See Google Account Security -> 2-Step Verification -> App passwords.
        self.SENDER_EMAIL = "santhoshradha360@gmail.com"  # <--- REPLACE WITH YOUR GMAIL ADDRESS
        self.SENDER_EMAIL_PASSWORD = "your_app_password" # <--- REPLACE WITH YOUR GENERATED APP PASSWORD

        # For Twilio SMS: Sign up at twilio.com, get a phone number, then find your Account SID and Auth Token.
        # Install the library: pip install twilio
        self.TWILIO_ACCOUNT_SID = "AC0b23229c56eacd63f5f3232220af1271" # <--- REPLACE WITH YOUR TWILIO ACCOUNT SID
        self.TWILIO_AUTH_TOKEN = "92b977ca7be8741eaf023d651cf14a46"       # <--- REPLACE WITH YOUR TWILIO AUTH TOKEN
        self.TWILIO_PHONE_NUMBER = "+916374635898"         # <--- REPLACE WITH YOUR TWILIO PHONE NUMBER (e.g., +15017122661)

        self.check_external_service_configs() # Check if credentials are placeholders

    def check_external_service_configs(self):
        """Checks if external service credentials are still default placeholders and warns the user."""
        warnings = []
        if self.SENDER_EMAIL == "your_email@gmail.com" or self.SENDER_EMAIL_PASSWORD == "your_app_password":
            warnings.append("Email sender credentials are not configured. Email reminders will not be sent.")
        
        if self.TWILIO_ACCOUNT_SID == "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" or \
           self.TWILIO_AUTH_TOKEN == "your_auth_token" or \
           self.TWILIO_PHONE_NUMBER == "+1234567890":
            warnings.append("Twilio SMS credentials are not configured. SMS reminders will not be sent.")

        if warnings:
            self.show_message_box(
                "Configuration Warning",
                "Please configure the following external service credentials in the MainTaskManagerUI class:\n\n" + "\n".join(warnings),
                QMessageBox.Warning
            )

    def set_current_user(self, username):
        """Sets the current user and loads their tasks."""
        self.current_user = username
        self.load_tasks()
        self.refresh_task_list()
        self.show_message_box("Welcome", f"Logged in as {self.current_user}", QMessageBox.Information)

    def init_ui(self):
        self.main_layout = QHBoxLayout()
        self.setLayout(self.main_layout)

        # Left Panel: Task Input
        self.input_container = QFrame()
        self.input_container.setObjectName("inputContainer")
        self.input_layout = QVBoxLayout(self.input_container)
        self.input_layout.setContentsMargins(20, 20, 20, 20)
        self.input_layout.setSpacing(10)
        self.main_layout.addWidget(self.input_container, 1)

        self.input_layout.addWidget(self.create_label("Task Name:"))
        self.task_name_input = QLineEdit()
        self.task_name_input.setPlaceholderText("Enter task name")
        self.input_layout.addWidget(self.task_name_input)

        self.input_layout.addWidget(self.create_label("Due Date & Time:"))
        self.due_date_input = QDateTimeEdit(QDateTime.currentDateTime())
        self.due_date_input.setCalendarPopup(True)
        self.due_date_input.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.input_layout.addWidget(self.due_date_input)

        self.input_layout.addWidget(self.create_label("Description:"))
        self.description_input = QTextEdit()
        self.description_input.setPlaceholderText("Enter task description (optional)")
        self.input_layout.addWidget(self.description_input)

        self.input_layout.addWidget(self.create_label("Next Step:"))
        self.next_step_input = QLineEdit()
        self.next_step_input.setPlaceholderText("e.g., Email professor, Start research, etc.")
        self.input_layout.addWidget(self.next_step_input)

        self.input_layout.addWidget(self.create_label("Priority:"))
        self.priority_input = QComboBox()
        self.priority_input.addItems(["High", "Medium", "Low"])
        self.priority_input.setCurrentText("Medium")
        self.input_layout.addWidget(self.priority_input)

        self.button_layout = QHBoxLayout()
        self.input_layout.addLayout(self.button_layout)

        self.add_button = QPushButton("Add Task")
        self.add_button.setObjectName("primaryButton")
        self.add_button.clicked.connect(self.add_task)
        self.button_layout.addWidget(self.add_button)

        self.update_button = QPushButton("Update Task")
        self.update_button.setObjectName("secondaryButton")
        self.update_button.clicked.connect(self.update_selected_task)
        self.update_button.setEnabled(False)
        self.button_layout.addWidget(self.update_button)

        self.clear_button = QPushButton("Clear Fields")
        self.clear_button.setObjectName("tertiaryButton")
        self.clear_button.clicked.connect(self.clear_fields)
        self.button_layout.addWidget(self.clear_button)

        self.input_layout.addStretch()

        # Right Panel: Task List and Details
        self.list_container = QFrame()
        self.list_container.setObjectName("listContainer")
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(20, 20, 20, 20)
        self.list_layout.setSpacing(10)
        self.main_layout.addWidget(self.list_container, 2)

        self.list_layout.addWidget(self.create_label("Your Tasks:", "h1"))
        self.task_list_widget = QListWidget()
        self.task_list_widget.setObjectName("taskList")
        self.task_list_widget.itemSelectionChanged.connect(self.display_selected_task_details)
        self.list_layout.addWidget(self.task_list_widget)

        self.list_action_buttons_layout = QHBoxLayout()
        self.list_layout.addLayout(self.list_action_buttons_layout)

        self.complete_button = QPushButton("Mark as Complete")
        self.complete_button.setObjectName("actionButton")
        self.complete_button.clicked.connect(self.mark_task_complete)
        self.list_action_buttons_layout.addWidget(self.complete_button)

        self.delete_button = QPushButton("Delete Task")
        self.delete_button.setObjectName("actionButton")
        self.delete_button.clicked.connect(self.delete_task)
        self.list_action_buttons_layout.addWidget(self.delete_button)

        # Task details display
        self.task_details_stacked_widget = QStackedWidget()
        self.list_layout.addWidget(self.task_details_stacked_widget)

        self.empty_details_page = self.create_label("Select a task to view details.", "placeholder")
        self.task_details_stacked_widget.addWidget(self.empty_details_page)

        self.task_details_widget = QFrame()
        self.task_details_widget.setObjectName("detailsPanel")
        self.task_details_layout = QVBoxLayout(self.task_details_widget)
        self.task_details_layout.setContentsMargins(15, 15, 15, 15)
        self.task_details_stacked_widget.addWidget(self.task_details_widget)

        self.detail_name_label = self.create_label("<b>Task:</b>", "detail")
        self.task_details_layout.addWidget(self.detail_name_label)
        self.detail_due_label = self.create_label("<b>Due:</b>", "detail")
        self.task_details_layout.addWidget(self.detail_due_label)
        self.detail_desc_label = self.create_label("<b>Description:</b>", "detail")
        self.task_details_layout.addWidget(self.detail_desc_label)
        self.detail_next_step_label = self.create_label("<b>Next Step:</b>", "detail")
        self.task_details_layout.addWidget(self.detail_next_step_label)
        self.detail_priority_label = self.create_label("<b>Priority:</b>", "detail")
        self.task_details_layout.addWidget(self.detail_priority_label)
        self.detail_status_label = self.create_label("<b>Status:</b>", "detail")
        self.task_details_layout.addWidget(self.detail_status_label)

        self.task_details_layout.addStretch()

        self.refresh_task_list()

    def create_label(self, text, style_class=""):
        label = QLabel(text)
        if style_class:
            label.setObjectName(style_class)
        return label

    def apply_stylesheet(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
                color: #e0e0e0;
                font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
                font-size: 14px;
            }

            /* Container Frames */
            QFrame#inputContainer, QFrame#listContainer {
                background-color: #3c3c3c;
                border-radius: 10px;
                padding: 10px;
            }

            QFrame#detailsPanel {
                background-color: #4a4a4a;
                border-radius: 8px;
                border: 1px solid #555555;
            }

            /* Labels */
            QLabel {
                color: #f0f0f0;
                font-weight: 500;
            }
            QLabel#h1 {
                font-size: 20px;
                font-weight: bold;
                color: #6a9de3;
                margin-bottom: 5px;
            }
            QLabel#detail {
                font-size: 13px;
                color: #d0d0d0;
            }
            QLabel#placeholder {
                color: #999999;
                font-style: italic;
                font-size: 16px;
            }


            /* LineEdits (Task Name, Next Step) */
            QLineEdit, QTextEdit {
                background-color: #4a4a4a;
                border: 1px solid #5c5c5c;
                border-radius: 5px;
                padding: 8px;
                color: #e0e0e0;
                selection-background-color: #6a9de3;
            }
            QLineEdit:focus, QTextEdit:focus {
                border: 1px solid #6a9de3;
                background-color: #404040;
            }

            /* QTextEdit */
            QTextEdit {
                min-height: 80px;
            }

            /* QDateTimeEdit */
            QDateTimeEdit {
                background-color: #4a4a4a;
                border: 1px solid #5c5c5c;
                border-radius: 5px;
                padding: 8px;
                color: #e0e0e0;
                selection-background-color: #6a9de3;
            }
            QDateTimeEdit::drop-down {
                border: 0px;
                subcontrol-origin: padding;
                subcontrol-position: center right;
                width: 20px;
            }
            QDateTimeEdit::down-arrow {
                width: 0px;
                height: 0px;
            }

            /* QComboBox (Priority) */
            QComboBox {
                background-color: #4a4a4a;
                border: 1px solid #5c5c5c;
                border-radius: 5px;
                padding: 8px;
                color: #e0e0e0;
                selection-background-color: #6a9de3;
            }
            QComboBox::drop-down {
                border: 0px;
                subcontrol-origin: padding;
                subcontrol-position: center right;
                width: 20px;
            }
            QComboBox::down-arrow {
                width: 0px;
                height: 0px;
            }
            QComboBox QAbstractItemView {
                background-color: #4a4a4a;
                border: 1px solid #6a9de3;
                selection-background-color: #6a9de3;
                color: #e0e0e0;
            }


            /* Buttons */
            QPushButton {
                background-color: #5c5c5c;
                border: none;
                border-radius: 7px;
                padding: 10px 15px;
                color: #ffffff;
                font-weight: bold;
            }

            QPushButton:hover {
                background-color: #6a6a6a;
            }

            QPushButton:pressed {
                background-color: #4a4a4a;
            }

            QPushButton:disabled {
                background-color: #3a3a3a;
                color: #888888;
            }

            /* Specific button styles */
            QPushButton#primaryButton {
                background-color: #6a9de3;
            }
            QPushButton#primaryButton:hover {
                background-color: #7ab0ff;
            }
            QPushButton#primaryButton:pressed {
                background-color: #5d8edb;
            }

            QPushButton#secondaryButton {
                background-color: #e39d6a;
            }
            QPushButton#secondaryButton:hover {
                background-color: #ffb07a;
            }
            QPushButton#secondaryButton:pressed {
                background-color: #db8e5d;
            }

            QPushButton#tertiaryButton {
                background-color: #7a6ae3;
            }
            QPushButton#tertiaryButton:hover {
                background-color: #8f7aff;
            }
            QPushButton#tertiaryButton:pressed {
                background-color: #6e5edb;
            }

            QPushButton#actionButton {
                background-color: #555555;
            }
            QPushButton#actionButton:hover {
                background-color: #666666;
            }
            QPushButton#actionButton:pressed {
                background-color: #444444;
            }


            /* QListWidget (Task List) */
            QListWidget {
                background-color: #4a4a4a;
                border: 1px solid #5c5c5c;
                border-radius: 8px;
                padding: 5px;
                outline: 0;
            }

            QListWidget::item {
                padding: 8px 10px;
                margin-bottom: 3px;
                border-radius: 5px;
                color: #e0e0e0;
                background-color: #555555;
            }

            QListWidget::item:selected {
                background-color: #6a9de3;
                color: #ffffff;
                border: 1px solid #6a9de3;
            }

            QListWidget::item:hover:!selected {
                background-color: #606060;
            }

            /* Style for completed tasks in the list */
            QListWidget::item[completed="true"] {
                color: #aaaaaa;
                background-color: #444444;
                text-decoration: line-through;
            }
        """)

    def show_message_box(self, title, message, icon=QMessageBox.Information, buttons=QMessageBox.Ok):
        msg = CustomMessageBox(self)
        msg.setWindowTitle(title)
        msg.setText(message)
        msg.setIcon(icon)
        msg.setStandardButtons(buttons)
        return msg.exec_()

    def add_task(self):
        name = self.task_name_input.text().strip()
        due_date_str = self.due_date_input.dateTime().toString("yyyy-MM-dd HH:mm")
        description = self.description_input.toPlainText().strip()
        next_step = self.next_step_input.text().strip()
        priority = self.priority_input.currentText()

        if not name:
            self.show_message_box("Input Error", "Task name cannot be empty.", QMessageBox.Warning)
            return

        new_task = Task(name, due_date_str, description, next_step, priority, reminded=False)
        self.tasks.append(new_task)
        self.save_tasks()
        self.refresh_task_list()
        self.clear_fields()
        self.show_message_box("Success", f"Task '{name}' added.")

    def update_selected_task(self):
        current_row = self.task_list_widget.currentRow()
        if current_row < 0:
            self.show_message_box("Selection Error", "No task selected to update.", QMessageBox.Warning)
            return

        name = self.task_name_input.text().strip()
        due_date_str = self.due_date_input.dateTime().toString("yyyy-MM-dd HH:mm")
        description = self.description_input.toPlainText().strip()
        next_step = self.next_step_input.text().strip()
        priority = self.priority_input.currentText()

        if not name:
            self.show_message_box("Input Error", "Task name cannot be empty.", QMessageBox.Warning)
            return

        task_to_update = self.tasks[current_row]
        task_to_update.name = name
        task_to_update.due_date = due_date_str
        task_to_update.description = description
        task_to_update.next_step = next_step
        task_to_update.priority = priority
        task_to_update.reminded = False

        self.save_tasks()
        self.refresh_task_list()
        self.clear_fields()
        self.update_button.setEnabled(False)
        self.show_message_box("Success", f"Task '{name}' updated.")

    def delete_task(self):
        current_row = self.task_list_widget.currentRow()
        if current_row < 0:
            self.show_message_box("Selection Error", "No task selected to delete.", QMessageBox.Warning)
            return

        reply = self.show_message_box(
            "Confirm Deletion",
            "Are you sure you want to delete this task?",
            QMessageBox.Question,
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            deleted_task_name = self.tasks[current_row].name
            del self.tasks[current_row]
            self.save_tasks()
            self.refresh_task_list()
            self.clear_fields()
            self.update_button.setEnabled(False)
            self.show_message_box("Success", f"Task '{deleted_task_name}' deleted.")
        else:
            self.show_message_box("Canceled", "Task deletion canceled.")

    def mark_task_complete(self):
        current_row = self.task_list_widget.currentRow()
        if current_row < 0:
            self.show_message_box("Selection Error", "No task selected to mark complete/incomplete.", QMessageBox.Warning)
            return

        task = self.tasks[current_row]
        new_status = not task.completed
        task.completed = new_status
        task.reminded = True

        self.save_tasks()
        self.refresh_task_list()
        self.display_selected_task_details()

        if new_status:
            self.trigger_completion_notification(task)
        
        self.show_message_box("Status Update", f"Task '{task.name}' marked as {'Complete' if task.completed else 'Incomplete'}.")


    def display_selected_task_details(self):
        selected_items = self.task_list_widget.selectedItems()
        if not selected_items:
            self.task_details_stacked_widget.setCurrentWidget(self.empty_details_page)
            self.clear_fields_internal()
            self.update_button.setEnabled(False)
            self.complete_button.setEnabled(False)
            self.delete_button.setEnabled(False)
            return

        self.task_details_stacked_widget.setCurrentWidget(self.task_details_widget)
        self.update_button.setEnabled(True)
        self.complete_button.setEnabled(True)
        self.delete_button.setEnabled(True)

        current_row = self.task_list_widget.currentRow()
        task = self.tasks[current_row]

        self.task_name_input.setText(task.name)
        due_datetime = QDateTime.fromString(task.due_date, "yyyy-MM-dd HH:mm")
        self.due_date_input.setDateTime(due_datetime)
        self.description_input.setText(task.description)
        self.next_step_input.setText(task.next_step)
        self.priority_input.setCurrentText(task.priority)

        self.detail_name_label.setText(f"<b>Task:</b> {task.name}")
        self.detail_due_label.setText(f"<b>Due:</b> {task.due_date}")
        self.detail_desc_label.setText(f"<b>Description:</b> {task.description if task.description else 'N/A'}")
        self.detail_next_step_label.setText(f"<b>Next Step:</b> {task.next_step if task.next_step else 'N/A'}")
        self.detail_priority_label.setText(f"<b>Priority:</b> {task.priority}")
        status = "Complete" if task.completed else "Pending"
        self.detail_status_label.setText(f"<b>Status:</b> {status}")

        self.complete_button.setText(f"Mark as {'Incomplete' if task.completed else 'Complete'}")

    def clear_fields(self):
        self.clear_fields_internal()
        self.task_list_widget.clearSelection()
        self.task_details_stacked_widget.setCurrentWidget(self.empty_details_page)
        self.update_button.setEnabled(False)
        self.complete_button.setEnabled(False)
        self.delete_button.setEnabled(False)

    def clear_fields_internal(self):
        self.task_name_input.clear()
        self.due_date_input.setDateTime(QDateTime.currentDateTime())
        self.description_input.clear()
        self.next_step_input.clear()
        self.priority_input.setCurrentText("Medium")

    def refresh_task_list(self):
        self.task_list_widget.clear()

        priority_order = {"High": 0, "Medium": 1, "Low": 2}

        incomplete_tasks = [t for t in self.tasks if not t.completed]
        completed_tasks = [t for t in self.tasks if t.completed]

        incomplete_tasks.sort(key=lambda x: (priority_order.get(x.priority, 99), datetime.strptime(x.due_date, "%Y-%m-%d %H:%M")))
        completed_tasks.sort(key=lambda x: (priority_order.get(x.priority, 99), datetime.strptime(x.due_date, "%Y-%m-%d %H:%M")))

        for task in incomplete_tasks:
            item_text = f"{task.name} (Due: {task.due_date}) [Priority: {task.priority}]"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, task)
            item.setData(Qt.WhatsThisRole, "false")
            self.task_list_widget.addItem(item)

        if incomplete_tasks and completed_tasks:
            separator_item = QListWidgetItem("--- Completed Tasks ---")
            separator_item.setTextAlignment(Qt.AlignCenter)
            separator_item.setFlags(Qt.NoItemFlags)
            separator_item.setForeground(Qt.gray)
            self.task_list_widget.addItem(separator_item)

        for task in completed_tasks:
            item_text = f"✓ {task.name} (Due: {task.due_date}) [Priority: {task.priority}]"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, task)
            item.setData(Qt.WhatsThisRole, "true")
            self.task_list_widget.addItem(item)

    def load_tasks(self):
        """Loads tasks from the local JSON data file specific to the current user."""
        if self.current_user:
            user_data_file = f"{self.current_user}{self.data_file_prefix}"
            try:
                with open(user_data_file, "r") as f:
                    tasks_data = json.load(f)
                    self.tasks = [Task.from_dict(data) for data in tasks_data]
            except FileNotFoundError:
                self.tasks = []
            except json.JSONDecodeError:
                self.tasks = []
                self.show_message_box("Load Error", f"Error reading tasks file for {self.current_user}. Starting with an empty list.", QMessageBox.Warning)
        else:
            self.tasks = [] # No user logged in, so no tasks loaded

    def save_tasks(self):
        """Saves current tasks to the local JSON data file specific to the current user."""
        if self.current_user:
            user_data_file = f"{self.current_user}{self.data_file_prefix}"
            try:
                with open(user_data_file, "w") as f:
                    json.dump([task.to_dict() for task in self.tasks], f, indent=4)
            except Exception as e:
                self.show_message_box("Save Error", f"Failed to save tasks for {self.current_user}: {e}", QMessageBox.Critical)
        else:
            print("No user logged in, cannot save tasks.")


    def setup_reminder_timer(self):
        self.reminder_timer = QTimer(self)
        self.reminder_timer.setInterval(60 * 1000)
        self.reminder_timer.timeout.connect(self.check_reminders)
        self.reminder_timer.start()

    def check_reminders(self):
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Checking for reminders...")
        now = datetime.now()
        for task in self.tasks:
            if not task.completed and not task.reminded:
                try:
                    due_dt = datetime.strptime(task.due_date, "%Y-%m-%d %H:%M")
                    
                    if now >= due_dt:
                        print(f"Task '{task.name}' is overdue. Triggering notifications.")
                        self.trigger_all_notifications(task)
                        task.reminded = True
                        self.save_tasks()
                    else:
                        print(f"Task '{task.name}' is not yet due (Due: {task.due_date}).")
                except ValueError:
                    print(f"Warning: Could not parse due date for task '{task.name}': {task.due_date}")
            elif task.completed:
                print(f"Task '{task.name}' is completed, skipping reminder check.")
            elif task.reminded:
                print(f"Task '{task.name}' already reminded, skipping reminder check.")

    def trigger_completion_notification(self, task):
        title = "Task Completed!"
        message = f"Congratulations! You have successfully completed the task:\n\nTask: {task.name}\nDue: {task.due_date}\nPriority: {task.priority}"
        self.show_message_box(title, message, QMessageBox.Information)

    def trigger_all_notifications(self, task):
        print(f"Attempting to trigger all notifications for task: {task.name}")
        # 1. In-app Message Box Notification
        self.show_message_box(
            "Task Reminder: Time's Up!",
            f"Task: {task.name}\nDue: {task.due_date}\nPriority: {task.priority}\n\n"
            "This task's due time has passed!",
            QMessageBox.Warning
        )

        # 2. Actual Email Notification
        self.send_email_notification(task)

        # 3. Actual Mobile (SMS) Notification
        self.send_sms_notification(task)

        # 4. Native Desktop Notification (using plyer)
        if PLYER_AVAILABLE:
            try:
                notification.notify(
                    title=f"Task Overdue: {task.name}",
                    message=f"Due: {task.due_date}\nPriority: {task.priority}\n\n"
                            f"Action: {task.next_step if task.next_step else 'No specific next step'}",
                    app_name="Student Task Manager",
                    # app_icon='path/to/your/app_icon.ico', # Optional: Uncomment and replace with path to an icon file
                    timeout=10 # Notification will disappear after 10 seconds (or stay until dismissed)
                )
                print(f"Desktop notification sent for task: {task.name}")
            except Exception as e:
                print(f"Failed to send desktop notification: {e}")
        else:
            print("Plyer not available, skipping desktop notification.")

    def send_email_notification(self, task):
        """
        Sends an email notification using SMTP.
        Requires SENDER_EMAIL and SENDER_EMAIL_PASSWORD (App Password for Gmail) to be configured.
        """
        print(f"Attempting to send email for task: {task.name}")
        if not self.SENDER_EMAIL or not self.SENDER_EMAIL_PASSWORD or \
           self.SENDER_EMAIL == "your_email@gmail.com" or self.SENDER_EMAIL_PASSWORD == "your_app_password":
            print("Email sender credentials not configured or are placeholders. Skipping email notification.")
            return

        email_subject = f"OVERDUE: Task '{task.name}' is due!"
        email_body = (
            f"Dear Student,\n\n"
            f"This is a reminder that your task:\n"
            f"Name: {task.name}\n"
            f"Due Date: {task.due_date}\n"
            f"Priority: {task.priority}\n"
            f"Description: {task.description if task.description else 'N/A'}\n"
            f"Next Step: {task.next_step if task.next_step else 'N/A'}\n\n"
            f"The due time for this task has passed. Please take action.\n\n"
            f"Best regards,\nYour Task Manager"
        )
        
        users_data = MainTaskManagerApp.load_users_from_file() # Access users data
        recipient_email = users_data.get(self.current_user, {}).get("email") # Get current user's email

        if not recipient_email:
            print(f"No email address found for user {self.current_user}. Skipping email notification.")
            return

        message = MIMEText(email_body)
        message['Subject'] = email_subject
        message['From'] = self.SENDER_EMAIL
        message['To'] = recipient_email

        try:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
                server.login(self.SENDER_EMAIL, self.SENDER_EMAIL_PASSWORD)
                server.send_message(message)
            print(f"Email notification sent to {recipient_email}")
        except Exception as e:
            print(f"Failed to send email notification: {e}")
            self.show_message_box("Email Error", f"Failed to send email: {e}", QMessageBox.Critical)


    def send_sms_notification(self, task):
        """
        Sends an SMS notification using Twilio.
        Requires TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and TWILIO_PHONE_NUMBER to be configured.
        """
        print(f"Attempting to send SMS for task: {task.name}")
        if not TWILIO_AVAILABLE:
            print("Twilio library not available. Skipping SMS notification.")
            return
        
        if not self.TWILIO_ACCOUNT_SID or not self.TWILIO_AUTH_TOKEN or not self.TWILIO_PHONE_NUMBER or \
           self.TWILIO_ACCOUNT_SID == "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" or \
           self.TWILIO_AUTH_TOKEN == "your_auth_token" or \
           self.TWILIO_PHONE_NUMBER == "+1234567890":
            print("Twilio credentials not configured or are placeholders. Skipping SMS notification.")
            return

        sms_message = (
            f"Task Alert: '{task.name}' due on {task.due_date}. "
            f"Priority: {task.priority}. Time's up! Check your manager."
        )
        # Retrieve recipient mobile number from user data
        users_data = MainTaskManagerApp.load_users_from_file()
        recipient_mobile = users_data.get(self.current_user, {}).get("phone_number")

        if not recipient_mobile:
            print(f"No mobile number found for user {self.current_user}. Skipping SMS notification.")
            return
        
        try:
            client = Client(self.TWILIO_ACCOUNT_SID, self.TWILIO_AUTH_TOKEN)
            message = client.messages.create(
                to=recipient_mobile,
                from_=self.TWILIO_PHONE_NUMBER,
                body=sms_message
            )
            print(f"SMS notification sent to {recipient_mobile}. SID: {message.sid}")
        except Exception as e:
            print(f"Failed to send SMS notification: {e}")
            self.show_message_box("SMS Error", f"Failed to send SMS: {e}", QMessageBox.Critical)


# --- Main Application Manager (QStackedWidget) ---
class MainTaskManagerApp(QStackedWidget):
    """
    Manages the different application pages: Login, Signup, and the main Task Manager UI.
    """
    USERS_FILE = "users.json" # Class-level constant for user data file

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Student Task Manager")
        self.setGeometry(100, 100, 1000, 700) # Initial window size for the stacked widget

        self.login_page = LoginWindow(self)
        self.signup_page = SignUpWindow(self)
        self.main_task_manager_ui = MainTaskManagerUI() # The actual task manager UI

        self.addWidget(self.login_page)    # Index 0
        self.addWidget(self.signup_page)   # Index 1
        self.addWidget(self.main_task_manager_ui) # Index 2

        self.setCurrentIndex(0) # Start with the login page

    @classmethod
    def load_users_from_file(cls):
        """Class method to load users data, accessible from anywhere."""
        try:
            with open(cls.USERS_FILE, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
        except json.JSONDecodeError:
            print("Error reading user data file. Returning empty users dict.")
            return {}


# --- Main Application Entry Point ---
if __name__ == "__main__":
    app = QApplication(sys.argv)
    manager = MainTaskManagerApp() # Instantiate the stacked widget
    manager.show()
    sys.exit(app.exec_())
