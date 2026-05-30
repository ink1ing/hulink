#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hulink - 代理节点订阅链接转换工具
支持 Shadowsocks, Clash, V2Ray, Surge 等协议的互相转换
"""

import os
import sys
import json
import base64
import yaml
import requests
from urllib.parse import urlparse, parse_qs, unquote, quote, urlencode
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.text import Text
from rich import print as rprint
from typing import Dict, List, Any, Optional

console = Console()

from converter import ProxyConverter


def show_banner():
    """显示程序横幅"""
    banner = Text()
    banner.append("\n██╗  ██╗██╗   ██╗██╗     ██╗███╗   ██╗██╗  ██╗\n", style="bold blue")
    banner.append("██║  ██║██║   ██║██║     ██║████╗  ██║██║ ██╔╝\n", style="bold blue")
    banner.append("███████║██║   ██║██║     ██║██╔██╗ ██║█████╔╝ \n", style="bold blue")
    banner.append("██╔══██║██║   ██║██║     ██║██║╚██╗██║██╔═██╗ \n", style="bold blue")
    banner.append("██║  ██║╚██████╔╝███████╗██║██║ ╚████║██║  ██╗\n", style="bold blue")
    banner.append("╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝\n", style="bold blue")
    banner.append("\n代理节点订阅链接转换工具\n", style="bold yellow")
    banner.append("支持 Shadowsocks, Clash, V2Ray, Surge 互相转换\n", style="dim")
    
    console.print(Panel(banner, border_style="blue"))

def show_menu():
    """显示主菜单"""
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("选项", style="dim", width=6)
    table.add_column("功能描述")
    
    table.add_row("1", "订阅链接转换")
    table.add_row("2", "测试示例链接")
    table.add_row("3", "查看支持的格式")
    table.add_row("0", "退出程序")
    
    console.print("\n")
    console.print(table)
    console.print("\n")

def show_supported_formats():
    """显示支持的格式"""
    table = Table(show_header=True, header_style="bold green")
    table.add_column("协议类型", style="dim")
    table.add_column("输入格式", style="cyan")
    table.add_column("输出格式", style="yellow")
    table.add_column("状态", style="green")
    
    table.add_row("Shadowsocks", "ss:// URI, Base64", "ss:// URI, Base64, Clash", "✅ 支持")
    table.add_row("VMess", "vmess:// URI, Base64", "vmess:// URI, Base64, Clash", "✅ 支持")
    table.add_row("Clash", "YAML 配置文件", "YAML, ss://, vmess://", "✅ 支持")
    table.add_row("V2Ray", "JSON 配置, vmess://", "vmess://, Clash", "✅ 支持")
    table.add_row("Trojan", "trojan:// URI", "Clash", "✅ 支持")
    table.add_row("VLESS", "vless:// URI", "Clash Meta, 通用URI", "✅ 支持")
    table.add_row("Hysteria2", "hysteria2://, hy2://", "Clash Meta, 通用URI", "✅ 支持")
    table.add_row("TUIC", "tuic:// URI (v5)", "Clash Meta, 通用URI", "✅ 支持")
    table.add_row("ShadowsocksR", "ssr:// URI", "Clash Meta, 通用URI", "✅ 支持")
    table.add_row("Hysteria v1", "hysteria:// URI", "Clash Meta, 通用URI", "✅ 支持")
    table.add_row("AnyTLS", "anytls:// URI", "Clash Meta, 通用URI", "✅ 支持")
    table.add_row("Surge", "配置文件", "Clash", "🚧 开发中")
    
    console.print("\n")
    console.print(Panel(table, title="支持的代理协议格式", border_style="green"))
    console.print("\n")

def convert_subscription():
    """订阅转换功能"""
    converter = ProxyConverter()
    
    # 获取订阅链接
    url = Prompt.ask("\n[bold cyan]请输入订阅链接[/bold cyan]")
    
    if not url.strip():
        console.print("[red]订阅链接不能为空![/red]")
        return
    
    try:
        # 获取订阅内容
        console.print("\n[yellow]正在获取订阅内容...[/yellow]")
        content = converter.fetch_subscription(url)
        
        # 检测格式
        format_type = converter.detect_format(content)
        console.print(f"[green]检测到格式: {format_type}[/green]")
        
        # 解析节点
        console.print("[yellow]正在解析节点信息...[/yellow]")
        nodes = converter.parse_subscription_content(content)
        
        if not nodes:
            console.print("[red]未找到有效的代理节点![/red]")
            return
        
        console.print(f"[green]成功解析 {len(nodes)} 个节点[/green]")
        
        # 显示节点信息
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("序号", width=6)
        table.add_column("节点名称")
        table.add_column("类型")
        table.add_column("服务器")
        table.add_column("端口")
        
        for i, node in enumerate(nodes[:10], 1):  # 只显示前10个
            table.add_row(
                str(i),
                node.get('name', 'Unknown'),
                node.get('type', 'Unknown'),
                node.get('server', 'Unknown'),
                str(node.get('port', 'Unknown'))
            )
        
        if len(nodes) > 10:
            table.add_row("...", f"还有 {len(nodes) - 10} 个节点", "", "", "")
        
        console.print("\n")
        console.print(table)
        console.print("\n")
        
        # 安全提示：存在跳过证书校验的节点
        if any(node.get('skip-cert-verify') for node in nodes):
            console.print("[yellow]⚠️  部分节点开启了跳过证书校验（insecure），存在中间人风险，请确认来源可信。[/yellow]")
        
        # 选择输出格式
        console.print("[bold cyan]请选择输出格式:[/bold cyan]")
        console.print("1. Clash YAML (Clash Meta/mihomo)")
        console.print("2. Shadowsocks Base64")
        console.print("3. V2Ray Base64")
        console.print("4. 通用 URI 订阅 Base64 (全协议)")
        
        choice = Prompt.ask("请输入选项 (1-4)", choices=["1", "2", "3", "4"])
        
        output_content = ""
        output_filename = ""
        
        if choice == "1":
            output_content = converter.convert_to_clash(nodes)
            output_filename = "clash_config.yaml"
        elif choice == "2":
            output_content = converter.convert_to_shadowsocks(nodes)
            output_filename = "shadowsocks_subscription.txt"
        elif choice == "3":
            output_content = converter.convert_to_v2ray(nodes)
            output_filename = "v2ray_subscription.txt"
        elif choice == "4":
            output_content = converter.convert_to_uri(nodes)
            output_filename = "universal_subscription.txt"
        
        # 保存文件
        if Confirm.ask(f"\n是否保存为文件 {output_filename}?"):
            with open(output_filename, 'w', encoding='utf-8') as f:
                f.write(output_content)
            console.print(f"[green]已保存为 {output_filename}[/green]")
        
        # 显示内容预览
        if Confirm.ask("是否显示转换结果预览?"):
            preview = output_content[:500] + "..." if len(output_content) > 500 else output_content
            console.print("\n[bold yellow]转换结果预览:[/bold yellow]")
            console.print(Panel(preview, border_style="yellow"))
    
    except Exception as e:
        console.print(f"[red]转换失败: {str(e)}[/red]")

def test_example_links():
    """测试示例链接"""
    test_urls = [
        "https://fba01.fbsubcn01.cc:2096/flydsubal/1xhwvjcevgcmwimh?clash=1&extend=1",
        "https://feed.iggv5.com/c/500e6566-6f68-42e9-b1c4-a0608d369253"
    ]
    
    console.print("\n[bold cyan]测试示例链接:[/bold cyan]")
    
    for i, url in enumerate(test_urls, 1):
        console.print(f"\n[yellow]测试链接 {i}: {url}[/yellow]")
        
        if Confirm.ask(f"是否测试链接 {i}?"):
            converter = ProxyConverter()
            try:
                content = converter.fetch_subscription(url)
                format_type = converter.detect_format(content)
                nodes = converter.parse_subscription_content(content)
                
                console.print(f"[green]✅ 链接 {i} 测试成功![/green]")
                console.print(f"   格式: {format_type}")
                console.print(f"   节点数量: {len(nodes)}")
                
                if nodes:
                    console.print(f"   示例节点: {nodes[0].get('name', 'Unknown')}")
            
            except Exception as e:
                console.print(f"[red]❌ 链接 {i} 测试失败: {str(e)}[/red]")

def main():
    """主函数"""
    show_banner()
    
    while True:
        show_menu()
        choice = Prompt.ask("请选择功能", choices=["0", "1", "2", "3"])
        
        if choice == "0":
            console.print("\n[bold blue]感谢使用 Hulink! 再见! 👋[/bold blue]")
            break
        elif choice == "1":
            convert_subscription()
        elif choice == "2":
            test_example_links()
        elif choice == "3":
            show_supported_formats()
        
        if choice != "0":
            input("\n按回车键继续...")
            console.clear()
            show_banner()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n\n[bold red]程序被用户中断[/bold red]")
    except Exception as e:
        console.print(f"\n\n[bold red]程序发生错误: {str(e)}[/bold red]")
