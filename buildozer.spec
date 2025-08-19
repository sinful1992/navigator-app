[app]
title = Address Navigator
package.name = addressnavigator
package.domain = org.example
source.dir = .
version = 1.0.0
# Optional but recommended for Play Store uploads:
# 1.0.0 -> 10000000 (choose any consistent scheme)
android.numeric_version = 10000000

# Pin libs for reproducible builds (adjust to your tested versions)
requirements = python3,kivy==2.3.0,kivymd==1.2.0,openpyxl
entrypoint = main.py

# Android API levels
android.api = 35
android.minapi = 24
android.ndk_api = 24

# Modern permissions (Android 13+). Drop legacy READ/WRITE_EXTERNAL_STORAGE.
android.permissions = INTERNET,READ_MEDIA_IMAGES,READ_MEDIA_VIDEO,READ_MEDIA_AUDIO
# If you truly require broad file access on older devices, handle conditionally at runtime.
# For notifications or foreground services, add as needed:
# android.permissions = ...,POST_NOTIFICATIONS,FOREGROUND_SERVICE

# Toolchain pinning
android.build_tools_version = 35.0.0
android.enable_androidx = True

# Packaging / ABI
orientation = portrait
android.archs = arm64-v8a,armeabi-v7a

# Backups
android.allow_backup = True
# Either remove the next line or point it to an actual XML file (e.g., res/xml/backup_rules.xml)
# android.backup_rules = res/xml/backup_rules.xml

[buildozer]
log_level = 2

[python-for-android]
# For day-to-day work, 'develop' is fine. For stable CI, pin a known good tag when ready.
p4a.branch = develop
ndk_version = 26d
