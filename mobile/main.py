#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Hulink Android 用户面板 (Kivy)，复用 converter.ProxyConverter"""

import os
import threading

from kivy.app import App
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.spinner import Spinner
from kivy.uix.scrollview import ScrollView

from converter import ProxyConverter

OUTPUTS = {
    "Clash Meta YAML": ("convert_to_clash", "clash_config.yaml"),
    "Shadowsocks Base64": ("convert_to_shadowsocks", "shadowsocks_subscription.txt"),
    "V2Ray Base64": ("convert_to_v2ray", "v2ray_subscription.txt"),
    "通用 URI 订阅 Base64": ("convert_to_uri", "universal_subscription.txt"),
}


class Hulink(App):
    def build(self):
        self.converter = ProxyConverter()
        self.nodes = []
        root = BoxLayout(orientation="vertical", padding=8, spacing=6)

        self.url = TextInput(hint_text="订阅链接", multiline=False, size_hint_y=None, height=44)
        self.fetch_btn = Button(text="获取并解析", size_hint_y=None, height=44, on_release=self.fetch)
        self.fmt = Spinner(text=list(OUTPUTS)[0], values=list(OUTPUTS), size_hint_y=None, height=44)
        row = BoxLayout(size_hint_y=None, height=44, spacing=6)
        row.add_widget(Button(text="预览", on_release=self.preview))
        row.add_widget(Button(text="保存", on_release=self.save))
        self.status = Label(text="就绪", size_hint_y=None, height=30)

        sv = ScrollView()
        self.out = Label(text="", size_hint_y=None, halign="left", valign="top")
        self.out.bind(
            width=lambda *_: setattr(self.out, "text_size", (self.out.width, None)),
            texture_size=lambda *_: setattr(self.out, "height", self.out.texture_size[1]),
        )
        sv.add_widget(self.out)

        for w in (self.url, self.fetch_btn, self.fmt, row, self.status, sv):
            root.add_widget(w)
        return root

    def fetch(self, *_):
        url = self.url.text.strip()
        if not url:
            self.status.text = "请输入订阅链接"
            return
        self.fetch_btn.disabled = True
        self.status.text = "正在获取并解析..."
        threading.Thread(target=self._fetch_worker, args=(url,), daemon=True).start()

    def _fetch_worker(self, url):
        try:
            content = self.converter.fetch_subscription(url)
            nodes = self.converter.parse_subscription_content(content)
            Clock.schedule_once(lambda dt: self._fetch_done(nodes, None))
        except Exception as e:
            Clock.schedule_once(lambda dt, e=e: self._fetch_done(None, str(e)))

    def _fetch_done(self, nodes, err):
        self.fetch_btn.disabled = False
        if err:
            self.status.text = "获取失败: " + err
            return
        self.nodes = nodes or []
        self.out.text = "\n".join(
            f"{i}. [{n.get('type')}] {n.get('name')}  {n.get('server')}:{n.get('port')}"
            for i, n in enumerate(self.nodes, 1)
        )
        insecure = any(n.get("skip-cert-verify") for n in self.nodes)
        self.status.text = f"解析到 {len(self.nodes)} 个节点" + ("（含跳过证书校验节点，注意安全）" if insecure else "")

    def _convert(self):
        if not self.nodes:
            self.status.text = "请先获取并解析订阅"
            return None
        method, fname = OUTPUTS[self.fmt.text]
        return getattr(self.converter, method)(self.nodes), fname

    def preview(self, *_):
        r = self._convert()
        if r:
            self.out.text = r[0]

    def save(self, *_):
        r = self._convert()
        if not r:
            return
        content, fname = r
        path = os.path.join(self.user_data_dir, fname)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        self.status.text = "已保存: " + path


if __name__ == "__main__":
    Hulink().run()
