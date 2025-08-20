[app]
title = Address Navigator
package.name = addressnavigator
package.domain = org.example
source.dir = .
version = 1.0.0
entrypoint = main.py

# Pin libs for reproducible builds (optional but recommended)
requirements = python3,kivy==2.3.0,kivymd==1.2.0,androidstorage4kivy,openpyxl==3.1.2,et_xmlfile==1.1.0

# Android API levels
android.api = 35
android.minapi = 24
android.ndk_api = 24

# Modern permissions (Android 13+)
# (SAF does not require READ/WRITE_EXTERNAL_STORAGE)
android.permissions = INTERNET,READ_MEDIA_IMAGES,READ_MEDIA_VIDEO,READ_MEDIA_AUDIO

# Toolchain pinning / AndroidX
android.build_tools_version = 35.0.0
android.enable_androidx = True

orientation = portrait
android.archs = arm64-v8a,armeabi-v7a
android.allow_backup = True
# If you actually use backup rules, point to a file:
# android.backup_rules = res/xml/backup_rules.xml

[buildozer]
log_level = 2

[python-for-android]
p4a.branch = develop
ndk_version = 26d