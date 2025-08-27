[app]
title = Address Navigator
package.name = addressnavigator
package.domain = org.example

source.dir = .
entrypoint = main.py
version = 1.0.2

# The most likely missing dependencies for MDDatePicker:
# 1. babel - for date/time formatting and localization
# 2. python-dateutil - for date parsing
# 3. pytz - for timezone handling
requirements = python3,kivy==2.3.0,kivymd==1.2.0,androidstorage4kivy,pyjnius,openpyxl==3.1.2,et_xmlfile==1.1.0,babel,python-dateutil,pytz,calendar

# Android targets
android.api = 35
android.minapi = 24
android.ndk_api = 24

# Permissions: SAF gives read access to user-picked files — no broad storage perms needed
android.permissions = INTERNET

# Toolchain pins
android.build_tools_version = 35.0.0
android.enable_androidx = True

# App/device config
orientation = portrait
android.archs = arm64-v8a,armeabi-v7a
bootstrap = sdl2

# Optional branding (uncomment and provide files if you have them)
# icon.filename = %(source.dir)s/icon.png
# presplash.filename = %(source.dir)s/presplash.png

# Backup behavior
android.allow_backup = True

[buildozer]
log_level = 2

[python-for-android]
# Use the develop branch (as you had). The workflow installs NDK r25b for p4a.
p4a.branch = develop
# Align with workflow (or omit this line and let the workflow's NDK win):
ndk_version = 25b
