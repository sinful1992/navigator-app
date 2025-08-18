from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.screenmanager import MDScreenManager
from kivymd.uix.button import MDRaisedButton, MDIconButton
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.toolbar import MDTopAppBar
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton
from kivymd.uix.filemanager import MDFileManager
from kivymd.toast import toast
from kivy.metrics import dp
from kivy.clock import Clock
import pandas as pd
import webbrowser
import os
import json
from urllib.parse import quote_plus


class AddressScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.addresses = []
        self.completed_addresses = set()
        self.completion_file = "completed_addresses.json"
        self.file_manager = None
        self.dialog = None
        
        # Load completed addresses from file
        self.load_completed_addresses()
        
        # Create the main layout
        main_layout = MDBoxLayout(orientation='vertical')
        
        # Add toolbar
        toolbar = MDTopAppBar(
            title="Address Navigator",
            elevation=2
        )
        toolbar.right_action_items = [
            ["folder-open", lambda x: self.open_file_manager()],
            ["refresh", lambda x: self.refresh_addresses()]
        ]
        main_layout.add_widget(toolbar)
        
        # Create scroll view for address buttons
        self.scroll_view = MDScrollView()
        self.address_layout = MDBoxLayout(
            orientation='vertical',
            adaptive_height=True,
            spacing=dp(10),
            padding=dp(10)
        )
        
        self.scroll_view.add_widget(self.address_layout)
        main_layout.add_widget(self.scroll_view)
        
        self.add_widget(main_layout)
        
        # Initialize file manager
        self.init_file_manager()
        
        # Add initial message if no addresses loaded
        self.show_initial_message()
    
    def init_file_manager(self):
        self.file_manager = MDFileManager(
            exit_manager=self.exit_manager,
            select_path=self.select_path,
        )
    
    def open_file_manager(self):
        # Try to open in Downloads folder first, fallback to root
        try:
            downloads_path = "/storage/emulated/0/Download"
            if os.path.exists(downloads_path):
                self.file_manager.show(downloads_path)
            else:
                self.file_manager.show("/")
        except:
            self.file_manager.show("/")
    
    def select_path(self, path):
        """Handle file selection"""
        self.exit_manager()
        if path.lower().endswith(('.xlsx', '.xls')):
            self.load_xlsx_file(path)
        else:
            toast("Please select an Excel file (.xlsx or .xls)")
    
    def exit_manager(self, *args):
        """Close file manager"""
        self.file_manager.close()
    
    def load_xlsx_file(self, file_path):
        """Load addresses from XLSX file"""
        try:
            # Read the Excel file
            df = pd.read_excel(file_path)
            
            # Look for address column (try common names)
            address_column = None
            possible_names = ['address', 'Address', 'ADDRESS', 'street', 'Street', 'location', 'Location']
            
            for col_name in possible_names:
                if col_name in df.columns:
                    address_column = col_name
                    break
            
            if address_column is None:
                # If no standard column found, use the first column
                address_column = df.columns[0]
                toast(f"Using column '{address_column}' as addresses")
            
            # Extract addresses and remove NaN values
            self.addresses = df[address_column].dropna().tolist()
            
            if self.addresses:
                self.create_address_buttons()
                toast(f"Loaded {len(self.addresses)} addresses")
            else:
                toast("No addresses found in the file")
                
        except Exception as e:
            toast(f"Error loading file: {str(e)}")
    
    def create_address_buttons(self):
        """Create buttons for each address"""
        # Clear existing buttons
        self.address_layout.clear_widgets()
        
        for i, address in enumerate(self.addresses):
            # Create card for each address
            card = MDCard(
                size_hint_y=None,
                height=dp(80),
                elevation=2,
                padding=dp(10),
                spacing=dp(10)
            )
            
            card_layout = MDBoxLayout(
                orientation='horizontal',
                adaptive_width=True
            )
            
            # Address label
            address_label = MDLabel(
                text=str(address),
                theme_text_color="Primary",
                size_hint_x=0.7,
                text_size=(None, None)
            )
            
            # Navigation button
            nav_button = MDRaisedButton(
                text="Navigate",
                size_hint_x=0.2,
                on_release=lambda x, addr=address, idx=i: self.navigate_to_address(addr, idx)
            )
            
            # Completion button
            is_completed = i in self.completed_addresses
            complete_button = MDIconButton(
                icon="check-circle" if is_completed else "circle-outline",
                theme_icon_color="Custom",
                icon_color="green" if is_completed else "grey",
                size_hint_x=0.1,
                on_release=lambda x, idx=i: self.toggle_completion(idx)
            )
            
            card_layout.add_widget(address_label)
            card_layout.add_widget(nav_button)
            card_layout.add_widget(complete_button)
            
            card.add_widget(card_layout)
            self.address_layout.add_widget(card)
    
    def navigate_to_address(self, address, index):
        """Open Google Maps with the address"""
        try:
            # Encode address for URL
            encoded_address = quote_plus(str(address))
            maps_url = f"https://www.google.com/maps/search/{encoded_address}"
            
            # Open in browser (on Android this should open Google Maps app)
            webbrowser.open(maps_url)
            
            toast(f"Opening navigation to: {address}")
            
        except Exception as e:
            toast(f"Error opening maps: {str(e)}")
    
    def toggle_completion(self, index):
        """Toggle completion status of an address"""
        if index in self.completed_addresses:
            self.completed_addresses.remove(index)
            toast("Marked as incomplete")
        else:
            self.completed_addresses.add(index)
            toast("Marked as completed")
        
        # Save to file
        self.save_completed_addresses()
        
        # Refresh the buttons to update visual state
        self.create_address_buttons()
    
    def save_completed_addresses(self):
        """Save completed addresses to file"""
        try:
            with open(self.completion_file, 'w') as f:
                json.dump(list(self.completed_addresses), f)
        except Exception as e:
            print(f"Error saving completion data: {e}")
    
    def load_completed_addresses(self):
        """Load completed addresses from file"""
        try:
            if os.path.exists(self.completion_file):
                with open(self.completion_file, 'r') as f:
                    completed_list = json.load(f)
                    self.completed_addresses = set(completed_list)
        except Exception as e:
            print(f"Error loading completion data: {e}")
            self.completed_addresses = set()
    
    def refresh_addresses(self):
        """Refresh the address list"""
        if self.addresses:
            self.create_address_buttons()
            toast("Address list refreshed")
        else:
            toast("No addresses to refresh. Please load an Excel file first.")
    
    def show_initial_message(self):
        """Show initial message when no addresses are loaded"""
        if not self.addresses:
            message_card = MDCard(
                size_hint=(None, None),
                size=(dp(300), dp(200)),
                pos_hint={"center_x": 0.5, "center_y": 0.5},
                elevation=3,
                padding=dp(20)
            )
            
            message_layout = MDBoxLayout(
                orientation='vertical',
                adaptive_height=True,
                spacing=dp(20)
            )
            
            message_label = MDLabel(
                text="Welcome to Address Navigator!\n\nTap the folder icon in the toolbar to load an Excel file with addresses.",
                theme_text_color="Primary",
                halign="center",
                text_size=(dp(260), None)
            )
            
            load_button = MDRaisedButton(
                text="Load Excel File",
                size_hint=(None, None),
                size=(dp(200), dp(40)),
                pos_hint={"center_x": 0.5},
                on_release=lambda x: self.open_file_manager()
            )
            
            message_layout.add_widget(message_label)
            message_layout.add_widget(load_button)
            message_card.add_widget(message_layout)
            
            self.address_layout.add_widget(message_card)


class AddressNavigatorApp(MDApp):
    def build(self):
        self.title = "Address Navigator"
        self.theme_cls.theme_style = "Light"
        self.theme_cls.primary_palette = "Blue"
        
        # Create screen manager
        sm = MDScreenManager()
        
        # Add address screen
        address_screen = AddressScreen(name="address_screen")
        sm.add_widget(address_screen)
        
        return sm


if __name__ == "__main__":
    AddressNavigatorApp().run()
