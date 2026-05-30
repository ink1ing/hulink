[app]
title = Hulink
package.name = hulink
package.domain = com.ink1ing
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 0.2.0
# converter.py 为共享核心，构建前由 CI / 手动从仓库根目录复制到本目录
requirements = python3,kivy,requests,pyyaml
orientation = portrait
android.permissions = INTERNET
android.archs = arm64-v8a
android.accept_sdk_license = True
android.allow_backup = True
# 钉住稳定版 p4a（面向 Python 3.11；默认 master 会用 3.14 导致 libffi 构建失败）
p4a.branch = v2024.01.21

[buildozer]
log_level = 2
warn_on_root = 1
