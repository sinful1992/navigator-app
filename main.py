##1.3
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.screenmanager import MDScreenManager
from kivymd.uix.button import MDRaisedButton, MDFlatButton
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
from urllib.parse import quote_plus
from datetime import datetime
import threading

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


class AddressCard(MDCard):
    """Simplified, efficient address card with proper cleanup"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint_y = None
        self.height = dp(85)
        self.elevation = 2
        self.padding = dp(12)
        self.radius = [6]
        
        # State tracking
        self.address_index = None
        self.address_text = ""
        
        self._setup_layout()
    
    def _setup_layout(self):
        """Create clean, simple layout"""
        self.main_layout = MDBoxLayout(
            orientation='vertical',
            spacing=dp(8),
            adaptive_height=True
        )
        
        # Address text
        self.address_label = MDLabel(
            theme_text_color="Primary",
            halign="left",
            shorten=True,
            font_size='14sp'
        )
        
        # Status and buttons row
        self.bottom_row = MDBoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=dp(32),
            spacing=dp(8)
        )
        
        self.status_label = MDLabel(
            font_size='12sp',
            size_hint_x=None,
            width=dp(90),
            halign="center"
        )
        
        # Buttons
        self.nav_button = MDFlatButton(
            text="Navigate",
            size_hint=(None, None),
            size=(dp(80), dp(28)),
            font_size='11sp'
        )
        
        self.action_button = MDFlatButton(
            size_hint=(None, None),
            size=(dp(80), dp(28)),
            font_size='11sp'
        )
        
        # Build layout
        self.bottom_row.add_widget(self.status_label)
        self.bottom_row.add_widget(MDLabel())  # Spacer
        self.bottom_row.add_widget(self.nav_button)
        self.bottom_row.add_widget(self.action_button)
        
        self.main_layout.add_widget(self.address_label)
        self.main_layout.add_widget(self.bottom_row)
        self.add_widget(self.main_layout)
    
    def update_card(self, index, address, status_info, callbacks):
        """Single method to update entire card state"""
        self.address_index = index
        self.address_text = address
        
        # Update address text
        prefix = "► " if status_info.get('is_active') else ""
        self.address_label.text = f"{prefix}{index + 1}. {address}"
        
        # Update appearance based on status
        self._update_appearance(status_info)
        
        # Update buttons
        self._update_buttons(status_info, callbacks)
    
    def _update_appearance(self, status_info):
        """Update visual appearance"""
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
                self.status_label.text = f"PIF £{amount}" if amount else "PIF"
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
        """Update button states and callbacks"""
        # Clear previous bindings
        self.nav_button.unbind(on_release=self.nav_button.dispatch)
        self.action_button.unbind(on_release=self.action_button.dispatch)
        
        # Navigation button
        self.nav_button.bind(
            on_release=lambda x: callbacks.get('navigate', lambda a, i: None)(
                self.address_text, self.address_index
            )
        )
        
        # Action button based on state
        if status_info.get('is_completed'):
            self.action_button.text = "Undo"
            self.action_button.theme_text_color = "Primary"
            self.action_button.bind(
                on_release=lambda x: callbacks.get('undo', lambda i: None)(self.address_index)
            )
        elif status_info.get('is_active'):
            self.action_button.text = "Complete"
            self.action_button.theme_text_color = "Custom"
            self.action_button.text_color = [0, 0.7, 0, 1]
            self.action_button.bind(
                on_release=lambda x: callbacks.get('complete', lambda i: None)(self.address_index)
            )
        else:
            self.action_button.text = "Set Active"
            self.action_button.theme_text_color = "Primary"
            self.action_button.bind(
                on_release=lambda x: callbacks.get('activate', lambda i: None)(self.address_index)
            )
    
    def reset_for_reuse(self):
        """Clean reset for card pooling"""
        self.address_index = None
        self.address_text = ""
        self.opacity = 1
        self.height = dp(85)
        self.disabled = False
        self.md_bg_color = (1, 1, 1, 1)
        self.elevation = 2
        
        # Unbind events to prevent memory leaks
        self.nav_button.unbind(on_release=self.nav_button.dispatch)
        self.action_button.unbind(on_release=self.action_button.dispatch)


class SearchField(MDTextField):
    """Efficient search field with proper debouncing"""
    
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
        """Debounced search with reasonable delay"""
        if self._search_event:
            self._search_event.cancel()
        
        # 300ms delay prevents excessive filtering
        self._search_event = Clock.schedule_once(
            lambda dt: self._perform_search(text), 0.3
        )
    
    def _perform_search(self, text):
        """Efficient search by showing/hiding existing cards"""
        query = text.strip().lower()
        self.screen.current_search_query = query
        
        visible_count = 0
        for child in self.screen.address_layout.children:
            if isinstance(child, AddressCard):
                # Check if address matches search
                if not query or query in child.address_text.lower():
                    # Show card
                    child.opacity = 1
                    child.height = dp(85)
                    child.disabled = False
                    visible_count += 1
                else:
                    # Hide card
                    child.opacity = 0
                    child.height = 0
                    child.disabled = True
        
        # Show/hide no results message
        if visible_count == 0 and query:
            self.screen.show_no_results()
        else:
            self.screen.hide_no_results()


class CompletedScreen(MDScreen):
    """Clean completed addresses screen"""
    
    def __init__(self, app_instance, **kwargs):
        super().__init__(**kwargs)
        self.app = app_instance
        self._setup_ui()
    
    def _setup_ui(self):
        layout = MDBoxLayout(orientation='vertical')
        
        # Toolbar
        toolbar = MDTopAppBar(
            title="Completed Addresses",
            size_hint_y=None,
            height=dp(56)
        )
        toolbar.left_action_items = [["arrow-left", lambda x: self.go_back()]]
        toolbar.right_action_items = [
            ["delete", lambda x: self.clear_completed_dialog()],
            ["download", lambda x: self.export_completed()]
        ]
        layout.add_widget(toolbar)
        
        # Content
        scroll = MDScrollView()
        self.content_layout = MDBoxLayout(
            orientation='vertical',
            adaptive_height=True,
            spacing=dp(8),
            padding=dp(12)
        )
        scroll.add_widget(self.content_layout)
        layout.add_widget(scroll)
        
        self.add_widget(layout)
    
    def go_back(self):
        self.manager.current = "main_screen"
    
    def populate_completed(self):
        """Populate with completed addresses"""
        self.content_layout.clear_widgets()
        
        main_screen = self.app.get_main_screen()
        if not main_screen:
            return
        
        completed_addresses = main_screen.get_completed_addresses()
        
        if not completed_addresses:
            self._show_no_completed()
            return
        
        # Sort by completion time (newest first)
        completed_addresses.sort(
            key=lambda x: x['completion'].get('timestamp', ''),
            reverse=True
        )
        
        # Summary
        summary_card = MDCard(
            size_hint_y=None,
            height=dp(60),
            elevation=2,
            padding=dp(12)
        )
        summary_layout = MDBoxLayout(orientation='horizontal')
        summary_layout.add_widget(
            MDLabel(text=f"Total Completed: {len(completed_addresses)}", font_style="H6")
        )
        summary_layout.add_widget(
            MDFlatButton(
                text="Export",
                size_hint_x=None,
                width=dp(80),
                on_release=lambda x: self.export_completed()
            )
        )
        summary_card.add_widget(summary_layout)
        self.content_layout.add_widget(summary_card)
        
        # Address cards
        for item in completed_addresses:
            card = self._create_completed_card(item)
            self.content_layout.add_widget(card)
    
    def _create_completed_card(self, item):
        """Create card for completed address"""
        card = MDCard(
            size_hint_y=None,
            height=dp(90),
            elevation=1,
            padding=dp(12)
        )
        
        layout = MDBoxLayout(orientation='vertical', spacing=dp(6))
        
        # Address and outcome
        top_row = MDBoxLayout(orientation='horizontal')
        address_label = MDLabel(
            text=f"{item['index'] + 1}. {item['address']}",
            size_hint_x=0.7,
            shorten=True
        )
        outcome_label = MDLabel(
            text=item['completion']['outcome'],
            size_hint_x=0.3,
            halign="right",
            theme_text_color="Custom",
            text_color=self._get_outcome_color(item['completion']['outcome'])
        )
        top_row.add_widget(address_label)
        top_row.add_widget(outcome_label)
        
        # Timestamp
        timestamp = item['completion'].get('timestamp', '')
        time_text = self._format_timestamp(timestamp)
        time_label = MDLabel(
            text=time_text,
            theme_text_color="Secondary",
            font_size='11sp'
        )
        
        # Buttons
        button_row = MDBoxLayout(orientation='horizontal', size_hint_y=None, height=dp(28))
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
            on_release=lambda x, idx=item['index']: self.remove_completed(idx)
        )
        button_row.add_widget(nav_btn)
        button_row.add_widget(MDLabel())  # Spacer
        button_row.add_widget(remove_btn)
        
        layout.add_widget(top_row)
        layout.add_widget(time_label)
        layout.add_widget(button_row)
        card.add_widget(layout)
        
        return card
    
    def _get_outcome_color(self, outcome):
        """Get color for outcome"""
        colors = {
            "PIF": [0, 0.7, 0, 1],
            "DA": [0.8, 0.1, 0.1, 1],
            "Done": [0, 0.5, 0.8, 1]
        }
        return colors.get(outcome, [0.5, 0.5, 0.5, 1])
    
    def _format_timestamp(self, timestamp):
        """Format timestamp for display"""
        try:
            dt = datetime.fromisoformat(timestamp)
            return dt.strftime("%m/%d %I:%M %p")
        except:
            return "Unknown"
    
    def _show_no_completed(self):
        """Show message when no completed addresses"""
        card = MDCard(
            size_hint_y=None,
            height=dp(100),
            elevation=2,
            padding=dp(16)
        )
        layout = MDBoxLayout(orientation='vertical', spacing=dp(8))
        layout.add_widget(
            MDLabel(
                text="No Completed Addresses",
                theme_text_color="Primary",
                font_style="H6",
                halign="center"
            )
        )
        layout.add_widget(
            MDLabel(
                text="Complete addresses to see them here",
                theme_text_color="Secondary",
                halign="center"
            )
        )
        card.add_widget(layout)
        self.content_layout.add_widget(card)
    
    def navigate_to_address(self, address):
        """Navigate to completed address"""
        main_screen = self.app.get_main_screen()
        if main_screen:
            main_screen.navigate_to_address(address, -1, from_completed=True)
    
    def remove_completed(self, index):
        """Remove from completed"""
        main_screen = self.app.get_main_screen()
        if main_screen:
            main_screen.remove_from_completed(index)
            self.populate_completed()
    
    def clear_completed_dialog(self):
        """Show dialog to clear all completed"""
        if not hasattr(self, '_clear_dialog'):
            self._clear_dialog = MDDialog(
                title="Clear All Completed?",
                text="This cannot be undone.",
                buttons=[
                    MDFlatButton(
                        text="Cancel",
                        on_release=lambda x: self._clear_dialog.dismiss()
                    ),
                    MDFlatButton(
                        text="Clear All",
                        theme_text_color="Error",
                        on_release=lambda x: self._clear_all()
                    ),
                ],
            )
        self._clear_dialog.open()
    
    def _clear_all(self):
        """Clear all completed addresses"""
        main_screen = self.app.get_main_screen()
        if main_screen:
            main_screen.clear_all_completed()
            self.populate_completed()
        self._clear_dialog.dismiss()
    
    def export_completed(self):
        """Export completed addresses to CSV"""
        threading.Thread(target=self._export_background, daemon=True).start()
    
    def _export_background(self):
        """Background export process"""
        try:
            main_screen = self.app.get_main_screen()
            if not main_screen:
                return
            
            completed = main_screen.get_completed_addresses()
            if not completed:
                return
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"completed_addresses_{timestamp}.csv"
            filepath = self._get_export_path(filename)
            
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['Index', 'Address', 'Outcome', 'Amount', 'Date', 'Time'])
                
                for item in completed:
                    completion = item['completion']
                    try:
                        dt = datetime.fromisoformat(completion.get('timestamp', ''))
                        date_str = dt.strftime("%Y-%m-%d")
                        time_str = dt.strftime("%H:%M:%S")
                    except:
                        date_str = time_str = "Unknown"
                    
                    writer.writerow([
                        item['index'] + 1,
                        item['address'],
                        completion.get('outcome', 'Done'),
                        completion.get('amount', ''),
                        date_str,
                        time_str
                    ])
            
            Clock.schedule_once(
                lambda dt: toast(f"Exported to {filename}"), 0
            )
        
        except Exception as e:
            Clock.schedule_once(
                lambda dt: toast(f"Export failed: {str(e)}"), 0
            )
    
    def _get_export_path(self, filename):
        """Get export file path"""
        if platform == 'android' and ANDROID_AVAILABLE:
            try:
                app_path = PythonActivity.mActivity.getFilesDir().getAbsolutePath()
                return os.path.join(app_path, filename)
            except:
                return filename
        return os.path.join(os.path.expanduser("~"), filename)


class MainScreen(MDScreen):
    """Simplified and efficient main screen"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Core data - single source of truth
        self.addresses = []
        self.completed_data = {}  # {index: {outcome, amount, timestamp}}
        self.active_index = None
        self.current_search_query = ""
        
        # UI management
        self._card_pool = []
        self._active_cards = {}
        self._no_results_card = None
        
        # File handling
        self.data_file = "address_navigator_data.json"
        self.file_manager = None
        
        # Dialogs (created on demand)
        self._completion_dialog = None
        self._payment_dialog = None
        self._current_completion_index = None
        
        # Android storage
        self._setup_android_storage()
        
        # Initialize
        self._setup_ui()
        self._load_data()
        self._update_display()
        
        if platform == 'android' and ANDROID_AVAILABLE:
            Clock.schedule_once(self._request_permissions, 0.5)
    
    def _setup_android_storage(self):
        """Setup Android storage if available"""
        self.storage_handler = None
        self.chooser = None
        
        if platform == 'android' and ASK_AVAILABLE:
            try:
                self.storage_handler = SharedStorage()
                self.chooser = Chooser(self._on_android_file_selected)
            except:
                pass
    
    def _setup_ui(self):
        """Create clean UI layout"""
        layout = MDBoxLayout(orientation='vertical')
        
        # Toolbar
        self.toolbar = MDTopAppBar(
            title="Address Navigator",
            size_hint_y=None,
            height=dp(56)
        )
        self.toolbar.right_action_items = [
            ["folder-open", lambda x: self.load_file()],
            ["check-all", lambda x: self.show_completed_screen()],
            ["refresh", lambda x: self.refresh_display()]
        ]
        layout.add_widget(self.toolbar)
        
        # Progress indicator
        self.progress_bar = MDProgressBar(
            size_hint_y=None,
            height=dp(3),
            opacity=0
        )
        layout.add_widget(self.progress_bar)
        
        # Search field
        search_container = MDBoxLayout(
            orientation='vertical',
            size_hint_y=None,
            height=dp(64),
            padding=[dp(12), dp(8)]
        )
        self.search_field = SearchField(self)
        search_container.add_widget(self.search_field)
        layout.add_widget(search_container)
        
        # Address list
        scroll = MDScrollView()
        self.address_layout = MDBoxLayout(
            orientation='vertical',
            adaptive_height=True,
            spacing=dp(8),
            padding=[dp(12), dp(12)]
        )
        scroll.add_widget(self.address_layout)
        layout.add_widget(scroll)
        
        self.add_widget(layout)
        
        # Initialize file manager
        self._init_file_manager()
    
    def _init_file_manager(self):
        """Initialize file manager"""
        try:
            self.file_manager = MDFileManager(
                exit_manager=self._close_file_manager,
                select_path=self._on_file_selected,
                preview=False
            )
        except:
            self.file_manager = None
    
    def _get_card_from_pool(self):
        """Get card from pool or create new one"""
        if self._card_pool:
            return self._card_pool.pop()
        return AddressCard()
    
    def _return_card_to_pool(self, card):
        """Return card to pool with proper cleanup"""
        if len(self._card_pool) < 20:  # Reasonable pool size
            card.reset_for_reuse()
            self._card_pool.append(card)
    
    def show_progress(self, show=True):
        """Show/hide progress indicator"""
        Animation(
            opacity=1 if show else 0,
            duration=0.2
        ).start(self.progress_bar)
    
    def _update_display(self):
        """Update the main address display"""
        # Clear existing cards
        self._clear_address_display()
        
        if not self.addresses:
            self._show_welcome_card()
            return
        
        # Create callback dict
        callbacks = {
            'navigate': self.navigate_to_address,
            'activate': self.set_active_address,
            'complete': self.show_completion_dialog,
            'undo': self.undo_completion
        }
        
        # Create cards for all addresses
        for i, address in enumerate(self.addresses):
            card = self._get_card_from_pool()
            
            # Determine status
            status_info = {
                'is_active': i == self.active_index,
                'is_completed': i in self.completed_data,
                'completion': self.completed_data.get(i, {})
            }
            
            card.update_card(i, address, status_info, callbacks)
            self.address_layout.add_widget(card)
            self._active_cards[i] = card
        
        # Apply search filter if active
        if self.current_search_query:
            Clock.schedule_once(
                lambda dt: self.search_field._perform_search(self.current_search_query),
                0.1
            )
    
    def _clear_address_display(self):
        """Clear current address display"""
        # Return cards to pool
        for card in self._active_cards.values():
            self.address_layout.remove_widget(card)
            self._return_card_to_pool(card)
        
        self._active_cards.clear()
        
        # Remove other widgets (welcome card, no results, etc.)
        self.address_layout.clear_widgets()
    
    def _show_welcome_card(self):
        """Show welcome message for empty state"""
        welcome_card = MDCard(
            size_hint_y=None,
            height=dp(160),
            elevation=2,
            padding=dp(20)
        )
        
        layout = MDBoxLayout(orientation='vertical', spacing=dp(12))
        layout.add_widget(
            MDLabel(
                text="Welcome to Address Navigator",
                theme_text_color="Primary",
                font_style="H6",
                halign="center"
            )
        )
        layout.add_widget(
            MDLabel(
                text="Load a CSV or Excel file to get started",
                theme_text_color="Secondary",
                halign="center"
            )
        )
        layout.add_widget(
            MDRaisedButton(
                text="Load File",
                size_hint=(None, None),
                size=(dp(120), dp(36)),
                pos_hint={"center_x": 0.5},
                on_release=lambda x: self.load_file()
            )
        )
        
        welcome_card.add_widget(layout)
        self.address_layout.add_widget(welcome_card)
    
    def show_no_results(self):
        """Show no search results message"""
        if self._no_results_card:
            return
        
        self._no_results_card = MDCard(
            size_hint_y=None,
            height=dp(80),
            elevation=1,
            padding=dp(16)
        )
        
        label = MDLabel(
            text="No addresses match your search",
            theme_text_color="Secondary",
            halign="center"
        )
        self._no_results_card.add_widget(label)
        self.address_layout.add_widget(self._no_results_card, index=0)
    
    def hide_no_results(self):
        """Hide no search results message"""
        if self._no_results_card:
            self.address_layout.remove_widget(self._no_results_card)
            self._no_results_card = None
    
    def set_active_address(self, index):
        """Set an address as active"""
        if index == self.active_index:
            return
        
        previous_active = self.active_index
        self.active_index = index
        
        # Update affected cards
        indices_to_update = [index]
        if previous_active is not None:
            indices_to_update.append(previous_active)
        
        self._update_specific_cards(indices_to_update)
        self._save_data()
    
    def _update_specific_cards(self, indices):
        """Update specific cards efficiently"""
        callbacks = {
            'navigate': self.navigate_to_address,
            'activate': self.set_active_address,
            'complete': self.show_completion_dialog,
            'undo': self.undo_completion
        }
        
        for index in indices:
            if index in self._active_cards:
                card = self._active_cards[index]
                status_info = {
                    'is_active': index == self.active_index,
                    'is_completed': index in self.completed_data,
                    'completion': self.completed_data.get(index, {})
                }
                card.update_card(index, card.address_text, status_info, callbacks)
    
    def show_completion_dialog(self, index):
        """Show address completion dialog"""
        if not self._completion_dialog:
            self._create_completion_dialog()
        
        self._current_completion_index = index
        address = self.addresses[index] if index < len(self.addresses) else "Unknown"
        self._completion_dialog.text = f"Mark as completed: {address[:60]}..."
        self._completion_dialog.open()
    
    def _create_completion_dialog(self):
        """Create completion dialog"""
        self._completion_dialog = MDDialog(
            title="Complete Address",
            text="",
            buttons=[
                MDFlatButton(
                    text="Cancel",
                    on_release=lambda x: self._completion_dialog.dismiss()
                ),
                MDFlatButton(
                    text="Done",
                    theme_text_color="Primary",
                    on_release=lambda x: self._complete_address("Done", "")
                ),
                MDFlatButton(
                    text="DA",
                    theme_text_color="Error",
                    on_release=lambda x: self._complete_address("DA", "")
                ),
                MDFlatButton(
                    text="PIF",
                    theme_text_color="Custom",
                    text_color=[0, 0.7, 0, 1],
                    on_release=lambda x: self._show_payment_dialog()
                )
            ],
        )
    
    def _show_payment_dialog(self):
        """Show payment amount dialog for PIF"""
        if not self._payment_dialog:
            self._create_payment_dialog()
        
        self._completion_dialog.dismiss()
        self._payment_field.text = ""
        self._payment_dialog.open()
    
    def _create_payment_dialog(self):
        """Create payment dialog"""
        self._payment_field = MDTextField(
            hint_text="Amount (£)",
            size_hint_x=None,
            width=dp(200),
            input_filter="float",
            halign="center"
        )
        
        content = MDBoxLayout(
            orientation='vertical',
            spacing=dp(12),
            adaptive_height=True
        )
        content.add_widget(self._payment_field)
        
        self._payment_dialog = MDDialog(
            title="Payment Amount",
            type="custom",
            content_cls=content,
            buttons=[
                MDFlatButton(
                    text="Cancel",
                    on_release=lambda x: self._payment_dialog.dismiss()
                ),
                MDFlatButton(
                    text="Confirm",
                    theme_text_color="Custom",
                    text_color=[0, 0.7, 0, 1],
                    on_release=lambda x: self._confirm_payment()
                ),
            ],
        )
    
    def _confirm_payment(self):
        """Confirm PIF payment"""
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
        """Complete an address with given outcome"""
        if self._current_completion_index is None:
            return
        
        index = self._current_completion_index
        self._completion_dialog.dismiss()
        
        # Store completion data
        self.completed_data[index] = {
            'outcome': outcome,
            'amount': amount,
            'timestamp': datetime.now().isoformat()
        }
        
        # Clear active status if this was the active address
        if self.active_index == index:
            self.active_index = None
        
        # Update UI
        self._update_specific_cards([index])
        self._save_data()
        
        toast(f"Address marked as {outcome}")
    
    def undo_completion(self, index):
        """Undo address completion"""
        if index in self.completed_data:
            del self.completed_data[index]
            self._update_specific_cards([index])
            self._save_data()
            toast("Completion undone")
    
    def navigate_to_address(self, address, index, from_completed=False):
        """Navigate to address using maps"""
        # Set as active if not completed and not from completed screen
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
            # Fallback to web maps
            try:
                webbrowser.open(f"https://www.google.com/maps/search/{encoded_address}")
            except:
                toast("Unable to open maps")
    
    def _open_android_maps(self, encoded_address):
        """Open Android maps app"""
        try:
            intent = Intent()
            intent.setAction(Intent.ACTION_VIEW)
            intent.setData(Uri.parse(f"geo:0,0?q={encoded_address}"))
            PythonActivity.mActivity.startActivity(intent)
        except Exception:
            self._open_web_maps(encoded_address)
    
    def _open_web_maps(self, encoded_address):
        """Open web maps"""
        webbrowser.open(f"https://www.google.com/maps/search/{encoded_address}")
    
    def load_file(self):
        """Load addresses from file"""
        if platform == 'android' and self.chooser:
            try:
                self.chooser.choose_content('*/*')
                return
            except:
                pass
        
        # Use file manager
        if not self.file_manager:
            toast("File manager not available")
            return
        
        try:
            if platform == 'android':
                # Try common Android paths
                paths = [
                    "/storage/emulated/0/Documents",
                    "/storage/emulated/0/Download", 
                    "/storage/emulated/0"
                ]
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
        """Handle Android SAF file selection"""
        def process():
            try:
                if not shared_file_list or not self.storage_handler:
                    return
                
                # Copy file to app storage
                private_path = self.storage_handler.copy_from_shared(shared_file_list[0])
                if not private_path or not os.path.exists(private_path):
                    Clock.schedule_once(lambda dt: toast("Failed to access file"), 0)
                    return
                
                # Process file based on extension
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
        """Handle file manager selection"""
        self._close_file_manager()
        
        lower = path.lower()
        if lower.endswith('.csv'):
            self._load_csv_file(path)
        elif lower.endswith(('.xlsx', '.xls')) and OPENPYXL_AVAILABLE:
            self._load_excel_file(path)
        else:
            toast("Please select a CSV or Excel file")
    
    def _close_file_manager(self):
        """Close file manager"""
        if self.file_manager:
            try:
                self.file_manager.close()
            except:
                pass
    
    def _load_csv_file(self, file_path):
        """Load CSV file in background"""
        self.show_progress(True)
        
        def load_background():
            try:
                addresses = []
                
                # Try different encodings
                for encoding in ['utf-8', 'utf-8-sig', 'latin1', 'cp1252']:
                    try:
                        with open(file_path, 'r', encoding=encoding) as f:
                            reader = csv.reader(f)
                            rows = list(reader)
                        break
                    except (UnicodeDecodeError, UnicodeError):
                        continue
                else:
                    Clock.schedule_once(
                        lambda dt: toast("Could not read file - encoding issue"), 0
                    )
                    Clock.schedule_once(lambda dt: self.show_progress(False), 0)
                    return
                
                if not rows:
                    Clock.schedule_once(lambda dt: toast("File is empty"), 0)
                    Clock.schedule_once(lambda dt: self.show_progress(False), 0)
                    return
                
                # Find address column
                headers = [str(cell).lower() for cell in rows[0]]
                address_col = 0
                
                for i, header in enumerate(headers):
                    if 'address' in header:
                        address_col = i
                        break
                
                # Extract addresses
                for row in rows[1:]:
                    if len(row) > address_col and row[address_col]:
                        address = str(row[address_col]).strip()
                        if address and address.lower() not in ['none', 'null', '']:
                            addresses.append(address)
                
                Clock.schedule_once(
                    lambda dt: self._load_addresses_data(addresses), 0
                )
                
            except Exception as e:
                Clock.schedule_once(
                    lambda dt: toast(f"Error reading CSV: {str(e)}"), 0
                )
                Clock.schedule_once(lambda dt: self.show_progress(False), 0)
        
        threading.Thread(target=load_background, daemon=True).start()
    
    def _load_excel_file(self, file_path):
        """Load Excel file in background"""
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
                
                # Find address column
                headers = [str(cell).lower() if cell else '' for cell in rows[0]]
                address_col = 0
                
                for i, header in enumerate(headers):
                    if 'address' in header:
                        address_col = i
                        break
                
                # Extract addresses
                addresses = []
                for row in rows[1:]:
                    if len(row) > address_col and row[address_col]:
                        address = str(row[address_col]).strip()
                        if address and address.lower() not in ['none', 'null', '']:
                            addresses.append(address)
                
                Clock.schedule_once(
                    lambda dt: self._load_addresses_data(addresses), 0
                )
                
            except Exception as e:
                Clock.schedule_once(
                    lambda dt: toast(f"Error reading Excel: {str(e)}"), 0
                )
                Clock.schedule_once(lambda dt: self.show_progress(False), 0)
        
        threading.Thread(target=load_background, daemon=True).start()
    
    def _load_addresses_data(self, addresses):
        """Load new address data"""
        self.show_progress(False)
        
        if not addresses:
            toast("No addresses found in file")
            return
        
        # Reset all data
        self.addresses = addresses
        self.completed_data = {}
        self.active_index = None
        self.current_search_query = ""
        
        # Clear search
        self.search_field.text = ""
        
        # Update display
        self._update_display()
        self._save_data()
        
        toast(f"Loaded {len(addresses)} addresses")
    
    def show_completed_screen(self):
        """Switch to completed addresses screen"""
        if hasattr(self, 'manager'):
            self.manager.current = "completed_screen"
            # Populate completed screen
            for screen in self.manager.screens:
                if screen.name == "completed_screen":
                    screen.populate_completed()
                    break
    
    def get_completed_addresses(self):
        """Get list of completed addresses with details"""
        completed = []
        for index, completion_data in self.completed_data.items():
            if index < len(self.addresses):
                completed.append({
                    'index': index,
                    'address': self.addresses[index],
                    'completion': completion_data
                })
        return completed
    
    def remove_from_completed(self, index):
        """Remove address from completed list"""
        if index in self.completed_data:
            del self.completed_data[index]
            self._save_data()
            # Update display if address is visible
            if index in self._active_cards:
                self._update_specific_cards([index])
    
    def clear_all_completed(self):
        """Clear all completed addresses"""
        completed_indices = list(self.completed_data.keys())
        self.completed_data.clear()
        self._save_data()
        # Update display
        self._update_specific_cards(completed_indices)
        toast("All completed addresses cleared")
    
    def refresh_display(self):
        """Refresh the address display"""
        self._update_display()
        toast("Display refreshed")
    
    def _save_data(self):
        """Save all data to single file"""
        try:
            data = {
                'addresses': self.addresses,
                'completed_data': self.completed_data,
                'active_index': self.active_index,
                'version': '2.0'
            }
            
            filepath = self._get_data_file_path()
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            print(f"Save error: {e}")
    
    def _load_data(self):
        """Load all data from single file"""
        try:
            filepath = self._get_data_file_path()
            if not os.path.exists(filepath):
                return
            
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.addresses = data.get('addresses', [])
            
            # Handle legacy format
            if 'completed_data' in data:
                self.completed_data = {int(k): v for k, v in data['completed_data'].items()}
            else:
                # Legacy migration
                completed_set = set(data.get('completed_addresses', []))
                timestamps = data.get('completed_timestamps', {})
                outcomes = data.get('completed_outcomes', {})
                amounts = data.get('completed_amounts', {})
                
                self.completed_data = {}
                for index in completed_set:
                    self.completed_data[index] = {
                        'outcome': outcomes.get(str(index), 'Done'),
                        'amount': amounts.get(str(index), ''),
                        'timestamp': timestamps.get(str(index), datetime.now().isoformat())
                    }
            
            self.active_index = data.get('active_index')
            
        except Exception as e:
            print(f"Load error: {e}")
            # Initialize with defaults
            self.addresses = []
            self.completed_data = {}
            self.active_index = None
    
    def _get_data_file_path(self):
        """Get data file path"""
        if platform == 'android' and ANDROID_AVAILABLE:
            try:
                app_path = PythonActivity.mActivity.getFilesDir().getAbsolutePath()
                return os.path.join(app_path, self.data_file)
            except:
                return self.data_file
        
        return os.path.join(os.path.expanduser("~"), self.data_file)
    
    def _request_permissions(self, dt):
        """Request Android permissions"""
        if platform == 'android' and ANDROID_AVAILABLE:
            try:
                request_permissions([
                    Permission.READ_EXTERNAL_STORAGE,
                    Permission.WRITE_EXTERNAL_STORAGE
                ])
            except:
                pass


class AddressNavigatorApp(MDApp):
    """Clean, efficient address navigator app"""
    
    def build(self):
        try:
            self.title = "Address Navigator"
            self.theme_cls.theme_style = "Light"
            self.theme_cls.primary_palette = "Blue"
            
            # Create screen manager
            self.screen_manager = MDScreenManager()
            
            # Create main screen
            self.main_screen = MainScreen(name="main_screen")
            self.screen_manager.add_widget(self.main_screen)
            
            # Create completed screen (lazy loaded)
            Clock.schedule_once(self._create_completed_screen, 1.0)
            
            return self.screen_manager
            
        except Exception as e:
            print(f"Build error: {e}")
            # Return error screen
            error_screen = MDScreen()
            error_layout = MDBoxLayout(orientation='vertical', padding=dp(20))
            error_layout.add_widget(
                MDLabel(
                    text=f"Application Error: {str(e)}",
                    theme_text_color="Error",
                    halign="center"
                )
            )
            error_screen.add_widget(error_layout)
            return error_screen
    
    def _create_completed_screen(self, dt):
        """Create completed screen when needed"""
        try:
            if not any(screen.name == "completed_screen" for screen in self.screen_manager.screens):
                completed_screen = CompletedScreen(self, name="completed_screen")
                self.screen_manager.add_widget(completed_screen)
        except Exception as e:
            print(f"Error creating completed screen: {e}")
    
    def get_main_screen(self):
        """Get reference to main screen"""
        return self.main_screen
    
    def on_start(self):
        """App startup"""
        try:
            # Any startup tasks can go here
            pass
        except Exception as e:
            print(f"Startup error: {e}")


if __name__ == "__main__":
    AddressNavigatorApp().run()