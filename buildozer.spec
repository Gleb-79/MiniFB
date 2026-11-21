[app]
title = MiniFootball
package.name = minifootball
package.domain = org.minifootball
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,wav,ogg,mp3

# Версия обновления. numeric_version (versionCode) ДОЛЖЕН быть больше, чем у уже
# опубликованной в RuStore сборки. Формат ГГГГММДДНН, при каждой новой сборке увеличивайте.
version = 1.1
android.numeric_version = 2026112201

# Закреплённая версия Kivy, чтобы сборка не ломалась от обновлений зависимостей.
requirements = python3==3.11.5,hostpython3==3.11.5,kivy==2.3.0

icon.filename = %(source.dir)s/icon.png
presplash.filename = %(source.dir)s/presplash.png
android.presplash_color = #167a31

orientation = portrait
fullscreen = 0

# Android 16 (API 36); минимальный Android 7.0 (API 24)
android.api = 36
android.minapi = 24
android.ndk = 28c
android.ndk_api = 24

# Только 64-битная сборка (как в прежних релизах)
android.archs = arm64-v8a

# Игре не нужны разрешения: музыка и настройки хранятся в папке данных приложения
android.permissions =

android.accept_sdk_license = True
android.release_artifact = apk

# Свежий python-for-android: нужен для API 35/36 и выравнивания под страницы памяти 16 КБ
p4a.branch = develop

[buildozer]
log_level = 2
warn_on_root = 0
