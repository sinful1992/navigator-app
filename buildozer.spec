[app]
title = Address Navigator
package.name = addressnavigator
package.domain = org.example
version = 1.0.0
requirements = python3,kivy,kivymd,openpyxl
entrypoint = main.py
android.permissions = INTERNET,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE
android.api = 33
android.minapi = 21
android.sdk_build_tools = 30.0.3
android.accept_sdk_license = True
orientation = portrait
android.archs = arm64-v8a,armeabi-v7a

[buildozer]
log_level = 2

[python-for-android]
p4a.branch = develop
