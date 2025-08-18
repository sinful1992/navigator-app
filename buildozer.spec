[app]
# (str) Title of your application
title = MyKivyApp
# (str) Package name
package.name = mykivyapp
# (str) Package domain (unique identifier)
package.domain = com.example
# (str) Source code directory (default: ".")
source.dir = .
# (list) Application requirements (comma-separated) - LIGHTER VERSION
requirements = python3,kivy,kivymd,openpyxl
source.include_exts = py,kv,png,jpg,ttf,atlas,json
# (str) The entry point of your application (the main Python file)
entrypoint = main.py
# (list) Permissions required by the application
android.permissions = INTERNET, READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE
# (int) Android API to target. 33 is currently stable for Android 13.
android.api = 33
# (int) Minimum API - can stay at 21 without pandas!
android.minapi = 21
# (bool) Enable fullscreen mode
fullscreen = 0
# (str) Supported orientation: "portrait", "landscape", or "sensor"
orientation = portrait
# (str) Application version
version = 1.0.0
# (str) Application icon
#icon.filename = icon.png
# (str) Supported package formats: "apk" (for testing/sideload) or "aab" (Play Store)
android.package_format = apk
# (bool) Whether to enable debug mode and debug logging in the app
debug = True
# (str) Build mode: "debug" (testing) or "release" (production)
android.build_mode = debug
# (list) Target architectures
android.archs = arm64-v8a, armeabi-v7a
# (bool) Enable verbose log output
log.enable = True
# (bool) Automatically accept Android SDK licenses
android.accept_sdk_license = True
# Use NDK r26d for compatibility
android.ndk = 26d
# ------------------------------------------------------------------------------
# Below are optional or advanced config sections. Uncomment/edit as needed.
# ------------------------------------------------------------------------------
#[buildozer]
# (int) Log level (0 = error only, 1 = warning, 2 = info, 3 = debug)
#log_level = 2
# (str) Path to where the log file is stored
#log_file = /tmp/buildozer.log
# (bool) Warn when running as root
#warn_on_root = 1
#[python-for-android]
# (str) extra commandline options to pass to p4a
p4a.branch = develop
