[app]
title = Address Navigator
package.name = addressnavigator
package.domain = org.example

source.dir = .
version = 1.0.1
entrypoint = main.py

# Minimal requirements to avoid dependency conflicts
# Remove openpyxl temporarily if it continues causing issues
# buildozer.spec
requirements = python3,kivy==2.3.0,kivymd==1.2.0,androidstorage4kivy,pyjnius,openpyxl==3.1.2,et_xmlfile==1.1.0

# Alternative: Include openpyxl with data_only fix
# requirements = python3,kivy==2.3.0,kivymd==1.2.0,androidstorage4kivy,openpyxl==3.0.10

android.api = 35
android.minapi = 24
android.ndk_api = 24

# Minimal permissions - SAF handles file access without broad storage permissions
android.permissions = INTERNET

android.build_tools_version = 35.0.0
android.gradle_version = 8.4
android.enable_androidx = True

orientation = portrait
android.archs = arm64-v8a,armeabi-v7a

android.allow_backup = True
android.adaptive_icon = True

# Build optimizations
android.java_options = -Xmx4g
android.gradle_options = --daemon --parallel --configure-on-demand

bootstrap = sdl2

# Icon paths (create these files)
# icon.filename = %(source.dir)s/icon.png
# presplash.filename = %(source.dir)s/presplash.png

[buildozer]
log_level = 2

[python-for-android]
p4a.branch = develop
ndk_version = 26d
p4a.bootstrap = sdl2
p4a.arch = arm64-v8a