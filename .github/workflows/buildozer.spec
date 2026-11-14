[app]
title = MiniFootball
package.name = minifootball
package.domain = org.minifootball
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,wav,ogg,mp3
version = 1.0
requirements = python3,kivy
icon.filename = %(source.dir)s/icon.png
orientation = portrait
fullscreen = 0
android.api = 34
android.minapi = 24
android.archs = arm64-v8a, armeabi-v7a
android.accept_sdk_license = True
android.release_artifact = apk

[buildozer]
log_level = 2
warn_on_root = 0
