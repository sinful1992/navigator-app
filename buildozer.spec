[app]
title = Address Navigator
package.name = addressnavigator
package.domain = org.example

source.dir = .
entrypoint = main.py
version = 1.0.2

# Enhanced requirements - explicit KivyMD components and dependencies
requirements = python3,kivy==2.3.0,kivymd==1.2.0,androidstorage4kivy,pyjnius,openpyxl==3.1.2,et_xmlfile==1.1.0,python-dateutil,babel,pytz

# Force include KivyMD picker modules
source.include_exts = py,png,jpg,kv,atlas,json
source.include_patterns = assets/*,images/*.png,*.kv

# Android targets
android.api = 35
android.minapi = 24
android.ndk_api = 24

# Enhanced permissions
android.permissions = INTERNET,VIBRATE,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE

# Toolchain pins
android.build_tools_version = 35.0.0
android.enable_androidx = True

# Force include specific modules that might be missing
android.add_compile_options_debug = True
android.gradle_dependencies = androidx.appcompat:appcompat:1.6.1,com.google.android.material:material:1.9.0

# App/device config
orientation = portrait
android.archs = arm64-v8a,armeabi-v7a
bootstrap = sdl2

# Include specific Python modules that might be stripped
android.p4a_whitelist = sqlite3,json,datetime,calendar,dateutil,babel.dates,kivymd.uix.pickers,kivymd.uix.pickers.datepicker

# Ensure all KivyMD assets are included
android.add_src = assets
android.add_aars = 

# Optional branding (uncomment and provide files if you have them)
# icon.filename = %(source.dir)s/icon.png
# presplash.filename = %(source.dir)s/presplash.png

# Backup behavior
android.allow_backup = True

# Add custom Java classes if needed (create java_classes directory)
android.add_java_dir = java_classes

[buildozer]
log_level = 2

# Enhanced debugging
warn_on_root = 1

[python-for-android]
# Use the develop branch (as you had). The workflow installs NDK r25b for p4a.
p4a.branch = develop
# Align with workflow (or omit this line and let the workflow's NDK win):
ndk_version = 25b

# Additional recipe arguments to ensure all dependencies
recipe_args = --with-sqlite3
private_dependencies = kivymd.uix.pickers.datepicker