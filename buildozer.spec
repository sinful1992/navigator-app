[app]

# (str) Title of your application
title = MyKivyApp

# (str) Package name
package.name = mykivyapp

# (str) Package domain (unique identifier)
package.domain = com.example

# (str) Source code directory (default: ".")
source.dir = .

# (list) Application requirements (comma-separated)
# Avoid adding build-time tools like "buildozer" or "python-for-android" 
# unless your app actually imports them at runtime.
requirements = python3,kivy,kivymd,pandas,openpyxl,xlrd
source.include_exts = py,kv,png,jpg,ttf,atlas,json

# (str) The entry point of your application (the main Python file)
entrypoint = main.py

# (list) Permissions required by the application (e.g. INTERNET, ACCESS_FINE_LOCATION)
# Leave empty if not needed.
android.permissions = INTERNET, READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE

# (int) Android API to target. 33 is currently stable for Android 13.
android.api = 33

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


# ------------------------------------------------------------------------------
# Below are optional or advanced config sections. Uncomment/edit as needed.
# ------------------------------------------------------------------------------


#[app]

# (list) Presplash of the application
#presplash.filename = %(source.dir)s/data/presplash.png

# (float) The aspect ratio used for the presplash, default is 1
#presplash.ratio = 1

# (list) Custom java compile options, such as source and target versions
#android.compile_options = source=11,target=11

# (list) Gradle dependencies to add
#android.gradle_dependencies = com.google.firebase:firebase-crashlytics:17.2.1

# (str) The filename for the splash screen used by aab
#android.screen_svga = some_animation.svga

# (bool) Use the new android crasher style for debugging
#android.debug_observed_crashes = False


#[buildozer]

# (int) Log level (0 = error only, 1 = warning, 2 = info, 3 = debug)
#log_level = 2

# (str) Path to where the log file is stored
#log_file = /tmp/buildozer.log

# (bool) Warn when running as root
#warn_on_root = 1


#[python-for-android]

# (str) extra commandline options to pass to p4a
#extra_args =
p4a.branch = develop


#[app]

# (str) A custom build directory (instead of .buildozer)
#build_dir = ./my_buildozer_dir


#[translations]

# (list) List of resource files with translations
# Only necessary if you have i18n strings for multiple languages
#po_files =


#[Global]

# (bool) Turn off automatic service addition
#service = False


#[internal]

# DO NOT MODIFY: Path used internally by buildozer
#package.domain.replace = -
