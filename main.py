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
from kivymd.toast import toast
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.utils import platform
import csv
import webbrowser
import os
import json
from urllib.parse import quote_plus
from datetime import datetime

# Try to import openpyxl, fallback if not available
try:
    from openpyxl import load_workbook
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False
    print("openpyxl not available, Excel support disabled")

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
        print("Android modules not available")

    # Storage Access Framework helper (Android 10+ scoped storage)
    try:
        from androidstorage4kivy import Chooser, SharedStorage
        ASK_AVAILABLE = True
    except Exception:
        print("androidstorage4kivy not available (Chooser/SharedStorage disabled)")
        ASK_AVAILABLE = False


class CompletedAddressesScreen(MDScreen):
    def __init__(self, app_instance, **kwargs):
        super().__init__(**kwargs)
        self.app_instance = app_instance

        main_layout = MDBoxLayout(
            orientation='vertical',
            size_hint=(1, 1),
            pos_hint={'center_x': 0.5, 'center_y': 0.5}
        )

        toolbar = MDTopAppBar(
            title="Completed Addresses",
            elevation=2,
            size_hint_y=None,
            height=dp(56)
        )
        toolbar.left_action_items = [["arrow-left", lambda x: self.go_back()]]
        toolbar.right_action_items = [
            ["delete", lambda x: self.clear_completed_dialog()],
            ["download", lambda x: self.export_completed()]
        ]
        main_layout.add_widget(toolbar)

        self.scroll_view = MDScrollView(size_hint=(1, 1))
        self.completed_layout = MDBoxLayout(
            orientation='vertical',
            adaptive_height=True,
            spacing=dp(10),
            padding=[dp(16), dp(16), dp(16), dp(16)]
        )
        self.scroll_view.add_widget(self.completed_layout)
        main_layout.add_widget(self.scroll_view)
        self.add_widget(main_layout)

        self.populate_completed_addresses()

    def go_back(self):
        self.manager.current = "address_screen"

    def populate_completed_addresses(self):
        self.completed_layout.clear_widgets()
        address_screen = self.app_instance.get_address_screen()
        if not address_screen:
            return

        completed_data = address_screen.get_completed_addresses_with_timestamps()

        if not completed_data:
            no_data_card = MDCard(
                size_hint_y=None,
                height=dp(150),
                elevation=2,
                padding=dp(20),
                radius=[12]
            )
            no_data_layout = MDBoxLayout(
                orientation='vertical',
                adaptive_height=True,
                spacing=dp(16)
            )
            title_label = MDLabel(
                text="No Completed Addresses",
                theme_text_color="Primary",
                font_style="H6",
                halign="center",
                size_hint_y=None,
                height=dp(32)
            )
            subtitle_label = MDLabel(
                text="Complete some addresses from the main screen to see them here.",
                theme_text_color="Secondary",
                halign="center",
                size_hint_y=None,
                height=dp(48)
            )
            no_data_layout.add_widget(title_label)
            no_data_layout.add_widget(subtitle_label)
            no_data_card.add_widget(no_data_layout)
            self.completed_layout.add_widget(no_data_card)
            return

        sorted_completed = sorted(completed_data, key=lambda x: x['timestamp'], reverse=True)

        summary_card = MDCard(
            size_hint_y=None,
            height=dp(80),
            elevation=3,
            padding=dp(16),
            radius=[12]
        )
        summary_layout = MDBoxLayout(orientation='horizontal', adaptive_height=True)
        total_label = MDLabel(
            text=f"Total Completed: {len(sorted_completed)}",
            theme_text_color="Primary",
            font_style="H6",
            size_hint_x=0.7
        )
        export_button = MDRaisedButton(text="Export", size_hint_x=0.3, on_release=lambda x: self.export_completed())
        summary_layout.add_widget(total_label)
        summary_layout.add_widget(export_button)
        summary_card.add_widget(summary_layout)
        self.completed_layout.add_widget(summary_card)

        for item in sorted_completed:
            self.add_completed_address_card(item)

    def add_completed_address_card(self, item):
        card = MDCard(
            size_hint_y=None,
            height=dp(120) if item['amount'] else dp(100),
            elevation=2,
            padding=dp(16),
            spacing=dp(8),
            radius=[8]
        )
        card_layout = MDBoxLayout(orientation='vertical', spacing=dp(8))

        top_row = MDBoxLayout(orientation='horizontal', size_hint_y=None, height=dp(32), spacing=dp(8))
        address_label = MDLabel(
            text=item['address'],
            theme_text_color="Primary",
            font_style="Body1",
            size_hint_x=0.6,
            halign="left",
            shorten=True,
            shorten_from='right'
        )
        outcome_color = {
            "PIF": [0, 0.7, 0, 1],
            "DA": [0.9, 0.1, 0.1, 1],
            "Completed": [0, 0.5, 0.8, 1]
        }.get(item['outcome'], [0.5, 0.5, 0.5, 1])

        outcome_label = MDLabel(
            text=item['outcome'],
            theme_text_color="Custom",
            text_color=outcome_color,
            font_style="Subtitle2",
            size_hint_x=0.4,
            halign="right",
            bold=True
        )
        top_row.add_widget(address_label)
        top_row.add_widget(outcome_label)

        if item['amount']:
            amount_row = MDBoxLayout(orientation='horizontal', size_hint_y=None, height=dp(24), spacing=dp(8))
            amount_label = MDLabel(
                text=f"Amount: £{item['amount']}",
                theme_text_color="Primary",
                font_style="Caption",
                size_hint_x=0.7,
                halign="left"
            )
            amount_row.add_widget(amount_label)
            amount_row.add_widget(MDLabel(size_hint_x=0.3))

        bottom_row = MDBoxLayout(orientation='horizontal', size_hint_y=None, height=dp(24), spacing=dp(8))
        try:
            dt = datetime.fromisoformat(item['timestamp'])
            time_str = dt.strftime("%m/%d/%Y %I:%M %p")
        except Exception:
            time_str = "Unknown time"
        time_label = MDLabel(
            text=time_str,
            theme_text_color="Secondary",
            font_style="Caption",
            size_hint_x=0.7,
            halign="left"
        )
        bottom_row.add_widget(time_label)

        button_row = MDBoxLayout(orientation='horizontal', size_hint_y=None, height=dp(36), spacing=dp(8))
        navigate_button = MDFlatButton(
            text="Navigate",
            size_hint_x=0.4,
            on_release=lambda x, addr=item['address']: self.navigate_to_address(addr)
        )
        remove_button = MDFlatButton(
            text="Remove",
            size_hint_x=0.3,
            theme_text_color="Error",
            on_release=lambda x, idx=item['index']: self.remove_completed_address(idx)
        )
        spacer = MDLabel(size_hint_x=0.3)
        button_row.add_widget(navigate_button)
        button_row.add_widget(remove_button)
        button_row.add_widget(spacer)

        card_layout.add_widget(top_row)
        if item['amount']:
            card_layout.add_widget(amount_row)
        card_layout.add_widget(bottom_row)
        card_layout.add_widget(button_row)
        card.add_widget(card_layout)
        self.completed_layout.add_widget(card)

    def navigate_to_address(self, address):
        address_screen = self.app_instance.get_address_screen()
        if address_screen:
            address_screen.navigate_to_address(address, -1)

    def remove_completed_address(self, index):
        address_screen = self.app_instance.get_address_screen()
        if address_screen:
            address_screen.remove_from_completed(index)
            self.populate_completed_addresses()
            toast("Address removed from completed list")

    def clear_completed_dialog(self):
        if not hasattr(self, 'clear_dialog'):
            self.clear_dialog = MDDialog(
                title="Clear All Completed",
                text="Are you sure you want to clear all completed addresses? This action cannot be undone.",
                buttons=[
                    MDFlatButton(text="CANCEL", on_release=lambda x: self.clear_dialog.dismiss()),
                    MDFlatButton(text="CLEAR ALL", theme_text_color="Error", on_release=lambda x: self.clear_all_completed()),
                ],
            )
        self.clear_dialog.open()

    def clear_all_completed(self):
        address_screen = self.app_instance.get_address_screen()
        if address_screen:
            address_screen.clear_all_completed()
            self.populate_completed_addresses()
            toast("All completed addresses cleared")
        self.clear_dialog.dismiss()

    def export_completed(self):
        try:
            address_screen = self.app_instance.get_address_screen()
            if not address_screen:
                toast("Unable to access address data")
                return

            completed_data = address_screen.get_completed_addresses_with_timestamps()
            if not completed_data:
                toast("No completed addresses to export")
                return

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"completed_addresses_{timestamp}.csv"

            if platform == 'android' and ANDROID_AVAILABLE:
                try:
                    downloads_path = "/storage/emulated/0/Download"
                    if not os.path.exists(downloads_path):
                        downloads_path = "/sdcard/Download"
                    filepath = os.path.join(downloads_path, filename)
                except Exception:
                    filepath = filename
            else:
                filepath = os.path.join(os.path.expanduser("~"), filename)

            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['address', 'outcome', 'amount', 'completed_date', 'completed_time']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for item in completed_data:
                    try:
                        dt = datetime.fromisoformat(item['timestamp'])
                        date_str = dt.strftime("%Y-%m-%d")
                        time_str = dt.strftime("%H:%M:%S")
                    except Exception:
                        date_str = "Unknown"
                        time_str = "Unknown"
                    writer.writerow({
                        'address': item['address'],
                        'outcome': item['outcome'],
                        'amount': item['amount'] if item['amount'] else '',
                        'completed_date': date_str,
                        'completed_time': time_str
                    })

            toast(f"Exported to: {filename}")

        except Exception as e:
            toast(f"Export failed: {str(e)}")
            print(f"Export error: {e}")


class AddressScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.addresses = []
        self.completed_addresses = set()
        self.completed_timestamps = {}
        self.completed_outcomes = {}
        self.completed_amounts = {}
        self.completion_file = "completed_addresses.json"
        self.file_manager = None
        self.dialog = None

        # SAF helpers
        self.ss = None
        self.chooser = None
        if platform == 'android' and ANDROID_AVAILABLE and ASK_AVAILABLE:
            try:
                self.ss = SharedStorage()
                self.chooser = Chooser(self._on_shared_file_chosen)
            except Exception as e:
                print(f"SharedStorage/Chooser init failed: {e}")
                self.ss = None
                self.chooser = None

        # Request permissions on Android (legacy; SAF doesn't require these)
        if platform == 'android' and ANDROID_AVAILABLE:
            Clock.schedule_once(self.request_android_permissions, 0.5)

        self.load_completed_addresses()

        main_layout = MDBoxLayout(
            orientation='vertical',
            size_hint=(1, 1),
            pos_hint={'center_x': 0.5, 'center_y': 0.5}
        )

        toolbar = MDTopAppBar(
            title="Address Navigator",
            elevation=2,
            size_hint_y=None,
            height=dp(56)
        )
        toolbar.right_action_items = [
            ["folder-open", lambda x: self.open_file_manager()],
            ["check-all", lambda x: self.show_completed_addresses()],
            ["refresh", lambda x: self.refresh_addresses()]
        ]
        main_layout.add_widget(toolbar)

        self.scroll_view = MDScrollView(size_hint=(1, 1))
        self.address_layout = MDBoxLayout(
            orientation='vertical',
            adaptive_height=True,
            spacing=dp(10),
            padding=[dp(16), dp(16), dp(16), dp(16)]
        )
        self.scroll_view.add_widget(self.address_layout)
        main_layout.add_widget(self.scroll_view)
        self.add_widget(main_layout)

        self.init_file_manager()
        self.show_initial_message()

    def show_completed_addresses(self):
        if hasattr(self, 'manager') and self.manager:
            self.manager.current = "completed_screen"
            for screen in self.manager.screens:
                if screen.name == "completed_screen":
                    screen.populate_completed_addresses()
                    break

    def get_completed_addresses_with_timestamps(self):
        result = []
        for index in self.completed_addresses:
            if index < len(self.addresses):
                outcome = self.completed_outcomes.get(index, "Completed")
                amount = self.completed_amounts.get(index, "")
                result.append({
                    'index': index,
                    'address': self.addresses[index],
                    'timestamp': self.completed_timestamps.get(index, datetime.now().isoformat()),
                    'outcome': outcome,
                    'amount': amount
                })
        return result

    def remove_from_completed(self, index):
        if index in self.completed_addresses:
            self.completed_addresses.remove(index)
            self.completed_timestamps.pop(index, None)
            self.completed_outcomes.pop(index, None)
            self.completed_amounts.pop(index, None)
            self.save_completed_addresses()
            if self.addresses:
                self.create_address_buttons()

    def clear_all_completed(self):
        self.completed_addresses.clear()
        self.completed_timestamps.clear()
        self.completed_outcomes.clear()
        self.completed_amounts.clear()
        self.save_completed_addresses()
        if self.addresses:
            self.create_address_buttons()

    def request_android_permissions(self, dt):
        if platform == 'android' and ANDROID_AVAILABLE:
            try:
                request_permissions([Permission.READ_EXTERNAL_STORAGE, Permission.WRITE_EXTERNAL_STORAGE])
            except Exception as e:
                print(f"Permission request failed: {e}")

    def init_file_manager(self):
        try:
            self.file_manager = MDFileManager(exit_manager=self.exit_manager, select_path=self.select_path)
        except Exception as e:
            print(f"Error initializing file manager: {e}")
            self.file_manager = None

    def open_file_manager(self):
        if platform == 'android' and ANDROID_AVAILABLE and ASK_AVAILABLE and self.chooser:
            try:
                self.chooser.choose_content('*/*')
                return
            except Exception as e:
                print(f"Chooser failed, falling back to MDFileManager: {e}")

        if self.file_manager is None:
            toast("File manager not available")
            return
        try:
            if platform == 'android':
                android_paths = [
                    "/storage/emulated/0/Download",
                    "/storage/emulated/0/Documents",
                    "/sdcard/Download",
                    "/sdcard/Documents",
                    "/storage/emulated/0"
                ]
                for path in android_paths:
                    if os.path.exists(path):
                        self.file_manager.show(path)
                        return
                self.file_manager.show("/storage/emulated/0")
            else:
                self.file_manager.show(os.path.expanduser("~"))
        except Exception as e:
            toast(f"Error opening file browser: {str(e)}")
            print(f"File manager error: {e}")

    def _on_shared_file_chosen(self, shared_file_list):
        """SAF callback: copy chosen file into app-private cache then load it."""
        try:
            if not shared_file_list:
                toast("No file selected")
                return
            if not self.ss:
                toast("Storage bridge not available")
                return

            private_path = self.ss.copy_from_shared(shared_file_list[0])
            if not private_path or not os.path.exists(private_path):
                toast("Could not access the selected file")
                return

            lower = private_path.lower()
            if lower.endswith('.csv'):
                self.load_csv_file(private_path)
            elif lower.endswith(('.xlsx', '.xls')):
                if OPENPYXL_AVAILABLE:
                    self.load_xlsx_file(private_path)
                else:
                    toast("Excel support not available. Please use CSV.")
            else:
                toast("Please select a .csv or .xlsx file")

        except Exception as e:
            toast(f"Import failed: {e}")
            print(f"SAF import error: {e}")

    def select_path(self, path):
        """Legacy/desktop handler when MDFileManager is used."""
        try:
            self.exit_manager()
            if path.lower().endswith(('.xlsx', '.xls')):
                if OPENPYXL_AVAILABLE:
                    self.load_xlsx_file(path)
                else:
                    toast("Excel support not available. Please use CSV files.")
            elif path.lower().endswith('.csv'):
                self.load_csv_file(path)
            else:
                if OPENPYXL_AVAILABLE:
                    toast("Please select an Excel file (.xlsx, .xls) or CSV file")
                else:
                    toast("Please select a CSV file")
        except Exception as e:
            toast(f"Error selecting file: {str(e)}")
            print(f"File selection error: {e}")

    def exit_manager(self, *args):
        if self.file_manager:
            self.file_manager.close()

    def load_xlsx_file(self, file_path):
        if not OPENPYXL_AVAILABLE:
            toast("Excel support not available")
            return
        try:
            # FIX: Use data_only=True to avoid style-related errors
            workbook = load_workbook(
                file_path, 
                read_only=True,
                data_only=True  # This prevents style loading issues
            )
            worksheet = workbook.active
            
            # Convert to list immediately to avoid generator issues
            try:
                rows = list(worksheet.rows)
            except Exception as e:
                print(f"Error reading rows: {e}")
                # Fallback: read manually row by row
                rows = []
                for row in worksheet.iter_rows():
                    try:
                        rows.append(row)
                    except:
                        continue
            
            if not rows:
                toast("No data found in the file")
                return

            # Get headers safely
            try:
                headers = []
                for cell in rows[0]:
                    try:
                        value = cell.value
                        headers.append(str(value) if value is not None else "")
                    except:
                        headers.append("")
            except Exception as e:
                print(f"Error reading headers: {e}")
                toast("Error reading file headers")
                return
            
            # Find address column
            address_column_idx = None
            possible_names = ['address', 'Address', 'ADDRESS', 'street', 'Street', 'location', 'Location']
            for i, header in enumerate(headers):
                if header and str(header).strip() in possible_names:
                    address_column_idx = i
                    break
            if address_column_idx is None:
                address_column_idx = 0
                if headers and headers[0]:
                    toast(f"Using column '{headers[0]}' as addresses")

            # Extract addresses safely
            self.addresses = []
            for row_idx, row in enumerate(rows[1:], 1):  # Skip header
                try:
                    if len(row) > address_column_idx:
                        cell = row[address_column_idx]
                        if cell and cell.value:
                            address = str(cell.value).strip()
                            if address and address.lower() != 'none':
                                self.addresses.append(address)
                except Exception as e:
                    print(f"Error reading row {row_idx}: {e}")
                    continue

            # Close workbook properly
            try:
                workbook.close()
            except:
                pass

            if self.addresses:
                self.completed_addresses.clear()
                self.completed_timestamps.clear()
                self.completed_outcomes.clear()
                self.completed_amounts.clear()
                self.save_completed_addresses()
                self.create_address_buttons()
                toast(f"Loaded {len(self.addresses)} addresses")
            else:
                toast("No addresses found in the file")

        except Exception as e:
            error_msg = str(e)
            print(f"Excel loading error: {error_msg}")
            
            # Provide specific error messages
            if "CellStyle" in error_msg or "styles" in error_msg:
                toast("Excel file formatting issue. Try saving as CSV instead.")
            elif "BadZipFile" in error_msg:
                toast("Invalid Excel file format")
            elif "PermissionError" in error_msg:
                toast("Cannot access file - check permissions")
            else:
                toast(f"Error loading Excel file: {error_msg[:50]}")

    def load_csv_file(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as csvfile:
                sample = csvfile.read(1024)
                csvfile.seek(0)
                sniffer = csv.Sniffer()
                delimiter = sniffer.sniff(sample).delimiter

                reader = csv.reader(csvfile, delimiter=delimiter)
                rows = list(reader)
                if not rows:
                    toast("No data found in the file")
                    return

                headers = rows[0]
                address_column_idx = None
                possible_names = ['address', 'Address', 'ADDRESS', 'street', 'Street', 'location', 'Location']
                for i, header in enumerate(headers):
                    if header.strip() in possible_names:
                        address_column_idx = i
                        break
                if address_column_idx is None:
                    address_column_idx = 0
                    toast(f"Using column '{headers[0]}' as addresses")

                self.addresses = []
                for row in rows[1:]:
                    if len(row) > address_column_idx and row[address_column_idx].strip():
                        self.addresses.append(row[address_column_idx].strip())

                if self.addresses:
                    self.completed_addresses.clear()
                    self.completed_timestamps.clear()
                    self.completed_outcomes.clear()
                    self.completed_amounts.clear()
                    self.save_completed_addresses()
                    self.create_address_buttons()
                    toast(f"Loaded {len(self.addresses)} addresses")
                else:
                    toast("No addresses found in the file")

        except Exception as e:
            toast(f"Error loading CSV file: {str(e)}")

    def create_address_buttons(self):
        self.address_layout.clear_widgets()
        for i, address in enumerate(self.addresses):
            card = MDCard(
                size_hint_y=None,
                height=dp(80),
                elevation=2,
                padding=dp(12),
                spacing=dp(8),
                radius=[8]
            )
            card_layout = MDBoxLayout(
                orientation='horizontal',
                spacing=dp(12),
                adaptive_height=True,
                size_hint_y=None,
                height=dp(56)
            )
            
            # FIX: Simplified label without Clock.schedule_once
            address_label = MDLabel(
                text=str(address),
                theme_text_color="Primary",
                size_hint_x=0.6,
                halign="left",
                valign="center",
                markup=False,
                shorten=True,
                shorten_from='right'
            )

            button_layout = MDBoxLayout(orientation='horizontal', size_hint_x=0.4, spacing=dp(8), adaptive_width=False)
            nav_button = MDRaisedButton(
                text="Navigate",
                size_hint=(None, None),
                size=(dp(100), dp(36)),
                on_release=lambda x, addr=address, idx=i: self.navigate_to_address(addr, idx)
            )
            is_completed = i in self.completed_addresses
            complete_button = MDIconButton(
                icon="check-circle" if is_completed else "circle-outline",
                theme_icon_color="Custom",
                icon_color=[0, 0.7, 0, 1] if is_completed else [0.5, 0.5, 0.5, 1],
                size_hint=(None, None),
                size=(dp(40), dp(40)),
                on_release=lambda x, idx=i: self.show_completion_dialog(idx)
            )
            button_layout.add_widget(nav_button)
            button_layout.add_widget(complete_button)

            card_layout.add_widget(address_label)
            card_layout.add_widget(button_layout)
            card.add_widget(card_layout)
            self.address_layout.add_widget(card)

    def navigate_to_address(self, address, index):
        try:
            encoded_address = quote_plus(str(address))
            if platform == 'android' and ANDROID_AVAILABLE:
                try:
                    maps_intent = Intent()
                    maps_intent.setAction(Intent.ACTION_VIEW)
                    maps_uri = Uri.parse(f"geo:0,0?q={encoded_address}")
                    maps_intent.setData(maps_uri)
                    current_activity = cast('android.app.Activity', PythonActivity.mActivity)
                    current_activity.startActivity(maps_intent)
                    toast(f"Opening navigation to: {address[:30]}...")
                except Exception as e:
                    print(f"Android intent failed: {e}")
                    maps_url = f"https://www.google.com/maps/search/{encoded_address}"
                    webbrowser.open(maps_url)
                    toast(f"Opening in browser: {address[:30]}...")
            else:
                maps_url = f"https://www.google.com/maps/search/{encoded_address}"
                webbrowser.open(maps_url)
                toast(f"Opening navigation to: {address[:30]}...")
        except Exception as e:
            toast(f"Error opening maps: {str(e)}")
            try:
                maps_url = f"https://www.google.com/maps/search/{encoded_address}"
                webbrowser.open(maps_url)
                toast("Opened in web browser")
            except Exception:
                toast("Unable to open navigation")

    def show_completion_dialog(self, index):
        if index in self.completed_addresses:
            self.toggle_completion(index, "remove")
            return
        address = self.addresses[index] if index < len(self.addresses) else "Unknown"
        if not hasattr(self, 'completion_dialog') or not self.completion_dialog:
            self.completion_dialog = MDDialog(
                title=f"Mark as Complete",
                text=f"How was this address completed?\n\n{address}",
                buttons=[
                    MDFlatButton(text="CANCEL", on_release=lambda x: self.completion_dialog.dismiss()),
                    MDFlatButton(text="COMPLETED", on_release=lambda x: self.complete_address(index, "Completed", "")),
                    MDFlatButton(text="DA", theme_text_color="Error", on_release=lambda x: self.complete_address(index, "DA", "")),
                    MDFlatButton(text="PIF", theme_text_color="Custom", text_color="green", on_release=lambda x: self.show_payment_dialog(index))
                ],
            )
        else:
            self.completion_dialog.text = f"How was this address completed?\n\n{address}"
            self.completion_dialog.buttons[1].bind(on_release=lambda x: self.complete_address(index, "Completed", ""))
            self.completion_dialog.buttons[2].bind(on_release=lambda x: self.complete_address(index, "DA", ""))
            self.completion_dialog.buttons[3].bind(on_release=lambda x: self.show_payment_dialog(index))
        self.completion_dialog.open()

    def show_payment_dialog(self, index):
        self.completion_dialog.dismiss()
        if not hasattr(self, 'payment_dialog') or not self.payment_dialog:
            self.payment_field = MDTextField(hint_text="Enter amount paid (£)", size_hint_x=None, width=dp(200), input_filter="float")
            content = MDBoxLayout(orientation='vertical', spacing=dp(16), adaptive_height=True)
            content.add_widget(self.payment_field)
            self.payment_dialog = MDDialog(
                title="Payment Amount",
                type="custom",
                content_cls=content,
                buttons=[
                    MDFlatButton(text="CANCEL", on_release=lambda x: self.payment_dialog.dismiss()),
                    MDFlatButton(text="CONFIRM PIF", theme_text_color="Primary", on_release=lambda x: self.confirm_payment(index)),
                ],
            )
        self.payment_field.text = ""
        self.payment_dialog.open()

    def confirm_payment(self, index):
        try:
            amount_text = self.payment_field.text.strip()
            if not amount_text:
                toast("Please enter an amount")
                return
            amount = float(amount_text)
            if amount <= 0:
                toast("Please enter a valid amount")
                return
            self.payment_dialog.dismiss()
            self.complete_address(index, "PIF", f"{amount:.2f}")
        except ValueError:
            toast("Please enter a valid number")

    def complete_address(self, index, outcome, amount):
        if hasattr(self, 'completion_dialog'):
            self.completion_dialog.dismiss()
        self.completed_addresses.add(index)
        self.completed_timestamps[index] = datetime.now().isoformat()
        self.completed_outcomes[index] = outcome
        if amount:
            self.completed_amounts[index] = amount
        self.save_completed_addresses()
        self.create_address_buttons()
        if outcome == "PIF" and amount:
            toast(f"Marked as PIF - £{amount}")
        else:
            toast(f"Marked as {outcome}")

    def toggle_completion(self, index, action="toggle"):
        if action == "remove" or index in self.completed_addresses:
            self.completed_addresses.remove(index)
            self.completed_timestamps.pop(index, None)
            self.completed_outcomes.pop(index, None)
            self.completed_amounts.pop(index, None)
            toast("Marked as incomplete")
        self.save_completed_addresses()
        self.create_address_buttons()

    def save_completed_addresses(self):
        try:
            if platform == 'android' and ANDROID_AVAILABLE:
                try:
                    app_path = PythonActivity.mActivity.getFilesDir().getAbsolutePath()
                    file_path = os.path.join(app_path, self.completion_file)
                except Exception:
                    file_path = self.completion_file
            else:
                file_path = self.completion_file

            data = {
                'completed_addresses': list(self.completed_addresses),
                'completed_timestamps': self.completed_timestamps,
                'completed_outcomes': self.completed_outcomes,
                'completed_amounts': self.completed_amounts
            }
            with open(file_path, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            print(f"Error saving completion data: {e}")

    def load_completed_addresses(self):
        try:
            if platform == 'android' and ANDROID_AVAILABLE:
                try:
                    app_path = PythonActivity.mActivity.getFilesDir().getAbsolutePath()
                    file_path = os.path.join(app_path, self.completion_file)
                except Exception:
                    file_path = self.completion_file
            else:
                file_path = self.completion_file

            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        self.completed_addresses = set(data)
                        self.completed_timestamps = {}
                        self.completed_outcomes = {}
                        self.completed_amounts = {}
                    else:
                        self.completed_addresses = set(data.get('completed_addresses', []))
                        self.completed_timestamps = {int(k): v for k, v in data.get('completed_timestamps', {}).items()}
                        self.completed_outcomes = {int(k): v for k, v in data.get('completed_outcomes', {}).items()}
                        self.completed_amounts = {int(k): v for k, v in data.get('completed_amounts', {}).items()}
        except Exception as e:
            print(f"Error loading completion data: {e}")
            self.completed_addresses = set()
            self.completed_timestamps = {}
            self.completed_outcomes = {}
            self.completed_amounts = {}

    def refresh_addresses(self):
        if self.addresses:
            self.create_address_buttons()
            toast("Address list refreshed")
        else:
            toast("No addresses to refresh. Please load a file first.")

    def show_initial_message(self):
        if not self.addresses:
            welcome_layout = MDBoxLayout(orientation='vertical', adaptive_height=True, spacing=dp(20), padding=dp(20))
            message_card = MDCard(size_hint_y=None, height=dp(200), elevation=3, padding=dp(24), radius=[12])
            message_content = MDBoxLayout(orientation='vertical', adaptive_height=True, spacing=dp(16), size_hint_y=None, height=dp(152))
            title_label = MDLabel(text="Welcome to Address Navigator!", theme_text_color="Primary", font_style="H6", halign="center", size_hint_y=None, height=dp(32))
            instruction_text = "Load an Excel (.xlsx) or CSV file with addresses to get started." if OPENPYXL_AVAILABLE else "Load a CSV file with addresses to get started."
            instruction_label = MDLabel(text=instruction_text, theme_text_color="Secondary", halign="center", size_hint_y=None, height=dp(48))
            load_button = MDRaisedButton(text="Load File", size_hint=(None, None), size=(dp(140), dp(40)), pos_hint={"center_x": 0.5}, on_release=lambda x: self.open_file_manager())
            message_content.add_widget(title_label)
            message_content.add_widget(instruction_label)
            message_content.add_widget(load_button)
            message_card.add_widget(message_content)
            welcome_layout.add_widget(message_card)
            self.address_layout.add_widget(welcome_layout)


class AddressNavigatorApp(MDApp):
    def build(self):
        try:
            self.title = "Address Navigator"
            self.theme_cls.theme_style = "Light"
            self.theme_cls.primary_palette = "Blue"

            self.sm = MDScreenManager()
            self.address_screen = AddressScreen(name="address_screen")
            self.sm.add_widget(self.address_screen)
            self.completed_screen = CompletedAddressesScreen(self, name="completed_screen")
            self.sm.add_widget(self.completed_screen)
            return self.sm
        except Exception as e:
            print(f"Error building app: {e}")
            from kivymd.uix.label import MDLabel
            return MDLabel(text=f"Error starting app: {str(e)}")

    def get_address_screen(self):
        return self.address_screen

    def on_start(self):
        try:
            print("App started successfully")
        except Exception as e:
            print(f"Error on start: {e}")


if __name__ == "__main__":
    AddressNavigatorApp().run()