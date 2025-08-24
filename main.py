##1.5
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.screenmanager import MDScreenManager
from kivymd.uix.button import MDRaisedButton, MDFlatButton, MDIconButton
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.toolbar import MDTopAppBar
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.dialog import MDDialog
from kivymd.uix.textfield import MDTextField
from kivymd.uix.filemanager import MDFileManager
from kivymd.toast import toast
from kivymd.uix.progressbar import MDProgressBar
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.utils import platform
from kivy.animation import Animation
import csv
import webbrowser
import os
import json
import sqlite3
from urllib.parse import quote_plus
from datetime import datetime, date, timedelta
import threading
import traceback

# Optional imports with fallbacks
try:
    from openpyxl import load_workbook
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False

# Android-specific imports
ANDROID_AVAILABLE = False
ASK_AVAILABLE = False
if platform == 'android':
    try:
        from android.permissions import request_permissions, Permission
        from jnius import autoclass
        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        Intent = autoclass('android.content.Intent')
        Uri = autoclass('android.net.Uri')
        ANDROID_AVAILABLE = True
    except ImportError:
        pass

    try:
        from androidstorage4kivy import Chooser, SharedStorage
        ASK_AVAILABLE = True
    except Exception:
        ASK_AVAILABLE = False


# -----------------------------
# SQLite storage for completions
# -----------------------------
class CompletionDB:
    def __init__(self, db_path):
        self.db_path = db_path
        self._ensure_db()

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute('PRAGMA journal_mode=WAL;')
        conn.execute('PRAGMA synchronous=NORMAL;')
        return conn

    def _ensure_db(self):
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS completions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    idx INTEGER,
                    address TEXT,
                    outcome TEXT,
                    amount REAL,
                    timestamp TEXT
                );
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON completions(timestamp);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_outcome ON completions(outcome);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_addr ON completions(address);")

    def insert_completion(self, idx, address, outcome, amount, ts_iso):
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO completions (idx, address, outcome, amount, timestamp) VALUES (?,?,?,?,?)",
                (idx, address, outcome, amount if amount is not None else None, ts_iso),
            )

    def delete_latest_by_idx(self, idx):
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT id FROM completions WHERE idx=? ORDER BY datetime(timestamp) DESC LIMIT 1",
                (idx,)
            )
            row = cur.fetchone()
            if row:
                conn.execute("DELETE FROM completions WHERE id=?", (row[0],))

    def clear_all(self):
        with self._connect() as conn:
            conn.execute("DELETE FROM completions")

    def query(self, date_from=None, date_to=None, outcome=None, search_text="", limit=50, offset=0):
        where = []
        params = []
        if date_from:
            where.append("datetime(timestamp) >= datetime(?)")
            params.append(date_from.isoformat())
        if date_to:
            where.append("datetime(timestamp) <= datetime(?)")
            params.append(date_to.isoformat())
        if outcome and outcome in ("PIF", "DA", "Done"):
            where.append("outcome = ?")
            params.append(outcome)
        if search_text:
            where.append("LOWER(address) LIKE ?")
            params.append(f"%{search_text.lower()}%")
        where_sql = (" WHERE " + " AND ".join(where)) if where else ""
        sql = f"SELECT idx, address, outcome, amount, timestamp FROM completions{where_sql} ORDER BY datetime(timestamp) DESC LIMIT ? OFFSET ?"
        with self._connect() as conn:
            cur = conn.execute(sql, (*params, limit, offset))
            rows = cur.fetchall()
        return [
            {
                'index': r[0],
                'address': r[1],
                'completion': {
                    'outcome': r[2],
                    'amount': "" if r[3] is None else f"{r[3]:.2f}",
                    'timestamp': r[4],
                },
            } for r in rows
        ]

    def count(self, date_from=None, date_to=None, outcome=None, search_text=""):
        where = []
        params = []
        if date_from:
            where.append("datetime(timestamp) >= datetime(?)")
            params.append(date_from.isoformat())
        if date_to:
            where.append("datetime(timestamp) <= datetime(?)")
            params.append(date_to.isoformat())
        if outcome and outcome in ("PIF", "DA", "Done"):
            where.append("outcome = ?")
            params.append(outcome)
        if search_text:
            where.append("LOWER(address) LIKE ?")
            params.append(f"%{search_text.lower()}%")
        where_sql = (" WHERE " + " AND ".join(where)) if where else ""
        sql = f"SELECT COUNT(*) FROM completions{where_sql}"
        with self._connect() as conn:
            cur = conn.execute(sql, params)
            (cnt,) = cur.fetchone()
        return int(cnt)


# -----------------------------
# Utility date helpers
# -----------------------------
def start_of_today():
    d = date.today()
    return datetime(d.year, d.month, d.day, 0, 0, 0)

def end_of_today():
    d = date.today()
    return datetime(d.year, d.month, d.day, 23, 59, 59)

def start_of_week():  # Monday 00:00
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    return datetime(monday.year, monday.month, monday.day, 0, 0, 0)

def end_of_week():    # Sunday 23:59:59
    s = start_of_week()
    sunday = s + timedelta(days=6)
    return datetime(sunday.year, sunday.month, sunday.day, 23, 59, 59)

def start_of_month():
    t = date.today()
    return datetime(t.year, t.month, 1, 0, 0, 0)

def end_of_month():
    t = date.today()
    if t.month == 12:
        first_next = datetime(t.year + 1, 1, 1)
    else:
        first_next = datetime(t.year, t.month + 1, 1)
    last = first_next - timedelta(seconds=1)
    return last


class AddressCard(MDCard):
    """Simplified, efficient address card with proper cleanup"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint_y = None
        self.height = dp(85)
        self.elevation = 2
        self.padding = dp(12)
        self.radius = [6]
        self.address_index = None
        self.address_text = ""
        self._setup_layout()

    def _setup_layout(self):
        self.main_layout = MDBoxLayout(orientation='vertical', spacing=dp(8), adaptive_height=True)
        self.address_label = MDLabel(theme_text_color="Primary", halign="left", shorten=True, font_size='14sp')
        self.bottom_row = MDBoxLayout(orientation='horizontal', size_hint_y=None, height=dp(32), spacing=dp(8))
        self.status_label = MDLabel(font_size='12sp', size_hint_x=None, width=dp(90), halign="center")
        self.nav_button = MDFlatButton(text="Navigate", size_hint=(None, None), size=(dp(80), dp(28)), font_size='11sp')
        self.action_button = MDFlatButton(size_hint=(None, None), size=(dp(80), dp(28)), font_size='11sp')
        self.bottom_row.add_widget(self.status_label)
        self.bottom_row.add_widget(MDLabel())  # Spacer
        self.bottom_row.add_widget(self.nav_button)
        self.bottom_row.add_widget(self.action_button)
        self.main_layout.add_widget(self.address_label)
        self.main_layout.add_widget(self.bottom_row)
        self.add_widget(self.main_layout)

    def update_card(self, index, address, status_info, callbacks):
        self.address_index = index
        self.address_text = address
        prefix = "â–º " if status_info.get('is_active') else ""
        self.address_label.text = f"{prefix}{index + 1}. {address}"
        self._update_appearance(status_info)
        self._update_buttons(status_info, callbacks)

    def _update_appearance(self, status_info):
        if status_info.get('is_active'):
            self.md_bg_color = (0.9, 0.95, 1.0, 1.0)
            self.elevation = 3
            self.status_label.text = "ACTIVE"
            self.status_label.text_color = [0, 0.5, 0.8, 1]
        elif status_info.get('is_completed'):
            self.elevation = 1
            completion = status_info.get('completion', {})
            outcome = completion.get('outcome', 'Done')
            if outcome == "PIF":
                self.md_bg_color = (0.92, 1.0, 0.92, 1.0)
                amount = completion.get('amount', '')
                self.status_label.text = f"PIF Â£{amount}" if amount else "PIF"
                self.status_label.text_color = [0, 0.7, 0, 1]
            elif outcome == "DA":
                self.md_bg_color = (1.0, 0.96, 0.96, 1.0)
                self.status_label.text = "DA"
                self.status_label.text_color = [0.8, 0.1, 0.1, 1]
            else:
                self.md_bg_color = (0.96, 0.96, 0.96, 1.0)
                self.status_label.text = "Done"
                self.status_label.text_color = [0, 0.5, 0.8, 1]
        else:
            self.md_bg_color = (1, 1, 1, 1)
            self.elevation = 2
            self.status_label.text = "PENDING"
            self.status_label.text_color = [0.6, 0.6, 0.6, 1]

    def _update_buttons(self, status_info, callbacks):
        try:
            self.nav_button.unbind(on_release=self._nav_callback)
        except:
            pass
        try:
            self.action_button.unbind(on_release=self._action_callback)
        except:
            pass
        if hasattr(self, 'cancel_button') and self.cancel_button and self.cancel_button.parent:
            try:
                self.cancel_button.unbind(on_release=self._cancel_callback)
                self.bottom_row.remove_widget(self.cancel_button)
            except:
                pass
        nav_callback = callbacks.get('navigate', lambda a, i: None)
        self._nav_callback = lambda x: nav_callback(self.address_text, self.address_index)
        self.nav_button.bind(on_release=self._nav_callback)
        if status_info.get('is_completed'):
            self.action_button.text = "Undo"
            self.action_button.theme_text_color = "Primary"
            undo_callback = callbacks.get('undo', lambda i: None)
            self._action_callback = lambda x: undo_callback(self.address_index)
            self.action_button.bind(on_release=self._action_callback)
        elif status_info.get('is_active'):
            self.action_button.text = "Complete"
            self.action_button.theme_text_color = "Custom"
            self.action_button.text_color = [0, 0.7, 0, 1]
            complete_callback = callbacks.get('complete', lambda i: None)
            self._action_callback = lambda x: complete_callback(self.address_index)
            self.action_button.bind(on_release=self._action_callback)
            if not hasattr(self, 'cancel_button') or not self.cancel_button:
                self.cancel_button = MDFlatButton(text="Cancel", size_hint=(None, None), size=(dp(60), dp(28)), font_size='11sp', theme_text_color="Error")
            try:
                self.cancel_button.unbind(on_release=self._cancel_callback)
            except:
                pass
            cancel_callback = callbacks.get('cancel', lambda: None)
            self._cancel_callback = lambda x: cancel_callback()
            self.cancel_button.bind(on_release=self._cancel_callback)
            self.bottom_row.add_widget(self.cancel_button)
        else:
            self.action_button.text = "Set Active"
            self.action_button.theme_text_color = "Primary"
            activate_callback = callbacks.get('activate', lambda i: None)
            self._action_callback = lambda x: activate_callback(self.address_index)
            self.action_button.bind(on_release=self._action_callback)

    def reset_for_reuse(self):
        self.address_index = None
        self.address_text = ""
        self.opacity = 1
        self.height = dp(85)
        self.disabled = False
        self.md_bg_color = (1, 1, 1, 1)
        self.elevation = 2
        try:
            self.nav_button.unbind(on_release=self._nav_callback)
        except:
            pass
        try:
            self.action_button.unbind(on_release=self._action_callback)
        except:
            pass
        if hasattr(self, 'cancel_button') and self.cancel_button and self.cancel_button.parent:
            try:
                self.cancel_button.unbind(on_release=self._cancel_callback)
                self.bottom_row.remove_widget(self.cancel_button)
            except:
                pass


class SearchField(MDTextField):
    def __init__(self, screen_instance, **kwargs):
        super().__init__(**kwargs)
        self.screen = screen_instance
        self._search_event = None
        self.hint_text = "Search addresses..."
        self.size_hint_y = None
        self.height = dp(48)
        self.mode = "rectangle"
        self.bind(text=self._on_text_change)

    def _on_text_change(self, instance, text):
        if self._search_event:
            self._search_event.cancel()
        self._search_event = Clock.schedule_once(lambda dt: self._perform_search(text), 0.3)

    def _perform_search(self, text):
        query = text.strip().lower()
        self.screen.current_search_query = query
        visible_count = 0
        for child in self.screen.address_layout.children:
            if isinstance(child, AddressCard):
                if not query or query in child.address_text.lower():
                    child.opacity = 1
                    child.height = dp(85)
                    child.disabled = False
                    visible_count += 1
                else:
                    child.opacity = 0
                    child.height = 0
                    child.disabled = True
        if visible_count == 0 and query:
            self.screen.show_no_results()
        else:
            self.screen.hide_no_results()


class MainScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.addresses = []
        self.completed_data = {}
        self.active_index = None
        self.current_search_query = ""
        self.current_day_data = None
        self.day_history = {}
        self._card_pool = []
        self._active_cards = {}
        self._no_results_card = None
        self.data_file = "address_navigator_data.json"
        self.file_manager = None
        self._completion_dialog = None
        self._payment_dialog = None
        self._payment_field = None
        self._current_completion_index = None
        self._day_tracking_dialog = None
        self._setup_android_storage()
        self._setup_ui()
        self._load_data()
        self._update_display()
        Clock.schedule_once(lambda dt: self._update_day_status_bar(), 0.2)
        if platform == 'android' and ANDROID_AVAILABLE:
            Clock.schedule_once(self._request_permissions, 0.5)

    def _setup_android_storage(self):
        self.storage_handler = None
        self.chooser = None
        if platform == 'android' and ASK_AVAILABLE:
            try:
                self.storage_handler = SharedStorage()
                self.chooser = Chooser(self._on_android_file_selected)
            except:
                pass

    def _setup_ui(self):
        layout = MDBoxLayout(orientation='vertical')
        self.toolbar = MDTopAppBar(title="Address Navigator", size_hint_y=None, height=dp(56))
        self.toolbar.right_action_items = [
            ["folder-open", lambda x: self.load_file()],
            ["check-all", lambda x: self.show_completed_screen()],
            ["calendar-clock", lambda x: self.show_day_tracking_dialog()],
            ["refresh", lambda x: self.refresh_display()],
        ]
        layout.add_widget(self.toolbar)
        self.day_status_card = MDCard(size_hint_y=None, height=dp(0), opacity=0, elevation=1, padding=[dp(12), dp(6)])
        self.day_status_layout = MDBoxLayout(orientation='horizontal', spacing=dp(12))
        self.day_status_label = MDLabel(text="", font_size='12sp', theme_text_color="Primary")
        self.end_day_button = MDFlatButton(text="End Day", size_hint_x=None, width=dp(80), font_size='11sp', theme_text_color="Error", on_release=lambda x: self.end_current_day())
        self.day_status_layout.add_widget(self.day_status_label)
        self.day_status_layout.add_widget(self.end_day_button)
        self.day_status_card.add_widget(self.day_status_layout)
        layout.add_widget(self.day_status_card)
        self.progress_bar = MDProgressBar(size_hint_y=None, height=dp(3), opacity=0)
        layout.add_widget(self.progress_bar)
        search_container = MDBoxLayout(orientation='vertical', size_hint_y=None, height=dp(64), padding=[dp(12), dp(8)])
        self.search_field = SearchField(self)
        search_container.add_widget(self.search_field)
        layout.add_widget(search_container)
        scroll = MDScrollView()
        self.address_layout = MDBoxLayout(orientation='vertical', adaptive_height=True, spacing=dp(8), padding=[dp(12), dp(12)])
        scroll.add_widget(self.address_layout)
        layout.add_widget(scroll)
        self.add_widget(layout)
        self._init_file_manager()

    def _init_file_manager(self):
        try:
            self.file_manager = MDFileManager(exit_manager=self._close_file_manager, select_path=self._on_file_selected, preview=False)
        except:
            self.file_manager = None

    def _get_card_from_pool(self):
        if self._card_pool:
            return self._card_pool.pop()
        return AddressCard()

    def _return_card_to_pool(self, card):
        if len(self._card_pool) < 20:
            card.reset_for_reuse()
            self._card_pool.append(card)

    def show_progress(self, show=True):
        Animation(opacity=1 if show else 0, duration=0.2).start(self.progress_bar)

    def _update_display(self):
        self._clear_address_display()
        if not self.addresses:
            self._show_welcome_card()
            return
        callbacks = {
            'navigate': self.navigate_to_address,
            'activate': self.set_active_address,
            'complete': self.show_completion_dialog,
            'undo': self.undo_completion,
            'cancel': self.cancel_active_address,
        }
        for i, address in enumerate(self.addresses):
            # Skip completed items in main list for responsiveness
            if i in self.completed_data:
                continue
            card = self._get_card_from_pool()
            status_info = {
                'is_active': i == self.active_index,
                'is_completed': i in self.completed_data,
                'completion': self.completed_data.get(i, {}),
            }
            card.update_card(i, address, status_info, callbacks)
            self.address_layout.add_widget(card)
            self._active_cards[i] = card
        if self.current_search_query:
            Clock.schedule_once(lambda dt: self.search_field._perform_search(self.current_search_query), 0.1)

    def _clear_address_display(self):
        for card in list(self._active_cards.values()):
            try:
                if card.parent:
                    card.parent.remove_widget(card)
            except Exception:
                pass
            self._return_card_to_pool(card)
        self._active_cards.clear()
        self.address_layout.clear_widgets()

    def _show_welcome_card(self):
        welcome_card = MDCard(size_hint_y=None, height=dp(160), elevation=2, padding=dp(20))
        layout = MDBoxLayout(orientation='vertical', spacing=dp(12))
        layout.add_widget(MDLabel(text="Welcome to Address Navigator", theme_text_color="Primary", font_style="H6", halign="center"))
        layout.add_widget(MDLabel(text="Load a CSV or Excel file to get started", theme_text_color="Secondary", halign="center"))
        layout.add_widget(MDRaisedButton(text="Load File", size_hint=(None, None), size=(dp(120), dp(36)), pos_hint={"center_x": 0.5}, on_release=lambda x: self.load_file()))
        welcome_card.add_widget(layout)
        self.address_layout.add_widget(welcome_card)

    def show_no_results(self):
        if self._no_results_card:
            return
        self._no_results_card = MDCard(size_hint_y=None, height=dp(80), elevation=1, padding=dp(16))
        label = MDLabel(text="No addresses match your search", theme_text_color="Secondary", halign="center")
        self._no_results_card.add_widget(label)
        self.address_layout.add_widget(self._no_results_card, index=0)

    def hide_no_results(self):
        if self._no_results_card:
            self.address_layout.remove_widget(self._no_results_card)
            self._no_results_card = None

    def set_active_address(self, index):
        if index == self.active_index:
            return
        previous_active = self.active_index
        self.active_index = index
        indices_to_update = [index]
        if previous_active is not None:
            indices_to_update.append(previous_active)
        self._update_specific_cards(indices_to_update)
        self._save_data()

    def cancel_active_address(self):
        if self.active_index is not None:
            previous_active = self.active_index
            self.active_index = None
            self._update_specific_cards([previous_active])
            self._save_data()
            toast("Active address cancelled")

    def _update_specific_cards(self, indices):
        callbacks = {
            'navigate': self.navigate_to_address,
            'activate': self.set_active_address,
            'complete': self.show_completion_dialog,
            'undo': self.undo_completion,
            'cancel': self.cancel_active_address,
        }
        for index in indices:
            if index in self._active_cards:
                card = self._active_cards[index]
                status_info = {
                    'is_active': index == self.active_index,
                    'is_completed': index in self.completed_data,
                    'completion': self.completed_data.get(index, {}),
                }
                card.update_card(index, card.address_text, status_info, callbacks)

    def show_completion_dialog(self, index):
        if not self._completion_dialog:
            self._create_completion_dialog()
        self._current_completion_index = index
        address = self.addresses[index] if index < len(self.addresses) else "Unknown"
        self._completion_dialog.text = f"Mark as completed: {address[:60]}..."
        self._completion_dialog.open()

    def _create_completion_dialog(self):
        self._completion_dialog = MDDialog(
            title="Complete Address",
            text="",
            buttons=[
                MDFlatButton(text="Cancel", on_release=lambda x: self._completion_dialog.dismiss()),
                MDFlatButton(text="Done", theme_text_color="Primary", on_release=lambda x: self._complete_address("Done", "")),
                MDFlatButton(text="DA", theme_text_color="Error", on_release=lambda x: self._complete_address("DA", "")),
                MDFlatButton(text="PIF", theme_text_color="Custom", text_color=[0, 0.7, 0, 1], on_release=lambda x: self._show_payment_dialog()),
            ],
        )

    def _show_payment_dialog(self):
        if not self._payment_dialog:
            self._create_payment_dialog()
        self._completion_dialog.dismiss()
        self._payment_field.text = ""
        self._payment_dialog.open()

    def _create_payment_dialog(self):
        self._payment_field = MDTextField(hint_text="Amount (Â£)", size_hint_x=None, width=dp(200), input_filter="float", halign="center")
        content = MDBoxLayout(orientation='vertical', spacing=dp(12), adaptive_height=True)
        content.add_widget(self._payment_field)
        self._payment_dialog = MDDialog(title="Payment Amount", type="custom", content_cls=content, buttons=[
            MDFlatButton(text="Cancel", on_release=lambda x: self._payment_dialog.dismiss()),
            MDFlatButton(text="Confirm", theme_text_color="Custom", text_color=[0, 0.7, 0, 1], on_release=lambda x: self._confirm_payment()),
        ])

    def _confirm_payment(self):
        try:
            amount_text = self._payment_field.text.strip()
            if not amount_text:
                toast("Please enter an amount")
                return
            amount = float(amount_text)
            if amount <= 0:
                toast("Amount must be greater than 0")
                return
            self._payment_dialog.dismiss()
            self._complete_address("PIF", f"{amount:.2f}")
        except ValueError:
            toast("Please enter a valid number")

    def _complete_address(self, outcome, amount):
        if self._current_completion_index is None:
            return
        index = self._current_completion_index
        self._completion_dialog.dismiss()
        completion_time = datetime.now().isoformat()
        self.completed_data[index] = {'outcome': outcome, 'amount': amount, 'timestamp': completion_time}

        # Day tracking
        if self.current_day_data and index < len(self.addresses):
            address_completion = {'index': index, 'address': self.addresses[index], 'outcome': outcome, 'amount': amount, 'timestamp': completion_time}
            self.current_day_data['addresses_completed'].append(address_completion)
            self._update_day_status_bar()

        # If the completed card is visible in the main list, remove it without redrawing everything
        if index in self._active_cards:
            try:
                card = self._active_cards.pop(index)
                if card.parent:
                    card.parent.remove_widget(card)
                self._return_card_to_pool(card)
            except Exception:
                pass

        # If this was the active address, clear active and refresh only the previous active card
        if self.active_index == index:
            prev_active = self.active_index
            self.active_index = None
            if prev_active is not None:
                self._update_specific_cards([prev_active])

        # Insert into SQLite
        try:
            app = MDApp.get_running_app()
            if hasattr(app, 'db') and app.db:
                addr = self.addresses[index] if index < len(self.addresses) else ""
                app.db.insert_completion(index, addr, outcome, float(amount) if amount else None, completion_time)
        except Exception as e:
            print(f"DB insert error: {e}")

        self._save_data()
        toast(f"Address marked as {outcome}")

    def undo_completion(self, index):
        if index in self.completed_data:
            if self.current_day_data:
                self.current_day_data['addresses_completed'] = [addr for addr in self.current_day_data['addresses_completed'] if addr.get('index') != index]
                self._update_day_status_bar()
            del self.completed_data[index]
            try:
                app = MDApp.get_running_app()
                if hasattr(app, 'db') and app.db:
                    app.db.delete_latest_by_idx(index)
            except Exception as e:
                print(f"DB delete error: {e}")
            # If the card is not in view (was removed earlier), rebuild the list so it reappears
            if index not in self._active_cards:
                self._update_display()
            else:
                self._update_specific_cards([index])
            self._save_data()
            toast("Completion undone")

    def navigate_to_address(self, address, index, from_completed=False):
        if not from_completed and index not in self.completed_data and index != self.active_index:
            self.set_active_address(index)
        try:
            encoded_address = quote_plus(str(address))
            if platform == 'android' and ANDROID_AVAILABLE:
                self._open_android_maps(encoded_address)
            else:
                self._open_web_maps(encoded_address)
        except Exception as e:
            toast(f"Navigation error: {str(e)}")
            try:
                webbrowser.open(f"https://www.google.com/maps/search/{encoded_address}")
            except:
                toast("Unable to open maps")

    def _open_android_maps(self, encoded_address):
        try:
            intent = Intent()
            intent.setAction(Intent.ACTION_VIEW)
            intent.setData(Uri.parse(f"geo:0,0?q={encoded_address}"))
            PythonActivity.mActivity.startActivity(intent)
        except Exception:
            self._open_web_maps(encoded_address)

    def _open_web_maps(self, encoded_address):
        webbrowser.open(f"https://www.google.com/maps/search/{encoded_address}")

    # Day tracking (as before, UK time formatting)
    def show_day_tracking_dialog(self):
        if not self._day_tracking_dialog:
            self._create_day_tracking_dialog()
        self._update_day_tracking_dialog()
        self._day_tracking_dialog.open()

    def _create_day_tracking_dialog(self):
        content = MDBoxLayout(orientation='vertical', spacing=dp(12), adaptive_height=True, size_hint_y=None)
        self._day_status_dialog_label = MDLabel(text="", theme_text_color="Primary", font_size='14sp', adaptive_height=True)
        content.add_widget(self._day_status_dialog_label)
        self._day_progress_label = MDLabel(text="", theme_text_color="Secondary", font_size='12sp', adaptive_height=True)
        content.add_widget(self._day_progress_label)
        button_layout = MDBoxLayout(orientation='horizontal', spacing=dp(8), size_hint_y=None, height=dp(40), adaptive_width=True)
        self._start_day_btn = MDRaisedButton(text="Start Day", size_hint_x=None, width=dp(100), on_release=lambda x: self.start_new_day())
        self._end_day_btn = MDFlatButton(text="End Day", size_hint_x=None, width=dp(100), theme_text_color="Error", on_release=lambda x: self.end_current_day())
        self._view_history_btn = MDFlatButton(text="View History", size_hint_x=None, width=dp(120), on_release=lambda x: self.show_day_history())
        button_layout.add_widget(self._start_day_btn)
        button_layout.add_widget(self._end_day_btn)
        button_layout.add_widget(self._view_history_btn)
        content.add_widget(button_layout)
        self._day_tracking_dialog = MDDialog(title="Day Tracking", type="custom", content_cls=content, buttons=[MDFlatButton(text="Close", on_release=lambda x: self._day_tracking_dialog.dismiss())])

    def _update_day_tracking_dialog(self):
        if not self._day_tracking_dialog:
            return
        today = datetime.now().strftime("%Y-%m-%d")
        if self.current_day_data:
            start_time = datetime.fromisoformat(self.current_day_data['start_time'])
            duration = datetime.now() - start_time
            hours = int(duration.total_seconds() // 3600)
            minutes = int((duration.total_seconds() % 3600) // 60)
            self._day_status_dialog_label.text = (
                f"Day started: {start_time.strftime('%H:%M')}\nDuration: {hours}h {minutes}m"
            )
            completed_today = len(self.current_day_data['addresses_completed'])
            self._day_progress_label.text = f"Addresses completed today: {completed_today}"
            self._start_day_btn.disabled = True
            self._end_day_btn.disabled = False
        else:
            self._day_status_dialog_label.text = "No active day session"
            if today in self.day_history:
                last_session = self.day_history[today]
                if isinstance(last_session, list) and last_session:
                    last_session = last_session[-1]
                completed = len(last_session.get('addresses_completed', []))
                end_time = last_session.get('end_time', 'Unknown')
                if end_time != 'Unknown':
                    try:
                        end_dt = datetime.fromisoformat(end_time)
                        end_time = end_dt.strftime('%H:%M')
                    except:
                        pass
                self._day_progress_label.text = f"Previous session today: {completed} addresses completed, ended at {end_time}"
            else:
                self._day_progress_label.text = "No sessions today"
            self._start_day_btn.disabled = False
            self._end_day_btn.disabled = True

    def start_new_day(self):
        today = datetime.now().strftime("%Y-%m-%d")
        start_time = datetime.now().isoformat()
        self.current_day_data = {'date': today, 'start_time': start_time, 'addresses_completed': [], 'total_addresses': len(self.addresses)}
        self._update_day_status_bar()
        self._save_data()
        self._day_tracking_dialog.dismiss()
        toast(f"Day started at {datetime.now().strftime('%H:%M')}")

    def end_current_day(self):
        if not self.current_day_data:
            toast("No active day session")
            return
        end_time = datetime.now().isoformat()
        today = self.current_day_data['date']
        completed_addresses = self.current_day_data['addresses_completed']
        start_dt = datetime.fromisoformat(self.current_day_data['start_time'])
        end_dt = datetime.fromisoformat(end_time)
        duration_seconds = (end_dt - start_dt).total_seconds()
        outcomes = {}
        for addr_data in completed_addresses:
            outcome = addr_data.get('outcome', 'Done')
            outcomes[outcome] = outcomes.get(outcome, 0) + 1
        day_summary = {
            'date': today,
            'start_time': self.current_day_data['start_time'],
            'end_time': end_time,
            'duration_seconds': duration_seconds,
            'addresses_completed': completed_addresses,
            'total_addresses': self.current_day_data['total_addresses'],
            'outcomes_summary': outcomes,
            'completion_rate': len(completed_addresses) / max(1, self.current_day_data['total_addresses']) * 100,
        }
        if today not in self.day_history:
            self.day_history[today] = []
        if isinstance(self.day_history[today], dict):
            self.day_history[today] = [self.day_history[today]]
        elif not isinstance(self.day_history[today], list):
            self.day_history[today] = []
        self.day_history[today].append(day_summary)
        self.current_day_data = None
        self._update_day_status_bar()
        self._save_data()
        if hasattr(self, '_day_tracking_dialog') and self._day_tracking_dialog:
            self._day_tracking_dialog.dismiss()
        hours = int(duration_seconds // 3600)
        minutes = int((duration_seconds % 3600) // 60)
        completed_count = len(completed_addresses)
        toast(f"Day ended! Duration: {hours}h {minutes}m, Completed: {completed_count} addresses")

    def _update_day_status_bar(self):
        if self.current_day_data:
            completed_today = len(self.current_day_data['addresses_completed'])
            start_time = datetime.fromisoformat(self.current_day_data['start_time'])
            self.day_status_label.text = f"Day started: {start_time.strftime('%H:%M')} â€¢ Completed: {completed_today}"
            Animation(opacity=1, height=dp(40), duration=0.3).start(self.day_status_card)
        else:
            Animation(opacity=0, height=dp(0), duration=0.3).start(self.day_status_card)

    def show_day_history(self):
        if not self.day_history:
            toast("No day history available")
            return
        total_days = len(self.day_history)
        total_sessions = sum(len(sessions) if isinstance(sessions, list) else 1 for sessions in self.day_history.values())
        toast(f"History: {total_days} days, {total_sessions} sessions")

    # File handling
    def load_file(self):
        if platform == 'android' and self.chooser:
            try:
                self.chooser.choose_content('*/*')
                return
            except:
                pass
        if not self.file_manager:
            toast("File manager not available")
            return
        try:
            if platform == 'android':
                paths = ["/storage/emulated/0/Documents", "/storage/emulated/0/Download", "/storage/emulated/0"]
                for path in paths:
                    if os.path.exists(path):
                        self.file_manager.show(path)
                        return
                self.file_manager.show("/")
            else:
                self.file_manager.show(os.path.expanduser("~"))
        except Exception as e:
            toast(f"Error opening file browser: {str(e)}")

    def _on_android_file_selected(self, shared_file_list):
        def process():
            try:
                if not shared_file_list or not self.storage_handler:
                    return
                private_path = self.storage_handler.copy_from_shared(shared_file_list[0])
                if not private_path or not os.path.exists(private_path):
                    Clock.schedule_once(lambda dt: toast("Failed to access file"), 0)
                    return
                lower = private_path.lower()
                if lower.endswith('.csv'):
                    Clock.schedule_once(lambda dt: self._load_csv_file(private_path), 0)
                elif lower.endswith(('.xlsx', '.xls')) and OPENPYXL_AVAILABLE:
                    Clock.schedule_once(lambda dt: self._load_excel_file(private_path), 0)
                else:
                    Clock.schedule_once(lambda dt: toast("Unsupported file type"), 0)
            except Exception as e:
                Clock.schedule_once(lambda dt: toast(f"File error: {str(e)}"), 0)
        threading.Thread(target=process, daemon=True).start()

    def _on_file_selected(self, path):
        self._close_file_manager()
        lower = path.lower()
        if lower.endswith('.csv'):
            self._load_csv_file(path)
        elif lower.endswith(('.xlsx', '.xls')) and OPENPYXL_AVAILABLE:
            self._load_excel_file(path)
        else:
            toast("Please select a CSV or Excel file")

    def _close_file_manager(self):
        if self.file_manager:
            try:
                self.file_manager.close()
            except:
                pass

    def _load_csv_file(self, file_path):
        self.show_progress(True)
        def load_background():
            try:
                addresses = []
                for encoding in ['utf-8', 'utf-8-sig', 'latin1', 'cp1252']:
                    try:
                        with open(file_path, 'r', encoding=encoding) as f:
                            reader = csv.reader(f)
                            rows = list(reader)
                        break
                    except (UnicodeDecodeError, UnicodeError):
                        continue
                else:
                    Clock.schedule_once(lambda dt: toast("Could not read file - encoding issue"), 0)
                    Clock.schedule_once(lambda dt: self.show_progress(False), 0)
                    return
                if not rows:
                    Clock.schedule_once(lambda dt: toast("File is empty"), 0)
                    Clock.schedule_once(lambda dt: self.show_progress(False), 0)
                    return
                headers = [str(cell).lower() for cell in rows[0]]
                address_col = 0
                for i, header in enumerate(headers):
                    if 'address' in header:
                        address_col = i
                        break
                for row in rows[1:]:
                    if len(row) > address_col and row[address_col]:
                        address = str(row[address_col]).strip()
                        if address and address.lower() not in ['none', 'null', '']:
                            addresses.append(address)
                Clock.schedule_once(lambda dt: self._load_addresses_data(addresses), 0)
            except Exception as e:
                Clock.schedule_once(lambda dt: toast(f"Error reading CSV: {str(e)}"), 0)
                Clock.schedule_once(lambda dt: self.show_progress(False), 0)
        threading.Thread(target=load_background, daemon=True).start()

    def _load_excel_file(self, file_path):
        if not OPENPYXL_AVAILABLE:
            toast("Excel support not available")
            return
        self.show_progress(True)
        def load_background():
            try:
                workbook = load_workbook(file_path, read_only=True, data_only=True)
                worksheet = workbook.active
                rows = list(worksheet.iter_rows(values_only=True))
                workbook.close()
                if not rows:
                    Clock.schedule_once(lambda dt: toast("File is empty"), 0)
                    Clock.schedule_once(lambda dt: self.show_progress(False), 0)
                    return
                headers = [str(cell).lower() if cell else '' for cell in rows[0]]
                address_col = 0
                for i, header in enumerate(headers):
                    if 'address' in header:
                        address_col = i
                        break
                addresses = []
                for row in rows[1:]:
                    if len(row) > address_col and row[address_col]:
                        address = str(row[address_col]).strip()
                        if address and address.lower() not in ['none', 'null', '']:
                            addresses.append(address)
                Clock.schedule_once(lambda dt: self._load_addresses_data(addresses), 0)
            except Exception as e:
                Clock.schedule_once(lambda dt: toast(f"Error reading Excel: {str(e)}"), 0)
                Clock.schedule_once(lambda dt: self.show_progress(False), 0)
        threading.Thread(target=load_background, daemon=True).start()

    def _load_addresses_data(self, addresses):
        self.show_progress(False)
        if not addresses:
            toast("No addresses found in file")
            return
        self.addresses = addresses
        self.completed_data = {}
        self.active_index = None
        self.current_search_query = ""
        if self.current_day_data:
            self.end_current_day()
        self.search_field.text = ""
        self._update_display()
        self._save_data()
        toast(f"Loaded {len(addresses)} addresses")

    def show_completed_screen(self):
        """Ensure completed_screen exists before switching, then load."""
        if not hasattr(self, 'manager') or self.manager is None:
            return
        app = MDApp.get_running_app()
        if not any(screen.name == "completed_screen" for screen in self.manager.screens):
            try:
                completed_screen = CompletedScreen(app, name="completed_screen")
                self.manager.add_widget(completed_screen)
            except Exception as e:
                print("Error creating completed screen:", e)
                traceback.print_exc()
                toast("Unable to open Completed screen")
                return
        self.manager.current = "completed_screen"
        for screen in self.manager.screens:
            if screen.name == "completed_screen":
                screen.reset_and_load()
                break

    def get_completed_addresses(self):
        completed = []
        for index, completion_data in self.completed_data.items():
            if index < len(self.addresses):
                completed.append({'index': index, 'address': self.addresses[index], 'completion': completion_data})
        return completed

    def remove_from_completed(self, index):
        if index in self.completed_data:
            del self.completed_data[index]
            self._save_data()
            # If the card reappears in main list, refresh
            self._update_display()

    def clear_all_completed(self):
        completed_indices = list(self.completed_data.keys())
        self.completed_data.clear()
        self._save_data()
        self._update_display()
        toast("All completed addresses cleared")

    def refresh_display(self):
        self._update_display()
        toast("Display refreshed")

    def _save_data(self):
        try:
            data = {
                'addresses': self.addresses,
                'completed_data': self.completed_data,
                'active_index': self.active_index,
                'current_day_data': self.current_day_data,
                'day_history': self.day_history,
                'version': '2.4-sqlite-nochips',
            }
            filepath = self._get_data_file_path()
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Save error: {e}")

    def _load_data(self):
        try:
            filepath = self._get_data_file_path()
            if not os.path.exists(filepath):
                self._initialize_default_data()
                return
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.addresses = data.get('addresses', [])
            if 'completed_data' in data:
                self.completed_data = {int(k): v for k, v in data['completed_data'].items()}
            else:
                completed_set = set(data.get('completed_addresses', []))
                timestamps = data.get('completed_timestamps', {})
                outcomes = data.get('completed_outcomes', {})
                amounts = data.get('completed_amounts', {})
                self.completed_data = {}
                for index in completed_set:
                    self.completed_data[index] = {'outcome': outcomes.get(str(index), 'Done'), 'amount': amounts.get(str(index), ''), 'timestamp': timestamps.get(str(index), datetime.now().isoformat())}
            self.active_index = data.get('active_index')
            self.current_day_data = data.get('current_day_data')
            self.day_history = data.get('day_history', {})
            Clock.schedule_once(lambda dt: self._update_day_status_bar(), 0.1)
        except Exception as e:
            print(f"Load error: {e}")
            self._initialize_default_data()

    def _initialize_default_data(self):
        self.addresses = []
        self.completed_data = {}
        self.active_index = None
        self.current_day_data = None
        self.day_history = {}

    def _get_data_file_path(self):
        if platform == 'android' and ANDROID_AVAILABLE:
            try:
                app_path = PythonActivity.mActivity.getFilesDir().getAbsolutePath()
                return os.path.join(app_path, self.data_file)
            except:
                return self.data_file
        return os.path.join(os.path.expanduser("~"), self.data_file)

    def _request_permissions(self, dt):
        if platform == 'android' and ANDROID_AVAILABLE:
            try:
                request_permissions([Permission.READ_EXTERNAL_STORAGE, Permission.WRITE_EXTERNAL_STORAGE])
            except:
                pass


class CompletedScreen(MDScreen):
    """Completed addresses screen with compact Filter dialog, date/outcome filters, search, and SQLite-backed pagination"""
    def __init__(self, app_instance, **kwargs):
        super().__init__(**kwargs)
        self.app = app_instance
        # Filter state
        self.quick_range = 'today'  # today|week|month|all|custom
        self.date_from = start_of_today()
        self.date_to = end_of_today()
        self.outcome_filter = None  # None|PIF|DA|Done
        self.search_query = ""
        # Paging
        self.limit = 50
        self.offset = 0
        self.total_count = 0
        self._loading = False
        self._load_more_btn = None
        self._filters_dialog = None
        self._setup_ui()

    def _setup_ui(self):
        layout = MDBoxLayout(orientation='vertical')

        # Toolbar
        toolbar = MDTopAppBar(title="Completed Addresses", size_hint_y=None, height=dp(56))
        toolbar.left_action_items = [["arrow-left", lambda x: self.go_back()]]
        toolbar.right_action_items = [
            ["delete", lambda x: self.clear_completed_dialog()],
            ["download", lambda x: self.export_completed()],
            ["calendar-today", lambda x: self.show_day_summary()],
        ]
        layout.add_widget(toolbar)

        # Controls row: Filters button + Search box
        controls = MDBoxLayout(
            orientation='horizontal',
            padding=[dp(12), dp(8), dp(12), dp(8)],
            spacing=dp(8),
            size_hint_y=None,
            height=dp(56),
        )

        self.filter_btn = MDRaisedButton(text="Filters", size_hint=(None, None), height=dp(40))
        self.filter_btn.bind(on_release=lambda x: self._open_filters_dialog())
        controls.add_widget(self.filter_btn)

        self.search_field = MDTextField(
            hint_text="Search in address...",
            mode="rectangle",
            size_hint=(1, None),
            height=dp(40),
        )
        self.search_field.bind(text=self._on_search_text)
        controls.add_widget(self.search_field)

        layout.add_widget(controls)

        # Summary line for current filters
        summary = MDBoxLayout(orientation='horizontal', padding=[dp(12), 0, dp(12), dp(4)],
                              size_hint_y=None, height=dp(22))
        self.filter_summary_label = MDLabel(text="", theme_text_color="Secondary", font_size='12sp')
        summary.add_widget(self.filter_summary_label)
        layout.add_widget(summary)
        self._update_filter_summary()

        # Content
        self.scroll = MDScrollView()
        self.content_layout = MDBoxLayout(orientation='vertical', adaptive_height=True, spacing=dp(8), padding=dp(12))
        self.scroll.add_widget(self.content_layout)
        layout.add_widget(self.scroll)
        self.add_widget(layout)

        # Load more button
        self._load_more_btn = MDRaisedButton(text="Load more", size_hint=(None, None), size=(dp(120), dp(36)))
        self._load_more_btn.bind(on_release=lambda x: self._load_page(reset=False))

    def _update_filter_summary(self):
        # Human-friendly summary
        range_txt = {
            'today': 'Today',
            'week': 'This Week',
            'month': 'This Month',
            'all': 'All',
            'custom': f"{self.date_from.strftime('%d/%m')} to {self.date_to.strftime('%d/%m')}"
        }.get(self.quick_range, 'Today')
        outcome_txt = self.outcome_filter if self.outcome_filter else "All"
        self.filter_summary_label.text = f"Range: {range_txt} | Outcome: {outcome_txt}"

    # --- Filters dialog ---
    def _open_filters_dialog(self):
        # Build content dynamically each time to reflect current selection
        content = MDBoxLayout(orientation='vertical', spacing=dp(12), adaptive_height=True)

        # Quick range row
        rrow = MDBoxLayout(orientation='horizontal', spacing=dp(6), size_hint_y=None, height=dp(36))
        def add_rbtn(key, text):
            btn = MDFlatButton(text=text)
            if key == self.quick_range:
                try:
                    btn.text_color = (0.1, 0.3, 0.6, 1)
                except Exception:
                    pass
            btn.bind(on_release=lambda *_: self._select_range_from_dialog(key))
            rrow.add_widget(btn)
        for k, t in [("today","Today"), ("week","This Week"), ("month","This Month"), ("all","All"), ("custom","Custom")]:
            add_rbtn(k, t)
        content.add_widget(MDLabel(text="Range", theme_text_color="Primary"))
        content.add_widget(rrow)

        # Outcome row
        orow = MDBoxLayout(orientation='horizontal', spacing=dp(6), size_hint_y=None, height=dp(36))
        def add_obtn(val, text):
            btn = MDFlatButton(text=text)
            if ((val is None and self.outcome_filter is None) or (val == self.outcome_filter)):
                try:
                    btn.text_color = (0.1, 0.3, 0.6, 1)
                except Exception:
                    pass
            btn.bind(on_release=lambda *_: self._select_outcome_from_dialog(val))
            orow.add_widget(btn)
        add_obtn(None, "All")
        for v in ["PIF","DA","Done"]:
            add_obtn(v, v)
        content.add_widget(MDLabel(text="Outcome", theme_text_color="Primary"))
        content.add_widget(orow)

        if self._filters_dialog:
            self._filters_dialog.dismiss()
            self._filters_dialog = None

        self._filters_dialog = MDDialog(title="Filters", type="custom", content_cls=content,
                                        buttons=[MDFlatButton(text="Close", on_release=lambda *_: self._filters_dialog.dismiss())])
        self._filters_dialog.open()

    def _select_range_from_dialog(self, key):
        if self._filters_dialog:
            self._filters_dialog.dismiss()
        self._select_quick_range(key)

    def _select_outcome_from_dialog(self, outcome):
        if self._filters_dialog:
            self._filters_dialog.dismiss()
        self._select_outcome(outcome)

    def go_back(self):
        self.manager.current = "main_screen"

    # ---------- Filters behavior ----------
    def _select_quick_range(self, key):
        self.quick_range = key
        if key == 'today':
            self.date_from, self.date_to = start_of_today(), end_of_today()
        elif key == 'week':
            self.date_from, self.date_to = start_of_week(), end_of_week()
        elif key == 'month':
            self.date_from, self.date_to = start_of_month(), end_of_month()
        elif key == 'all':
            self.date_from, self.date_to = None, None
        elif key == 'custom':
            self._open_custom_range_picker()
            return
        self._update_filter_summary()
        self.reset_and_load()

    def _open_custom_range_picker(self):
        try:
            from kivymd.uix.picker import MDDatePicker
        except Exception:
            toast("Date picker not available")
            return

        # Pick start, then end
        def on_start_save(instance, value, date_range):
            self._custom_start = datetime(value.year, value.month, value.day, 0, 0, 0)
            instance.dismiss()
            end_picker = MDDatePicker()
            end_picker.title = "Select end date"
            end_picker.bind(on_save=on_end_save, on_cancel=lambda *a: None)
            end_picker.open()

        def on_end_save(instance, value, date_range):
            self._custom_end = datetime(value.year, value.month, value.day, 23, 59, 59)
            instance.dismiss()
            self.date_from, self.date_to = self._custom_start, self._custom_end
            self.quick_range = 'custom'
            self._update_filter_summary()
            self.reset_and_load()

        start_picker = MDDatePicker()
        start_picker.title = "Select start date"
        start_picker.bind(on_save=on_start_save, on_cancel=lambda *a: None)
        start_picker.open()

    def _select_outcome(self, outcome):
        self.outcome_filter = outcome
        self._update_filter_summary()
        self.reset_and_load()

    def _on_search_text(self, instance, text):
        if hasattr(self, '_search_ev') and self._search_ev:
            self._search_ev.cancel()
        self._search_ev = Clock.schedule_once(lambda dt: self._apply_search(text), 0.35)

    def _apply_search(self, text):
        self.search_query = text.strip()
        self.reset_and_load()

    # ---------- Data loading ----------
    def reset_and_load(self):
        if self._loading:
            return
        self.offset = 0
        self.content_layout.clear_widgets()
        self._load_page(reset=True)

    def _load_page(self, reset=False):
        if self._loading:
            return
        self._loading = True
        def work():
            try:
                total = self.app.db.count(self.date_from, self.date_to, self.outcome_filter, self.search_query)
                items = self.app.db.query(self.date_from, self.date_to, self.outcome_filter, self.search_query,
                                          limit=self.limit, offset=self.offset)
                Clock.schedule_once(lambda dt, T=total, I=items: self._apply_page(T, I), 0)
            except Exception as e:
                Clock.schedule_once(lambda dt: toast(f"Load failed: {e}"), 0)
                self._loading = False
        threading.Thread(target=work, daemon=True).start()

    def _apply_page(self, total, items):
        self.total_count = total
        # Summary at top when reset and first page
        if self.offset == 0:
            self._add_summary_card(total)
        # Add cards
        for item in items:
            card = self._create_completed_card(item)
            self.content_layout.add_widget(card)
        self.offset += len(items)
        # Handle Load more button
        if self.offset < self.total_count:
            if self._load_more_btn.parent is None:
                self.content_layout.add_widget(self._load_more_btn)
        else:
            if self._load_more_btn.parent is not None:
                self.content_layout.remove_widget(self._load_more_btn)
        self._loading = False

    def _add_summary_card(self, total):
        summary_card = MDCard(size_hint_y=None, height=dp(64), elevation=2, padding=dp(12))
        row = MDBoxLayout(orientation='horizontal')
        row.add_widget(MDLabel(text=f"Matches: {total}", font_style="H6"))
        export_btn = MDFlatButton(text="Export", size_hint_x=None, width=dp(80), on_release=lambda x: self.export_completed())
        row.add_widget(export_btn)
        summary_card.add_widget(row)
        self.content_layout.add_widget(summary_card)

    def _create_completed_card(self, item):
        card = MDCard(size_hint_y=None, height=dp(90), elevation=1, padding=dp(12))
        layout = MDBoxLayout(orientation='vertical', spacing=dp(6))
        top_row = MDBoxLayout(orientation='horizontal')
        address_label = MDLabel(text=f"{item['index'] + 1}. {item['address']}", size_hint_x=0.7, shorten=True)
        outcome_label = MDLabel(text=item['completion']['outcome'], size_hint_x=0.3, halign="right", theme_text_color="Custom", text_color=self._get_outcome_color(item['completion']['outcome']))
        top_row.add_widget(address_label)
        top_row.add_widget(outcome_label)
        timestamp = item['completion'].get('timestamp', '')
        time_text = self._format_timestamp(timestamp)
        time_label = MDLabel(text=time_text, theme_text_color="Secondary", font_size='11sp')
        button_row = MDBoxLayout(orientation='horizontal', size_hint_y=None, height=dp(28))
        nav_btn = MDFlatButton(text="Navigate", size_hint_x=None, width=dp(80), font_size='11sp', on_release=lambda x, a=item['address']: self.navigate_to_address(a))
        remove_btn = MDFlatButton(text="Remove", size_hint_x=None, width=dp(70), theme_text_color="Error", font_size='11sp', on_release=lambda x, idx=item['index']: self.remove_completed(idx))
        button_row.add_widget(nav_btn)
        button_row.add_widget(MDLabel())
        button_row.add_widget(remove_btn)
        layout.add_widget(top_row)
        layout.add_widget(time_label)
        layout.add_widget(button_row)
        card.add_widget(layout)
        return card

    def _get_outcome_color(self, outcome):
        colors = {"PIF": [0, 0.7, 0, 1], "DA": [0.8, 0.1, 0.1, 1], "Done": [0, 0.5, 0.8, 1]}
        return colors.get(outcome, [0.5, 0.5, 0.5, 1])

    def _format_timestamp(self, timestamp):
        try:
            dt = datetime.fromisoformat(timestamp)
            return dt.strftime("%d/%m %H:%M")
        except:
            return "Unknown"

    def navigate_to_address(self, address):
        main_screen = self.app.get_main_screen()
        if main_screen:
            main_screen.navigate_to_address(address, -1, from_completed=True)

    def remove_completed(self, index):
        main_screen = self.app.get_main_screen()
        if main_screen:
            main_screen.remove_from_completed(index)
        try:
            self.app.db.delete_latest_by_idx(index)
        except Exception as e:
            print(f"DB delete error: {e}")
        self.reset_and_load()

    def show_day_summary(self):
        main_screen = self.app.get_main_screen()
        if not main_screen or not main_screen.day_history:
            toast("No day history available")
            return
        total_days = len(main_screen.day_history)
        total_sessions = sum(len(sessions) if isinstance(sessions, list) else 1 for sessions in main_screen.day_history.values())
        if main_screen.current_day_data:
            current_completed = len(main_screen.current_day_data['addresses_completed'])
            toast(f"History: {total_days} days, {total_sessions} sessions â€¢ Today: {current_completed} completed")
        else:
            toast(f"History: {total_days} days, {total_sessions} sessions")

    def clear_completed_dialog(self):
        if not hasattr(self, '_clear_dialog'):
            self._clear_dialog = MDDialog(title="Clear All Completed?", text="This cannot be undone.", buttons=[
                MDFlatButton(text="Cancel", on_release=lambda x: self._clear_dialog.dismiss()),
                MDFlatButton(text="Clear All", theme_text_color="Error", on_release=lambda x: self._clear_all()),
            ])
        self._clear_dialog.open()

    def _clear_all(self):
        main_screen = self.app.get_main_screen()
        if main_screen:
            main_screen.clear_all_completed()
        try:
            self.app.db.clear_all()
        except Exception as e:
            print(f"DB clear error: {e}")
        self.reset_and_load()
        self._clear_dialog.dismiss()

    def export_completed(self):
        threading.Thread(target=self._export_background, daemon=True).start()

    def _export_background(self):
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"completed_addresses_{timestamp}.csv"
            filepath = self._get_export_path(filename)
            # Export all matches under current filters
            offset = 0
            batch = 500
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['Index', 'Address', 'Outcome', 'Amount', 'Date', 'Time'])
                total = self.app.db.count(self.date_from, self.date_to, self.outcome_filter, self.search_query)
                while offset < total:
                    items = self.app.db.query(self.date_from, self.date_to, self.outcome_filter, self.search_query, limit=batch, offset=offset)
                    for item in items:
                        comp = item['completion']
                        try:
                            dt = datetime.fromisoformat(comp.get('timestamp', ''))
                            date_str = dt.strftime("%Y-%m-%d")
                            time_str = dt.strftime("%H:%M:%S")
                        except:
                            date_str = time_str = "Unknown"
                        writer.writerow([item['index'] + 1, item['address'], comp.get('outcome', 'Done'), comp.get('amount', ''), date_str, time_str])
                    offset += len(items)
            Clock.schedule_once(lambda dt: toast(f"Exported to {filename}"), 0)
        except Exception as e:
            Clock.schedule_once(lambda dt: toast(f"Export failed: {str(e)}"), 0)

    def _get_export_path(self, filename):
        if platform == 'android' and ANDROID_AVAILABLE:
            try:
                app_path = PythonActivity.mActivity.getFilesDir().getAbsolutePath()
                return os.path.join(app_path, filename)
            except:
                return filename
        return os.path.join(os.path.expanduser("~"), filename)


class AddressNavigatorApp(MDApp):
    def build(self):
        try:
            self.title = "Address Navigator"
            self.theme_cls.theme_style = "Light"
            self.theme_cls.primary_palette = "Blue"
            # DB path
            self.db = CompletionDB(self._get_db_path())
            # Create screen manager
            self.screen_manager = MDScreenManager()
            # Create main screen
            self.main_screen = MainScreen(name="main_screen")
            self.screen_manager.add_widget(self.main_screen)
            # Create completed screen immediately (avoid race)
            self._create_completed_screen(0)
            # Migrate any existing JSON completions (once) into DB
            Clock.schedule_once(self._maybe_migrate_completions, 0.5)
            return self.screen_manager
        except Exception as e:
            print(f"Build error: {e}")
            error_screen = MDScreen()
            error_layout = MDBoxLayout(orientation='vertical', padding=dp(20))
            error_layout.add_widget(MDLabel(text=f"Application Error: {str(e)}", theme_text_color="Error", halign="center"))
            error_screen.add_widget(error_layout)
            return error_screen

    def _create_completed_screen(self, dt):
        try:
            if not any(screen.name == "completed_screen" for screen in self.screen_manager.screens):
                completed_screen = CompletedScreen(self, name="completed_screen")
                self.screen_manager.add_widget(completed_screen)
        except Exception as e:
            print("Error creating completed screen:", e)
            traceback.print_exc()

    def _maybe_migrate_completions(self, dt):
        """One-way migrate in-memory JSON completions into SQLite if DB empty."""
        try:
            ms = self.get_main_screen()
            if self.db.count() == 0 and ms and ms.completed_data:
                for idx, comp in ms.completed_data.items():
                    addr = ms.addresses[idx] if idx < len(ms.addresses) else ""
                    ts = comp.get('timestamp', datetime.now().isoformat())
                    outcome = comp.get('outcome', 'Done')
                    amt = comp.get('amount', None)
                    try:
                        amt = float(amt) if amt not in (None, "") else None
                    except:
                        amt = None
                    self.db.insert_completion(idx, addr, outcome, amt, ts)
                print("Migration: completed_data -> SQLite inserted")
        except Exception as e:
            print(f"Migration error: {e}")

    def _get_db_path(self):
        fname = "address_navigator.db"
        if platform == 'android' and ANDROID_AVAILABLE:
            try:
                app_path = PythonActivity.mActivity.getFilesDir().getAbsolutePath()
                return os.path.join(app_path, fname)
            except:
                return fname
        return os.path.join(os.path.expanduser("~"), fname)

    def get_main_screen(self):
        return self.main_screen

    def on_start(self):
        try:
            pass
        except Exception as e:
            print(f"Startup error: {e}")


if __name__ == "__main__":
    AddressNavigatorApp().run()