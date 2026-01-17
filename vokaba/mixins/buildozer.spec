############################################################
# Buildozer configuration file for "vokaba"
#
# This file describes how your Kivy app is packaged
# for Android (and optionally iOS).
############################################################

[app]

# -------------------------------------------------------------------
# App identity
# -------------------------------------------------------------------

# Title of your application (shown under the icon)
title = Vokaba

# Package name (ONE word, lowercase, ASCII only)
package.name = vokaba

# Package domain (reverse domain notation)
# Choose carefully – this becomes the unique app ID!
# Example: de.vokaba.app
package.domain = de.vokaba


version = 0.0.1
# -------------------------------------------------------------------
# Source configuration
# -------------------------------------------------------------------

# Path to your source directory
# Must contain main.py
source.dir = .

# File extensions to include
# Add anything you need (mp3, json, csv, etc.)
source.include_exts = py,png,jpg,svg,kv,txt,csv,yml,yaml

# Explicitly excluded extensions
source.exclude_exts = spec,pyc,pyo,log

# Directories to exclude entirely
source.exclude_dirs = tests,bin,__pycache__,.git,.venv

# Exclude files matching these patterns
source.exclude_patterns = license,README.md,.gitignore,build_contentfile.sh,Lernkonzept,TODO.txt,build.sh

# Include files even if excluded above
# (does NOT override include/ext rules)
source.include_patterns = assets/*,data/*

# NOTE:
# - Files/folders starting with "." are ALWAYS excluded
# - Files without extension are allowed


# -------------------------------------------------------------------
# Python & dependencies
# -------------------------------------------------------------------

# Python requirements
# Must be either:
# - a python-for-android recipe
# - a pure-python package
#
# Common examples:
# kivy, requests, pillow, sqlite3
requirements = python3,kivy,requests,plyer,filetype,pyyaml

# Python version (default works, but explicit is safer)
python.version = 3.12

# -------------------------------------------------------------------
# Assets
# -------------------------------------------------------------------

# App icon (PNG, 512x512 recommended)
icon.filename = assets/vokaba_logo.png

# Presplash / loading screen (PNG or JPG)
presplash.filename = assets/vokaba_logo.png


# -------------------------------------------------------------------
# App behavior
# -------------------------------------------------------------------

# Supported orientations
# Valid: portrait, landscape, portrait-reverse, landscape-reverse
orientation = landscape

# Fullscreen mode
# 1 = fullscreen (default)
# 0 = show status bar
fullscreen = 1

# Is this a launcher (home screen replacement) app?
home_app = 0

# Display cutout / notch behavior
# Options: never, default, shortEdges
display_cutout = default


# -------------------------------------------------------------------
# Logging
# -------------------------------------------------------------------

# Show logcat output on device
log_level = 2


############################################################
# Android-specific configuration
############################################################
[android]

# Minimum Android API level
android.minapi = 21

# Target Android API level
android.api = 33

# SDK & NDK versions
android.sdk = 24
android.ndk = 25b
android.ndk_api = 21

# Supported CPU architectures
android.archs = arm64-v8a,armeabi-v7a

# Allow internet access?
android.permissions = INTERNET

# Additional Android permissions (examples)
# android.permissions = INTERNET,READ_EXTERNAL_STORAGE

# Gradle dependencies (optional)
# android.gradle_dependencies = androidx.appcompat:appcompat:1.6.1

# Use AndroidX (recommended)
android.enable_androidx = True

# Allow backup via Android system
android.allow_backup = True

# App launch mode
# standard, singleTop, singleTask, singleInstance
android.launch_mode = standard

# App theme (usually no need to change)
android.theme = @android:style/Theme.NoTitleBar

# Show app in recent apps
android.exclude_from_recents = False

# Enable immersive mode
android.immersive = True

# Enable hardware acceleration
android.hardware_accelerated = True

# -------------------------------------------------------------------
# Android build options
# -------------------------------------------------------------------

# Enable debug symbols (bigger APK, better debugging)
android.debuggable = False

# Release keystore (for Play Store)
# android.release_keystore = mykey.keystore
# android.release_keyalias = myalias
# android.release_keystore_passwd = ****
# android.release_keyalias_passwd = ****


############################################################
# iOS (mostly experimental / optional)
############################################################
[ios]

# iOS is not very stable in Buildozer
# Only fill this if you REALLY need it

# ios.kivy_ios_url = https://github.com/kivy/kivy-ios
# ios.codesign.allowed = False


############################################################
# Buildozer behavior
############################################################
[buildozer]

# Log level: 0 (quiet) – 2 (verbose)
log_level = 2

# Warn on configuration issues
warn_on_root = 1
