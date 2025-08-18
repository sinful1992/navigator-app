[app]
title = Address Navigator
package.name = addressnavigator
package.domain = org.example
source.dir = .
requirements = python3,kivy==2.1.0,kivymd==1.1.1,openpyxl
source.include_exts = py,png,jpg,kv,atlas,json
entrypoint = main.py
android.permissions = INTERNET,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE
android.api = 33
android.minapi = 21
fullscreen = 0
orientation = portrait
android.archs = arm64-v8a,armeabi-v7a

[buildozer]
log_level = 2

[python-for-android]
p4a.branch = develop
