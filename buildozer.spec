[app]
title = Address Navigator
package.name = addressnavigator
package.domain = org.example
source.dir = .
version = 1.0.0
requirements = python3,kivy,kivymd,openpyxl
entrypoint = main.py

# 2025 REQUIREMENTS - Target Android 15 (API 35) for Galaxy S25 compatibility
android.api = 35
android.minapi = 24
android.ndk_api = 24

# Updated permissions for Android 15
android.permissions = INTERNET,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,READ_MEDIA_IMAGES,READ_MEDIA_VIDEO,READ_MEDIA_AUDIO

# Latest build tools
android.build_tools_version = 35.0.0

orientation = portrait
android.archs = arm64-v8a,armeabi-v7a

# Enable modern Android features
android.allow_backup = True
android.backup_rules = True

[buildozer]
log_level = 2

[python-for-android]
p4a.branch = develop
# Use latest NDK recommended for 2025
ndk_version = 26d
