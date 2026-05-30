#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Hulink 图形用户面板（跨平台 Tkinter，复用 main.ProxyConverter）"""

import sys
import io
# windowed 打包后 stdout/stderr 可能为 None，避免 rich 输出崩溃
if sys.stdout is None:
    sys.stdout = io.StringIO()
if sys.stderr is None:
    sys.stderr = io.StringIO()

import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

from converter import ProxyConverter

# 输出格式 -> (ProxyConverter 方法名, 默认文件名)
OUTPUTS = {
    "Clash Meta YAML": ("convert_to_clash", "clash_config.yaml"),
    "Shadowsocks Base64": ("convert_to_shadowsocks", "shadowsocks_subscription.txt"),
    "V2Ray Base64": ("convert_to_v2ray", "v2ray_subscription.txt"),
    "通用 URI 订阅 Base64": ("convert_to_uri", "universal_subscription.txt"),
}


class HulinkGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.converter = ProxyConverter()
        self.nodes = []

        root.title("Hulink - 代理订阅转换工具")
        root.geometry("760x560")

        top = ttk.Frame(root, padding=10)
        top.pack(fill="x")
        ttk.Label(top, text="订阅链接:").pack(side="left")
        self.url = ttk.Entry(top)
        self.url.pack(side="left", fill="x", expand=True, padx=6)
        self.fetch_btn = ttk.Button(top, text="获取并解析", command=self.fetch)
        self.fetch_btn.pack(side="left")

        mid = ttk.Frame(root, padding=(10, 0))
        mid.pack(fill="x")
        ttk.Label(mid, text="输出格式:").pack(side="left")
        self.fmt = ttk.Combobox(mid, values=list(OUTPUTS), state="readonly", width=22)
        self.fmt.current(0)
        self.fmt.pack(side="left", padx=6)
        ttk.Button(mid, text="预览", command=self.preview).pack(side="left")
        ttk.Button(mid, text="转换并保存", command=self.save).pack(side="left", padx=6)

        self.status = ttk.Label(root, text="就绪", padding=(10, 4), foreground="gray")
        self.status.pack(fill="x")
        self.text = scrolledtext.ScrolledText(root, wrap="none")
        self.text.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def set_status(self, msg, color="gray"):
        self.status.config(text=msg, foreground=color)

    # ---- 获取与解析（后台线程，避免阻塞 UI）----
    def fetch(self):
        url = self.url.get().strip()
        if not url:
            messagebox.showwarning("提示", "请输入订阅链接")
            return
        self.fetch_btn.config(state="disabled")
        self.set_status("正在获取并解析...", "blue")
        threading.Thread(target=self._fetch_worker, args=(url,), daemon=True).start()

    def _fetch_worker(self, url):
        try:
            content = self.converter.fetch_subscription(url)
            nodes = self.converter.parse_subscription_content(content)
            self.root.after(0, self._fetch_done, nodes, None)
        except Exception as e:
            self.root.after(0, self._fetch_done, None, str(e))

    def _fetch_done(self, nodes, err):
        self.fetch_btn.config(state="normal")
        if err:
            self.set_status("获取失败", "red")
            messagebox.showerror("错误", err)
            return
        self.nodes = nodes or []
        self.text.delete("1.0", "end")
        for i, n in enumerate(self.nodes, 1):
            self.text.insert("end", f"{i:>3}. [{n.get('type')}] {n.get('name')}  {n.get('server')}:{n.get('port')}\n")
        insecure = any(n.get("skip-cert-verify") for n in self.nodes)
        msg = f"解析到 {len(self.nodes)} 个节点"
        if insecure:
            msg += "（含跳过证书校验节点，请确认来源可信）"
        self.set_status(msg, "orange" if insecure else "green")

    # ---- 转换 ----
    def _convert(self):
        if not self.nodes:
            messagebox.showwarning("提示", "请先获取并解析订阅")
            return None
        method, fname = OUTPUTS[self.fmt.get()]
        return getattr(self.converter, method)(self.nodes), fname

    def preview(self):
        r = self._convert()
        if not r:
            return
        self.text.delete("1.0", "end")
        self.text.insert("end", r[0])
        self.set_status("已生成预览", "green")

    def save(self):
        r = self._convert()
        if not r:
            return
        content, fname = r
        path = filedialog.asksaveasfilename(initialfile=fname)
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            self.set_status(f"已保存: {path}", "green")


def main():
    root = tk.Tk()
    HulinkGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
