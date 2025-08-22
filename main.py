from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.screenmanager import MDScreenManager
from kivymd.uix.button import MDRaisedButton, MDIconButton, MDFlatButton
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.toolbar import MDTopAppBar
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.dialog import MDDialog
from kivymd.uix.textfield import MDTextField
from kivymd.uix.filemanager import MDFileManager
from kivymd.uix.responsivelayout import MDResponsiveLayout
from kivymd.toast import toast
from kivymd.uix.progressbar import MDProgressBar
from kivy.metrics import dp
from kivy.clock import Clock, mainthread
from kivy.utils import platform
from kivy.animation import Animation
import csv
import webbrowser
import os
import json
from urllib.parse import quote_plus
from datetime import datetime
import threading
from collections import deque
import gc
from functools import lru_cache
import weakref

# Try to import openpyxl, fallback if not available
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
        from jnius import autoclass, cast
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

class HighPerformanceAddressCard(MDCard):
    """Ultra-optimized reusable address card widget with minimal overhead"""
    __slots__ = ('original_index', 'address', 'is_active', 'is_completed', 'card_layout',
                 'top_row', 'address_label', 'status_label', 'button_row', 'nav_button',
                 'edit_button', 'action_button', 'cancel_button', 'spacer',
                 '_cached_height', '_last_state')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Pre-configure card properties
        self.size_hint_y = None
        self._cached_height = dp(90)
        self.height = self._cached_height
        self.elevation = 2
        self.padding = dp(10)
        self.spacing = dp(6)
        self.radius = [6]

        # State tracking
        self.original_index = None
        self.address = ""
        self.is_active = False
        self.is_completed = False
        self._last_state = None

        # Create layout once
        self._setup_optimized_layout()

    def _setup_optimized_layout(self):
        """Pre-create optimized layout structure"""
        self.card_layout = MDBoxLayout(
            orientation='vertical',
            spacing=dp(6),
            adaptive_height=True
        )

        # Top row - address and status
        self.top_row = MDBoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=dp(28),
            spacing=dp(6)
        )

        self.address_label = MDLabel(
            theme_text_color="Primary",
            size_hint_x=0.7,
            halign="left",
            valign="center",
            shorten=True,
            shorten_from='right',
            font_size='14sp'
        )

        self.status_label = MDLabel(
            font_style="Caption",
            size_hint_x=0.3,
            halign="right",
            valign="center",
            font_size='12sp'
        )

        # Button row
        self.button_row = MDBoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=dp(32),
            spacing=dp(6)
        )

        # Pre-create buttons with minimal sizes
        self.nav_button = MDRaisedButton(
            text="Navigate",
            size_hint=(None, None),
            size=(dp(85), dp(28)),
            font_size='12sp'
        )

        self.edit_button = MDFlatButton(
            text="Edit",
            size_hint=(None, None),
            size=(dp(60), dp(28)),
            font_size='12sp'
        )

        self.action_button = MDFlatButton(
            size_hint=(None, None),
            size=(dp(75), dp(28)),
            font_size='12sp'
        )

        self.cancel_button = MDFlatButton(
            text="Cancel",
            size_hint=(None, None),
            size=(dp(65), dp(28)),
            theme_text_color="Error",
            font_size='12sp'
        )

        self.spacer = MDLabel(size_hint_x=1)

        # Build layout
        self.top_row.add_widget(self.address_label)
        self.top_row.add_widget(self.status_label)
        self.card_layout.add_widget(self.top_row)
        self.card_layout.add_widget(self.button_row)
        self.add_widget(self.card_layout)

    def fast_update(self, original_index, address, is_active, is_completed,
                   completed_outcomes, completed_amounts, callback_nav,
                   callback_action, callback_cancel, callback_edit):
        """Ultra-fast update with state caching"""
        current_state = (original_index, is_active, is_completed, 
                        completed_outcomes.get(original_index), 
                        completed_amounts.get(original_index))

        # Skip update if state hasn't changed
        if self._last_state == current_state and self.address == address:
            return

        self._last_state = current_state
        self.original_index = original_index
        self.address = address
        self.is_active = is_active
        self.is_completed = is_completed

        # Update address text with numbering
        display_text = f"{original_index + 1}. {address}"
        if is_active and not is_completed:
            self.address_label.text = f"► {display_text}"
            self.address_label.font_style = "Body1"
        elif is_completed:
            self.address_label.text = display_text
            self.address_label.font_style = "Body2"
        else:
            self.address_label.text = display_text
            self.address_label.font_style = "Body2"

        # Fast color and status update
        self._fast_update_appearance(completed_outcomes, completed_amounts)

        # Update buttons efficiently
        self._fast_update_buttons(callback_nav, callback_action, callback_cancel, callback_edit)

    def _fast_update_appearance(self, completed_outcomes, completed_amounts):
        """Ultra-fast appearance update"""
        if self.is_active and not self.is_completed:
            self.md_bg_color = (0.9, 0.95, 1.0, 1.0)
            self.elevation = 3
            self.status_label.text = "ACTIVE"
            self.status_label.theme_text_color = "Custom"
            self.status_label.text_color = [0, 0.5, 0.8, 1]
        elif self.is_completed:
            outcome = completed_outcomes.get(self.original_index, "Done")
            amount = completed_amounts.get(self.original_index, "")

            # Minimal color logic
            if outcome == "PIF":
                self.md_bg_color = (0.92, 1.0, 0.92, 1.0)
                status_text = f"PIF £{amount}" if amount else "PIF"
                self.status_label.text_color = [0, 0.7, 0, 1]
            elif outcome == "DA":
                self.md_bg_color = (1.0, 0.96, 0.96, 1.0)
                status_text = "DA"
                self.status_label.text_color = [0.8, 0.1, 0.1, 1]
            else:
                self.md_bg_color = (0.96, 0.96, 0.96, 1.0)
                status_text = "Done"
                self.status_label.text_color = [0, 0.5, 0.8, 1]

            self.elevation = 1
            self.status_label.text = status_text
            self.status_label.theme_text_color = "Custom"
        else:
            self.md_bg_color = (1, 1, 1, 1)
            self.elevation = 2
            self.status_label.text = "PENDING"
            self.status_label.theme_text_color = "Secondary"

    def _fast_update_buttons(self, callback_nav, callback_action, callback_cancel, callback_edit):
        """Ultra-fast button update"""
        # Clear and rebuild button row efficiently
        self.button_row.clear_widgets()

        # Update nav and edit buttons (always present)
        self.nav_button.unbind()
        self.nav_button.bind(on_release=lambda x: callback_nav(self.address, self.original_index))

        self.edit_button.unbind()
        self.edit_button.bind(on_release=lambda x: callback_edit(self.original_index))

        self.button_row.add_widget(self.nav_button)
        self.button_row.add_widget(self.edit_button)

        if self.is_completed:
            self.action_button.text = "Undo"
            self.action_button.theme_text_color = "Primary"
            self.action_button.unbind()
            self.action_button.bind(on_release=lambda x: callback_action(self.original_index, "undo"))

            self.button_row.add_widget(self.spacer)
            self.button_row.add_widget(self.action_button)

        elif self.is_active:
            self.action_button.text = "Complete"
            self.action_button.theme_text_color = "Custom"
            self.action_button.text_color = [0, 0.7, 0, 1]
            self.action_button.unbind()
            self.action_button.bind(on_release=lambda x: callback_action(self.original_index, "complete"))

            self.cancel_button.unbind()
            self.cancel_button.bind(on_release=lambda x: callback_cancel())

            self.button_row.add_widget(self.action_button)
            self.button_row.add_widget(self.cancel_button)

        else:
            self.action_button.text = "Set Active"
            self.action_button.theme_text_color = "Primary"
            self.action_button.unbind()
            self.action_button.bind(on_release=lambda x: callback_action(self.original_index, "set_active"))

            self.button_row.add_widget(self.spacer)
            self.button_row.add_widget(self.action_button)

class UltraFastLazyLoader:
    """Ultra-optimized lazy loading with batching and caching"""
    def __init__(self, batch_size=15):
        self.widget_queue = deque()
        self.loading_active = False
        self.batch_size = batch_size
        self._loading_event = None

    def queue_widgets(self, widget_data_list):
        """Queue multiple widgets at once"""
        self.widget_queue.extend(widget_data_list)
        if not self.loading_active:
            self._start_loading()

    def _start_loading(self):
        """Start optimized loading process"""
        self.loading_active = True
        self._process_batch()

    def _process_batch(self, dt=0):
        """Process batch of widgets without animations for speed"""
        batch_count = 0
        while self.widget_queue and batch_count < self.batch_size:
            widget_data = self.widget_queue.popleft()
            widget = widget_data['widget']
            parent = widget_data['parent']
            parent.add_widget(widget)
            batch_count += 1

        if self.widget_queue:
            # Schedule next batch with minimal delay
            self._loading_event = Clock.schedule_once(self._process_batch, 1/60)
        else:
            self.loading_active = False

    def clear_queue(self):
        """Clear loading queue"""
        self.widget_queue.clear()
        if self._loading_event:
            self._loading_event.cancel()
        self.loading_active = False

class PersistentSearchField(MDTextField):
    """Always-visible search field with live filtering"""
    def __init__(self, screen_instance, **kwargs):
        super().__init__(**kwargs)
        self.screen_instance = screen_instance
        self._search_event = None
        self.hint_text = "Type to search addresses..."
        self.size_hint_y = None
        self.height = dp(48)
        self.font_size = '16sp'
        self.mode = "rectangle"
        
        # Bind to text changes
        self.bind(text=self._on_search_text)
        
    def _on_search_text(self, instance, text):
        """Handle real-time search text changes"""
        # Cancel previous search event
        if self._search_event:
            self._search_event.cancel()
        
        # Use shorter delay and optimized search
        self._search_event = Clock.schedule_once(
            lambda dt: self._perform_optimized_search(text), 0.1
        )

    def _perform_optimized_search(self, text):
        """Perform optimized search without full UI rebuild"""
        self.screen_instance.search_query = text.strip()
        # Use the new optimized filter method instead of full rebuild
        self.screen_instance.filter_existing_cards()

class OptimizedCompletedScreen(MDScreen):
    """Streamlined completed addresses screen"""
    def __init__(self, app_instance, **kwargs):
        super().__init__(**kwargs)
        self.app_instance = app_instance
        self.lazy_loader = UltraFastLazyLoader(batch_size=20)
        self._setup_ui()

    def _setup_ui(self):
        main_layout = MDBoxLayout(orientation='vertical')

        # Compact toolbar
        toolbar = MDTopAppBar(
            title="Completed",
            elevation=2,
            size_hint_y=None,
            height=dp(52)
        )
        toolbar.left_action_items = [["arrow-left", lambda x: self.go_back()]]
        toolbar.right_action_items = [
            ["delete", lambda x: self.clear_completed_dialog()],
            ["download", lambda x: self.export_completed()]
        ]

        main_layout.add_widget(toolbar)

        self.scroll_view = MDScrollView()
        self.completed_layout = MDBoxLayout(
            orientation='vertical',
            adaptive_height=True,
            spacing=dp(8),
            padding=[dp(12), dp(12)]
        )
        self.scroll_view.add_widget(self.completed_layout)

        main_layout.add_widget(self.scroll_view)
        self.add_widget(main_layout)

    def go_back(self):
        self.manager.current = "address_screen"

    def populate_completed_addresses(self):
        """Ultra-fast population"""
        self.lazy_loader.clear_queue()
        self.completed_layout.clear_widgets()

        address_screen = self.app_instance.get_address_screen()
        if not address_screen:
            return

        completed_data = address_screen.get_completed_addresses_with_timestamps()
        if not completed_data:
            self._show_no_data()
            return

        # Sort by timestamp (newest first)
        completed_data.sort(key=lambda x: x['timestamp'], reverse=True)

        # Create summary
        self._create_summary(len(completed_data))

        # Queue cards for lazy loading
        widget_data_list = []
        for item in completed_data:
            card = self._create_completed_card(item)
            widget_data_list.append({
                'widget': card,
                'parent': self.completed_layout
            })

        self.lazy_loader.queue_widgets(widget_data_list)

    def _show_no_data(self):
        card = MDCard(
            size_hint_y=None,
            height=dp(120),
            elevation=2,
            padding=dp(16),
            radius=[8]
        )

        layout = MDBoxLayout(orientation='vertical', spacing=dp(12))
        title = MDLabel(
            text="No Completed Addresses",
            theme_text_color="Primary",
            font_style="H6",
            halign="center",
            size_hint_y=None,
            height=dp(32)
        )
        subtitle = MDLabel(
            text="Complete addresses to see them here",
            theme_text_color="Secondary",
            halign="center",
            size_hint_y=None,
            height=dp(24)
        )

        layout.add_widget(title)
        layout.add_widget(subtitle)
        card.add_widget(layout)
        self.completed_layout.add_widget(card)

    def _create_summary(self, count):
        summary_card = MDCard(
            size_hint_y=None,
            height=dp(60),
            elevation=2,
            padding=dp(12),
            radius=[8]
        )

        layout = MDBoxLayout(orientation='horizontal')
        label = MDLabel(
            text=f"Total: {count}",
            theme_text_color="Primary",
            font_style="H6"
        )
        export_btn = MDRaisedButton(
            text="Export",
            size_hint_x=None,
            width=dp(80),
            on_release=lambda x: self.export_completed()
        )

        layout.add_widget(label)
        layout.add_widget(export_btn)
        summary_card.add_widget(layout)
        self.completed_layout.add_widget(summary_card)

    def _create_completed_card(self, item):
        """Create minimal completed address card"""
        card = MDCard(
            size_hint_y=None,
            height=dp(90),
            elevation=1,
            padding=dp(12),
            radius=[6]
        )

        layout = MDBoxLayout(orientation='vertical', spacing=dp(6))

        # Top row
        top_row = MDBoxLayout(orientation='horizontal', size_hint_y=None, height=dp(24))
        address_label = MDLabel(
            text=f"{item['index'] + 1}. {item['address']}",
            theme_text_color="Primary",
            size_hint_x=0.65,
            shorten=True,
            font_size='13sp'
        )
        outcome_label = MDLabel(
            text=item['outcome'],
            theme_text_color="Custom",
            text_color=self._get_outcome_color(item['outcome']),
            size_hint_x=0.35,
            halign="right",
            font_size='12sp'
        )

        top_row.add_widget(address_label)
        top_row.add_widget(outcome_label)
        layout.add_widget(top_row)

        # Time row
        time_row = MDBoxLayout(orientation='horizontal', size_hint_y=None, height=dp(20))
        time_label = MDLabel(
            text=self._format_timestamp(item['timestamp']),
            theme_text_color="Secondary",
            font_size='11sp'
        )
        time_row.add_widget(time_label)
        layout.add_widget(time_row)

        # Button row
        btn_row = MDBoxLayout(orientation='horizontal', size_hint_y=None, height=dp(28))
        nav_btn = MDFlatButton(
            text="Navigate",
            size_hint_x=None,
            width=dp(80),
            font_size='11sp',
            on_release=lambda x: self.navigate_to_address(item['address'])
        )
        remove_btn = MDFlatButton(
            text="Remove",
            size_hint_x=None,
            width=dp(70),
            theme_text_color="Error",
            font_size='11sp',
            on_release=lambda x: self.remove_address(item['index'])
        )

        btn_row.add_widget(nav_btn)
        btn_row.add_widget(MDLabel())  # spacer
        btn_row.add_widget(remove_btn)
        layout.add_widget(btn_row)

        card.add_widget(layout)
        return card

    def _get_outcome_color(self, outcome):
        colors = {
            "PIF": [0, 0.7, 0, 1],
            "DA": [0.8, 0.1, 0.1, 1],
            "Done": [0, 0.5, 0.8, 1]
        }
        return colors.get(outcome, [0.5, 0.5, 0.5, 1])

    def _format_timestamp(self, timestamp):
        try:
            dt = datetime.fromisoformat(timestamp)
            return dt.strftime("%m/%d %I:%M %p")
        except:
            return "Unknown"

    def navigate_to_address(self, address):
        address_screen = self.app_instance.get_address_screen()
        if address_screen:
            address_screen.navigate_to_address(address, -1, from_completed=True)

    def remove_address(self, index):
        address_screen = self.app_instance.get_address_screen()
        if address_screen:
            address_screen.remove_from_completed(index)
            self.populate_completed_addresses()

    def clear_completed_dialog(self):
        if not hasattr(self, 'clear_dialog'):
            self.clear_dialog = MDDialog(
                title="Clear All Completed?",
                text="This cannot be undone.",
                buttons=[
                    MDFlatButton(text="Cancel", on_release=lambda x: self.clear_dialog.dismiss()),
                    MDFlatButton(text="Clear", theme_text_color="Error", on_release=lambda x: self.clear_all()),
                ],
            )
        self.clear_dialog.open()

    def clear_all(self):
        address_screen = self.app_instance.get_address_screen()
        if address_screen:
            address_screen.clear_all_completed()
            self.populate_completed_addresses()
        self.clear_dialog.dismiss()

    def export_completed(self):
        threading.Thread(target=self._export_background, daemon=True).start()

    def _export_background(self):
        try:
            address_screen = self.app_instance.get_address_screen()
            if not address_screen:
                return

            completed_data = address_screen.get_completed_addresses_with_timestamps()
            if not completed_data:
                return

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"completed_{timestamp}.csv"
            filepath = self._get_export_path(filename)

            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=['address', 'outcome', 'amount', 'date', 'time'])
                writer.writeheader()
                
                for item in completed_data:
                    try:
                        dt = datetime.fromisoformat(item['timestamp'])
                        date_str = dt.strftime("%Y-%m-%d")
                        time_str = dt.strftime("%H:%M:%S")
                    except:
                        date_str = time_str = "Unknown"

                    writer.writerow({
                        'address': item['address'],
                        'outcome': item['outcome'],
                        'amount': item.get('amount', ''),
                        'date': date_str,
                        'time': time_str
                    })

        except Exception as e:
            print(f"Export error: {e}")

    def _get_export_path(self, filename):
        if platform == 'android' and ANDROID_AVAILABLE:
            try:
                app_path = PythonActivity.mActivity.getFilesDir().getAbsolutePath()
                return os.path.join(app_path, filename)
            except:
                return filename
        return os.path.join(os.path.expanduser("~"), filename)

class UltraFastAddressScreen(MDScreen):
    """Ultra-optimized main address screen"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Core data structures
        self.addresses = []
        self.completed_addresses = set()
        self.completed_timestamps = {}
        self.completed_outcomes = {}
        self.completed_amounts = {}
        self.active_address_index = None

        # Optimizations
        self.lazy_loader = UltraFastLazyLoader(batch_size=25)
        self._widget_pool = deque(maxlen=50)
        self._card_refs = {}
        self._cached_sorted_addresses = None
        self._addresses_dirty = True

        # File handling
        self.completion_file = "completed_addresses.json"
        self.addresses_file = "addresses.json"
        self.file_manager = None

        # Pre-created dialogs
        self.completion_dialog = None
        self.payment_dialog = None
        self.payment_field = None
        self.edit_dialog = None
        self.edit_field = None
        self.search_query = ""

        # Android storage
        self.ss = None
        self.chooser = None
        if platform == 'android' and ASK_AVAILABLE:
            try:
                self.ss = SharedStorage()
                self.chooser = Chooser(self._on_file_chosen)
            except:
                pass

        # Initialize
        if platform == 'android' and ANDROID_AVAILABLE:
            Clock.schedule_once(self.request_permissions, 0.5)
        
        self.load_completion_data()
        self.load_address_list()
        self._setup_ui()
        if self.addresses:
            self.update_ui_fast()
        else:
            self._show_welcome()

    def _setup_ui(self):
        main_layout = MDBoxLayout(orientation='vertical')

        # Standard toolbar without search functionality
        self.toolbar = MDTopAppBar(
            title="Address Navigator",
            elevation=2,
            size_hint_y=None,
            height=dp(52)
        )
        self.toolbar.right_action_items = [
            ["folder-open", lambda x: self.open_file_browser()],
            ["check-all", lambda x: self.show_completed()],
            ["refresh", lambda x: self.refresh_list()]
        ]

        main_layout.add_widget(self.toolbar)

        # Progress indicator
        self.progress = MDProgressBar(
            size_hint_y=None,
            height=dp(3),
            opacity=0
        )
        main_layout.add_widget(self.progress)

        # Persistent search field - always visible
        self.search_field = PersistentSearchField(
            self,
            size_hint_y=None,
            height=dp(56)
        )
        # Add padding around search field
        search_container = MDBoxLayout(
            orientation='vertical',
            size_hint_y=None,
            height=dp(72),
            padding=[dp(12), dp(8), dp(12), dp(8)]
        )
        search_container.add_widget(self.search_field)
        main_layout.add_widget(search_container)

        # Scroll view
        self.scroll_view = MDScrollView()
        self.address_layout = MDBoxLayout(
            orientation='vertical',
            adaptive_height=True,
            spacing=dp(8),
            padding=[dp(12), dp(12)]
        )
        self.scroll_view.add_widget(self.address_layout)

        main_layout.add_widget(self.scroll_view)
        self.add_widget(main_layout)

        # Initialize file manager
        self._init_file_manager()

    def _get_card_from_pool(self):
        """Get card from pool or create new"""
        if self._widget_pool:
            return self._widget_pool.popleft()
        return HighPerformanceAddressCard()

    def _return_card_to_pool(self, card):
        """Return card to pool"""
        if len(self._widget_pool) < self._widget_pool.maxlen:
            self._card_refs.pop(card.original_index, None)
            # Reset card
            card.opacity = 1
            card.md_bg_color = (1, 1, 1, 1)
            card.elevation = 2
            self._widget_pool.append(card)

    def show_progress(self, show=True):
        """Show/hide progress indicator"""
        target = 1 if show else 0
        Animation(opacity=target, duration=0.2).start(self.progress)

    @lru_cache(maxsize=1)
    def get_sorted_addresses_cached(self, addresses_hash):
        """Cached address order preserving original sequence"""
        if not self.addresses:
            return []
        return list(enumerate(self.addresses))

    def get_sorted_addresses(self):
        """Get addresses while preserving original order"""
        addresses_hash = hash(tuple(self.addresses)) if self.addresses else 0
        return self.get_sorted_addresses_cached(addresses_hash)

    def filter_existing_cards(self):
        """Ultra-fast filtering by hiding/showing existing cards without rebuilding"""
        if not self.search_query:
            # Show all cards if no search query
            for child in self.address_layout.children:
                if isinstance(child, HighPerformanceAddressCard):
                    child.opacity = 1
                    child.size_hint_y = None
                    child.height = child._cached_height
                    child.disabled = False
            return
        
        query = self.search_query.lower()
        visible_count = 0
        
        # Hide/show cards based on search query
        for child in self.address_layout.children:
            if isinstance(child, HighPerformanceAddressCard):
                if query in child.address.lower():
                    # Show matching card
                    child.opacity = 1
                    child.size_hint_y = None
                    child.height = child._cached_height
                    child.disabled = False
                    visible_count += 1
                else:
                    # Hide non-matching card
                    child.opacity = 0
                    child.height = 0
                    child.size_hint_y = None
                    child.disabled = True
        
        # If no results, could show a "no results" message
        # This is optional - the empty space also indicates no results

    def update_ui_fast(self):
        """Ultra-fast UI update - only use for major changes like loading new data"""
        self.lazy_loader.clear_queue()

        # Remove existing widgets (including welcome card)
        self._card_refs.clear()
        for child in self.address_layout.children[:]:
            if isinstance(child, HighPerformanceAddressCard):
                self.address_layout.remove_widget(child)
                self._return_card_to_pool(child)
            else:
                self.address_layout.remove_widget(child)

        if not self.addresses:
            return

        sorted_addresses = self.get_sorted_addresses()

        # Don't filter here anymore - let filter_existing_cards handle it
        # This method is now only for major UI rebuilds
        
        # Create first batch immediately
        immediate_batch = min(20, len(sorted_addresses))
        for i in range(immediate_batch):
            original_index, address = sorted_addresses[i]
            card = self._create_address_card_fast(original_index, address)
            self.address_layout.add_widget(card)

        # Queue remaining for lazy loading
        if len(sorted_addresses) > immediate_batch:
            remaining_data = []
            for original_index, address in sorted_addresses[immediate_batch:]:
                card = self._create_address_card_fast(original_index, address)
                remaining_data.append({
                    'widget': card,
                    'parent': self.address_layout
                })
            self.lazy_loader.queue_widgets(remaining_data)
        
        # Apply search filter if there's a query
        if self.search_query:
            Clock.schedule_once(lambda dt: self.filter_existing_cards(), 0.1)

    def _create_address_card_fast(self, original_index, address):
        """Create address card with maximum speed"""
        card = self._get_card_from_pool()
        is_active = original_index == self.active_address_index
        is_completed = original_index in self.completed_addresses

        card.fast_update(
            original_index=original_index,
            address=address,
            is_active=is_active,
            is_completed=is_completed,
            completed_outcomes=self.completed_outcomes,
            completed_amounts=self.completed_amounts,
            callback_nav=self.navigate_to_address,
            callback_action=self._handle_action,
            callback_cancel=self.cancel_active_fast,
            callback_edit=self.show_edit_dialog
        )
        self._card_refs[original_index] = card
        return card

    def _handle_action(self, index, action):
        """Handle button actions efficiently"""
        if action == "set_active":
            self.set_active_fast(index)
        elif action == "complete":
            self.show_completion_dialog(index)
        elif action == "undo":
            self.undo_completion(index)

    def set_active_fast(self, index):
        """Ultra-fast active address setting"""
        if index == self.active_address_index:
            return

        previous = self.active_address_index
        self.active_address_index = index
        self.get_sorted_addresses_cached.cache_clear()

        indices = [index]
        if previous is not None:
            indices.append(previous)

        self._update_specific_cards(indices)
        threading.Thread(target=self.save_completion_data, daemon=True).start()

    def _find_card(self, index):
        return self._card_refs.get(index)

    def _update_specific_cards(self, indices):
        """Update only specific cards for performance"""
        for idx in indices:
            card = self._card_refs.get(idx)
            if card:
                is_active = idx == self.active_address_index
                is_completed = idx in self.completed_addresses

                card.fast_update(
                    idx,
                    card.address,
                    is_active,
                    is_completed,
                    self.completed_outcomes,
                    self.completed_amounts,
                    self.navigate_to_address,
                    self._handle_action,
                    self.cancel_active_fast,
                    self.show_edit_dialog
                )

    def cancel_active_fast(self):
        """OPTIMIZED: Cancel active address with instant UI feedback"""
        if self.active_address_index is None:
            return
            
        # Store the index before clearing
        cancelled_index = self.active_address_index
        self.active_address_index = None
        
        # Find and update just the cancelled card immediately
        cancelled_card = self._find_card(cancelled_index)
        if cancelled_card:
            cancelled_card.fast_update(
                cancelled_index,
                cancelled_card.address,
                False,  # No longer active
                cancelled_index in self.completed_addresses,
                self.completed_outcomes,
                self.completed_amounts,
                self.navigate_to_address,
                self._handle_action,
                self.cancel_active_fast,
                self.show_edit_dialog
            )
        
        # Clear cache and save data in background
        self.get_sorted_addresses_cached.cache_clear()
        threading.Thread(target=self.save_completion_data, daemon=True).start()

    def navigate_to_address(self, address, index, from_completed=False):
        """Navigate with optimized maps integration"""
        if not from_completed and index not in self.completed_addresses and index != self.active_address_index:
            self.set_active_fast(index)

        try:
            encoded_address = quote_plus(str(address))
            if platform == 'android' and ANDROID_AVAILABLE:
                self._open_android_maps(encoded_address)
            else:
                self._open_web_maps(encoded_address)
        except Exception as e:
            print(f"Navigation error: {e}")
            self._fallback_maps(encoded_address)

    def _open_android_maps(self, encoded_address):
        """Optimized Android maps"""
        try:
            intent = Intent()
            intent.setAction(Intent.ACTION_VIEW)
            intent.setData(Uri.parse(f"geo:0,0?q={encoded_address}"))
            PythonActivity.mActivity.startActivity(intent)
        except Exception:
            self._open_web_maps(encoded_address)

    def _open_web_maps(self, encoded_address):
        """Web maps fallback"""
        webbrowser.open(f"https://www.google.com/maps/search/{encoded_address}")

    def _fallback_maps(self, encoded_address):
        """Final fallback"""
        try:
            webbrowser.open(f"https://www.google.com/maps/search/{encoded_address}")
        except:
            pass

    def show_edit_dialog(self, index):
        """Display dialog to edit an address"""
        if index >= len(self.addresses):
            return
        if not self.edit_dialog:
            self._create_edit_dialog()
        self._current_edit_index = index
        self.edit_field.text = self.addresses[index]
        self.edit_dialog.open()

    def _create_edit_dialog(self):
        self.edit_field = MDTextField(
            hint_text="Enter address",
            multiline=True,
            size_hint_x=None,
            width=dp(350),
            font_size='14sp'
        )
        content = MDBoxLayout(orientation='vertical', spacing=dp(12), adaptive_height=True)
        content.add_widget(self.edit_field)
        self.edit_dialog = MDDialog(
            title="Edit Address",
            type="custom",
            content_cls=content,
            buttons=[
                MDFlatButton(text="Cancel", on_release=lambda x: self.edit_dialog.dismiss()),
                MDFlatButton(text="Save", theme_text_color="Primary", on_release=lambda x: self._save_address_edit()),
            ],
        )

    def _save_address_edit(self):
        new_addr = self.edit_field.text.strip()
        idx = getattr(self, '_current_edit_index', None)
        if new_addr and idx is not None and idx < len(self.addresses):
            self.addresses[idx] = new_addr
            self.edit_dialog.dismiss()
            self.get_sorted_addresses_cached.cache_clear()
            self._update_specific_cards([idx])
            self.save_address_list()
            toast("Address updated")
        else:
            toast("Address cannot be empty")

    def show_completion_dialog(self, index):
        """Show streamlined completion dialog"""
        if not self.completion_dialog:
            self._create_completion_dialog()
        
        address = self.addresses[index] if index < len(self.addresses) else "Unknown"
        self.completion_dialog.text = f"Complete: {address[:50]}..."
        self._current_completion_index = index
        self.completion_dialog.open()

    def _create_completion_dialog(self):
        """Pre-create completion dialog"""
        self.completion_dialog = MDDialog(
            title="Complete Address",
            text="",
            buttons=[
                MDFlatButton(text="Cancel", on_release=lambda x: self.completion_dialog.dismiss()),
                MDFlatButton(
                    text="Done",
                    theme_text_color="Primary",
                    on_release=lambda x: self._complete_fast("Done", "")
                ),
                MDFlatButton(
                    text="DA",
                    theme_text_color="Error",
                    on_release=lambda x: self._complete_fast("DA", "")
                ),
                MDFlatButton(
                    text="PIF",
                    theme_text_color="Custom",
                    text_color=[0, 0.7, 0, 1],
                    on_release=lambda x: self.show_payment_dialog()
                )
            ],
        )

    def _complete_fast(self, outcome, amount):
        """Ultra-fast completion"""
        self.completion_dialog.dismiss()
        index = getattr(self, '_current_completion_index', None)
        if index is None:
            return

        # Update state
        self.completed_addresses.add(index)
        self.completed_timestamps[index] = datetime.now().isoformat()
        self.completed_outcomes[index] = outcome
        if amount:
            self.completed_amounts[index] = amount

        # Clear active if this was active
        if self.active_address_index == index:
            self.active_address_index = None

        # Invalidate cache and update UI
        self.get_sorted_addresses_cached.cache_clear()
        self._update_specific_cards([index])

        # Save in background
        threading.Thread(target=self.save_completion_data, daemon=True).start()

    def show_payment_dialog(self):
        """Show payment dialog"""
        if not self.payment_dialog:
            self._create_payment_dialog()
        
        self.completion_dialog.dismiss()
        self.payment_field.text = ""
        self.payment_dialog.open()

    def _create_payment_dialog(self):
        """Pre-create payment dialog"""
        self.payment_field = MDTextField(
            hint_text="Amount (£)",
            size_hint_x=None,
            width=dp(180),
            input_filter="float",
            halign="center"
        )

        content = MDBoxLayout(
            orientation='vertical',
            spacing=dp(12),
            adaptive_height=True
        )
        content.add_widget(self.payment_field)

        self.payment_dialog = MDDialog(
            title="Payment Amount",
            type="custom",
            content_cls=content,
            buttons=[
                MDFlatButton(text="Cancel", on_release=lambda x: self.payment_dialog.dismiss()),
                MDFlatButton(
                    text="Confirm",
                    theme_text_color="Custom",
                    text_color=[0, 0.7, 0, 1],
                    on_release=lambda x: self.confirm_payment()
                ),
            ],
        )

    def confirm_payment(self):
        """Confirm payment with validation"""
        try:
            amount_text = self.payment_field.text.strip()
            if not amount_text:
                return
            
            amount = float(amount_text)
            if amount <= 0:
                return
            
            self.payment_dialog.dismiss()
            self._complete_fast("PIF", f"{amount:.2f}")
        except ValueError:
            pass

    def undo_completion(self, index):
        """Undo completion efficiently"""
        if index in self.completed_addresses:
            self.completed_addresses.remove(index)
            self.completed_timestamps.pop(index, None)
            self.completed_outcomes.pop(index, None)
            self.completed_amounts.pop(index, None)
            
            self.get_sorted_addresses_cached.cache_clear()
            self._update_specific_cards([index])
            threading.Thread(target=self.save_completion_data, daemon=True).start()

    # File handling - optimized
    def request_permissions(self, dt):
        if platform == 'android' and ANDROID_AVAILABLE:
            try:
                request_permissions([Permission.READ_EXTERNAL_STORAGE, Permission.WRITE_EXTERNAL_STORAGE])
            except:
                pass

    def _init_file_manager(self):
        try:
            self.file_manager = MDFileManager(
                exit_manager=self.exit_manager,
                select_path=self.select_path,
                preview=False
            )
        except:
            self.file_manager = None

    def open_file_browser(self):
        """Open file browser with SAF support"""
        if platform == 'android' and self.chooser:
            try:
                self.chooser.choose_content('*/*')
                return
            except:
                pass

        if not self.file_manager:
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
        except:
            pass

    def _on_file_chosen(self, shared_file_list):
        """Handle SAF file selection"""
        def process():
            try:
                if not shared_file_list or not self.ss:
                    return
                
                private_path = self.ss.copy_from_shared(shared_file_list[0])
                if not private_path or not os.path.exists(private_path):
                    return
                
                lower = private_path.lower()
                if lower.endswith('.csv'):
                    Clock.schedule_once(lambda dt: self.load_csv(private_path), 0)
                elif lower.endswith(('.xlsx', '.xls')) and OPENPYXL_AVAILABLE:
                    Clock.schedule_once(lambda dt: self.load_excel(private_path), 0)
            except:
                pass
        
        threading.Thread(target=process, daemon=True).start()

    def select_path(self, path):
        """Handle file selection"""
        self.exit_manager()
        lower = path.lower()
        if lower.endswith(('.xlsx', '.xls')) and OPENPYXL_AVAILABLE:
            self.load_excel(path)
        elif lower.endswith('.csv'):
            self.load_csv(path)

    def exit_manager(self):
        if self.file_manager:
            try:
                self.file_manager.close()
            except:
                pass

    @mainthread
    def load_excel(self, file_path):
        """Load Excel file efficiently"""
        if not OPENPYXL_AVAILABLE:
            return
        
        self.show_progress(True)
        
        def load_background():
            try:
                wb = load_workbook(file_path, read_only=True, data_only=True)
                ws = wb.active
                rows = list(ws.iter_rows(values_only=True))
                wb.close()
                
                if not rows:
                    Clock.schedule_once(lambda dt: self.show_progress(False), 0)
                    return
                
                # Find address column
                headers = [str(cell) if cell else "" for cell in rows[0]]
                addr_col = 0
                for i, header in enumerate(headers):
                    if 'address' in header.lower():
                        addr_col = i
                        break
                
                # Extract addresses
                addresses = []
                for row in rows[1:]:
                    if len(row) > addr_col and row[addr_col]:
                        addr = str(row[addr_col]).strip()
                        if addr and addr.lower() not in ['none', 'null']:
                            addresses.append(addr)
                
                Clock.schedule_once(lambda dt: self._load_addresses(addresses), 0)
            except Exception as e:
                Clock.schedule_once(lambda dt: self.show_progress(False), 0)
        
        threading.Thread(target=load_background, daemon=True).start()

    @mainthread
    def load_csv(self, file_path):
        """Load CSV file efficiently"""
        self.show_progress(True)
        
        def load_background():
            try:
                addresses = []
                encodings = ['utf-8', 'utf-8-sig', 'latin1']
                
                for encoding in encodings:
                    try:
                        with open(file_path, 'r', encoding=encoding) as f:
                            reader = csv.reader(f)
                            rows = list(reader)
                        break
                    except:
                        continue
                else:
                    Clock.schedule_once(lambda dt: self.show_progress(False), 0)
                    return
                
                if not rows:
                    Clock.schedule_once(lambda dt: self.show_progress(False), 0)
                    return
                
                # Find address column
                headers = rows[0]
                addr_col = 0
                for i, header in enumerate(headers):
                    if 'address' in header.lower():
                        addr_col = i
                        break
                
                # Extract addresses
                for row in rows[1:]:
                    if len(row) > addr_col and row[addr_col].strip():
                        addresses.append(row[addr_col].strip())
                
                Clock.schedule_once(lambda dt: self._load_addresses(addresses), 0)
            except:
                Clock.schedule_once(lambda dt: self.show_progress(False), 0)
        
        threading.Thread(target=load_background, daemon=True).start()

    def _load_addresses(self, addresses):
        """Load addresses into UI"""
        self.show_progress(False)
        self.addresses = addresses or []
        self.active_address_index = None
        self.completed_addresses.clear()
        self.completed_timestamps.clear()
        self.completed_outcomes.clear()
        self.completed_amounts.clear()
        
        # Clear search field
        self.search_query = ""
        if hasattr(self, 'search_field'):
            self.search_field.text = ""

        # Clear cache and update
        self.get_sorted_addresses_cached.cache_clear()
        self.save_completion_data()
        self.save_address_list()
        self.update_ui_fast()

    # Data persistence
    def save_address_list(self):
        """Persist current addresses list"""
        try:
            path = self._get_addresses_path()
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self.addresses, f, ensure_ascii=False)
        except Exception as e:
            print(f"Address save error: {e}")

    def load_address_list(self):
        """Load persisted addresses list"""
        try:
            path = self._get_addresses_path()
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    self.addresses = json.load(f)
        except Exception as e:
            print(f"Address load error: {e}")
            self.addresses = []

    def _get_addresses_path(self):
        if platform == 'android' and ANDROID_AVAILABLE:
            try:
                app_path = PythonActivity.mActivity.getFilesDir().getAbsolutePath()
                return os.path.join(app_path, self.addresses_file)
            except:
                return self.addresses_file
        return os.path.join(os.path.expanduser("~"), self.addresses_file)

    def save_completion_data(self):
        """Save completion data efficiently"""
        try:
            file_path = self._get_completion_path()
            data = {
                'completed_addresses': list(self.completed_addresses),
                'completed_timestamps': self.completed_timestamps,
                'completed_outcomes': self.completed_outcomes,
                'completed_amounts': self.completed_amounts,
                'active_address_index': self.active_address_index
            }
            with open(file_path, 'w') as f:
                json.dump(data, f, separators=(',', ':'))
        except:
            pass

    def load_completion_data(self):
        """Load completion data"""
        try:
            file_path = self._get_completion_path()
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    data = json.load(f)
                
                if isinstance(data, list):
                    self.completed_addresses = set(data)
                else:
                    self.completed_addresses = set(data.get('completed_addresses', []))
                    self.completed_timestamps = {int(k): v for k, v in data.get('completed_timestamps', {}).items()}
                    self.completed_outcomes = {int(k): v for k, v in data.get('completed_outcomes', {}).items()}
                    self.completed_amounts = {int(k): v for k, v in data.get('completed_amounts', {}).items()}
                    self.active_address_index = data.get('active_address_index')
        except:
            self.completed_addresses = set()
            self.completed_timestamps = {}
            self.completed_outcomes = {}
            self.completed_amounts = {}
            self.active_address_index = None

    def _get_completion_path(self):
        """Get completion file path"""
        if platform == 'android' and ANDROID_AVAILABLE:
            try:
                app_path = PythonActivity.mActivity.getFilesDir().getAbsolutePath()
                return os.path.join(app_path, self.completion_file)
            except:
                return self.completion_file
        return os.path.join(os.path.expanduser("~"), self.completion_file)

    # Helper methods
    def show_completed(self):
        """Show completed addresses screen"""
        if hasattr(self, 'manager'):
            self.manager.current = "completed_screen"
            for screen in self.manager.screens:
                if screen.name == "completed_screen":
                    screen.populate_completed_addresses()
                    break

    def get_completed_addresses_with_timestamps(self):
        """Get completed addresses with timestamps"""
        result = []
        for index in self.completed_addresses:
            if index < len(self.addresses):
                result.append({
                    'index': index,
                    'address': self.addresses[index],
                    'timestamp': self.completed_timestamps.get(index, datetime.now().isoformat()),
                    'outcome': self.completed_outcomes.get(index, "Done"),
                    'amount': self.completed_amounts.get(index, "")
                })
        return result

    def remove_from_completed(self, index):
        """Remove from completed"""
        if index in self.completed_addresses:
            self.completed_addresses.remove(index)
            self.completed_timestamps.pop(index, None)
            self.completed_outcomes.pop(index, None)
            self.completed_amounts.pop(index, None)
            self.get_sorted_addresses_cached.cache_clear()
            self.save_completion_data()
            self.update_ui_fast()

    def clear_all_completed(self):
        """Clear all completed"""
        self.completed_addresses.clear()
        self.completed_timestamps.clear()
        self.completed_outcomes.clear()
        self.completed_amounts.clear()
        self.get_sorted_addresses_cached.cache_clear()
        self.save_completion_data()
        self.update_ui_fast()

    def refresh_list(self):
        """Refresh address list"""
        if self.addresses:
            self.get_sorted_addresses_cached.cache_clear()
            self.update_ui_fast()

    def _show_welcome(self):
        """Show welcome message"""
        if not self.addresses:
            welcome_card = MDCard(
                size_hint_y=None,
                height=dp(180),
                elevation=2,
                padding=dp(20),
                radius=[8]
            )

            layout = MDBoxLayout(
                orientation='vertical',
                spacing=dp(12),
                adaptive_height=True
            )

            title = MDLabel(
                text="Welcome to Address Navigator",
                theme_text_color="Primary",
                font_style="H6",
                halign="center",
                size_hint_y=None,
                height=dp(32)
            )

            subtitle = MDLabel(
                text="Load a CSV or Excel file to get started\nUse the search field above to filter addresses",
                theme_text_color="Secondary",
                halign="center",
                size_hint_y=None,
                height=dp(48)
            )

            load_btn = MDRaisedButton(
                text="Load File",
                size_hint=(None, None),
                size=(dp(120), dp(36)),
                pos_hint={"center_x": 0.5},
                on_release=lambda x: self.open_file_browser()
            )

            layout.add_widget(title)
            layout.add_widget(subtitle)
            layout.add_widget(load_btn)
            welcome_card.add_widget(layout)
            self.address_layout.add_widget(welcome_card)

class OptimizedAddressApp(MDApp):
    """Ultra-optimized app with minimal overhead"""
    def build(self):
        try:
            self.title = "Address Navigator"
            self.theme_cls.theme_style = "Light"
            self.theme_cls.primary_palette = "Blue"

            # Create screen manager
            self.sm = MDScreenManager()

            # Create main screen immediately
            self.address_screen = UltraFastAddressScreen(name="address_screen")
            self.sm.add_widget(self.address_screen)

            # Lazy load completed screen
            Clock.schedule_once(self._create_completed_screen, 0.5)

            return self.sm
        except Exception as e:
            print(f"Build error: {e}")
            return MDLabel(text=f"Error: {e}")

    def _create_completed_screen(self, dt):
        """Lazy create completed screen"""
        try:
            if not any(s.name == "completed_screen" for s in self.sm.screens):
                self.completed_screen = OptimizedCompletedScreen(self, name="completed_screen")
                self.sm.add_widget(self.completed_screen)
        except Exception as e:
            print(f"Completed screen error: {e}")

    def get_address_screen(self):
        """Get address screen reference"""
        return self.address_screen

    def on_start(self):
        """App start optimization"""
        try:
            # Force initial UI update if addresses exist
            if hasattr(self.address_screen, 'addresses') and self.address_screen.addresses:
                Clock.schedule_once(lambda dt: self.address_screen.update_ui_fast(), 0.1)
        except Exception as e:
            print(f"Start error: {e}")

if __name__ == "__main__":
    OptimizedAddressApp().run()
