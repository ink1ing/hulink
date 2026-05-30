[app]
title = Hulink
package.name = hulink
package.domain = com.ink1ing
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 0.2.0
# converter.py 为共享核心，构建前由 CI / 手动从仓库根目录复制到本目录
requirements = python3,kivy,requests,urllib3,certifi,charset-normalizer,idna,pyyaml
orientation = portrait
android.permissions = INTERNET
android.archs = arm64-v8a,armeabi-v7a
android.allow_backup = True

[buildozer]
log_level = 2
warn_on_root = 1
