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
from urllib.parse import urlparse, parse_qs, unquote
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.text import Text
from rich import print as rprint
from typing import Dict, List, Any, Optional

console = Console()

class ProxyConverter:
    """代理协议转换器"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        # 禁用SSL验证以避免证书问题
        self.session.verify = False
        # 禁用SSL警告
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    def fetch_subscription(self, url: str) -> str:
        """获取订阅内容"""
        max_retries = 3
        
        # 尝试不同的请求方法
        methods = [
            # 方法1: 标准请求
            {
                'headers': {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1'
                }
            },
            # 方法2: 模拟订阅客户端
            {
                'headers': {
                    'User-Agent': 'ClashforWindows/0.20.39',
                    'Accept': '*/*',
                    'Accept-Encoding': 'gzip, deflate'
                }
            },
            # 方法3: 模拟移动端
            {
                'headers': {
                    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
                }
            }
        ]
        
        for method_idx, method in enumerate(methods):
            console.print(f"[cyan]尝试方法 {method_idx + 1}: {method['headers']['User-Agent'][:30]}...[/cyan]")
            
            for attempt in range(max_retries):
                try:
                    console.print(f"[dim]  第 {attempt + 1} 次连接...[/dim]")
                    
                    # 创建新的session以避免cookie干扰
                    session = requests.Session()
                    session.headers.update(method['headers'])
                    session.verify = False
                    
                    response = session.get(
                        url, 
                        timeout=60,
                        allow_redirects=True,
                        stream=False
                    )
                    
                    console.print(f"[dim]  响应状态码: {response.status_code}[/dim]")
                    console.print(f"[dim]  响应头: {dict(list(response.headers.items())[:3])}[/dim]")
                    
                    response.raise_for_status()
                    
                    # 检查响应内容
                    if not response.text.strip():
                        raise Exception("响应内容为空")
                    
                    console.print(f"[green]✅ 成功获取内容，长度: {len(response.text)} 字符[/green]")
                    return response.text
                    
                except requests.exceptions.Timeout:
                    console.print(f"[yellow]  第 {attempt + 1} 次尝试超时[/yellow]")
                    if attempt == max_retries - 1:
                        continue  # 尝试下一个方法
                except requests.exceptions.ConnectionError as e:
                    console.print(f"[yellow]  第 {attempt + 1} 次连接失败: {str(e)[:50]}...[/yellow]")
                    if attempt == max_retries - 1:
                        continue  # 尝试下一个方法
                except requests.exceptions.HTTPError as e:
                    console.print(f"[yellow]  HTTP错误 ({e.response.status_code}): {str(e)[:50]}...[/yellow]")
                    if e.response.status_code in [404, 403, 500, 502, 503]:
                        if attempt == max_retries - 1:
                            continue  # 尝试下一个方法
                    else:
                        raise Exception(f"HTTP错误 ({e.response.status_code}): {str(e)}")
                except Exception as e:
                    console.print(f"[yellow]  第 {attempt + 1} 次尝试失败: {str(e)[:50]}...[/yellow]")
                    if attempt == max_retries - 1:
                        continue  # 尝试下一个方法
                
                # 等待后重试
                if attempt < max_retries - 1:
                    import time
                    time.sleep(1)
        
        # 所有方法都失败了
        raise Exception("所有请求方法都失败，无法获取订阅内容")
    
    def detect_format(self, content: str) -> str:
        """检测订阅格式"""
        content = content.strip()
        
        # 检测 Clash YAML 格式 - 更全面的检测
        clash_indicators = [
            'proxies:', 'proxy-groups:', 'rules:', 'port:', 'socks-port:',
            'allow-lan:', 'mode:', 'log-level:', 'external-controller:',
            '- name:', '- type:', '- server:', '- port:'
        ]
        if any(indicator in content for indicator in clash_indicators):
            try:
                # 尝试解析YAML来确认
                yaml.safe_load(content)
                return 'clash'
            except:
                pass
        
        # 检测 V2Ray JSON 格式
        try:
            data = json.loads(content)
            if 'outbounds' in data or 'inbounds' in data:
                return 'v2ray'
        except:
            pass
        
        # 检测原始URI格式（优先检测）
        lines = content.strip().split('\n')
        if lines:
            first_line = lines[0].strip()
            if first_line.startswith('ss://'):
                return 'shadowsocks'
            elif first_line.startswith('vmess://'):
                return 'v2ray_uri'
            elif first_line.startswith('trojan://'):
                return 'trojan'
        
        # 检测 Base64 编码的内容
        try:
            # 检查是否为有效的Base64
            if len(content) % 4 == 0 and all(c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=' for c in content):
                decoded = base64.b64decode(content).decode('utf-8')
                lines = decoded.strip().split('\n')
                if lines:
                    first_line = lines[0].strip()
                    if first_line.startswith('ss://'):
                        return 'shadowsocks'
                    elif first_line.startswith('vmess://'):
                        return 'v2ray_uri'
                    elif first_line.startswith('trojan://'):
                        return 'trojan'
        except:
            pass
        
        return 'unknown'
    
    def parse_shadowsocks_uri(self, uri: str) -> Dict[str, Any]:
        """解析 Shadowsocks URI"""
        try:
            # ss://method:password@server:port#name
            if uri.startswith('ss://'):
                uri = uri[5:]  # 移除 ss://
                
                # 分离名称
                if '#' in uri:
                    uri, name = uri.split('#', 1)
                    name = unquote(name)
                else:
                    name = 'Shadowsocks Node'
                
                # 解码base64或直接解析
                try:
                    decoded = base64.b64decode(uri).decode('utf-8')
                    uri = decoded
                except:
                    pass
                
                # 解析 method:password@server:port
                if '@' in uri:
                    auth_part, server_part = uri.split('@', 1)
                    method, password = auth_part.split(':', 1)
                    server, port = server_part.split(':', 1)
                    
                    return {
                        'name': name,
                        'type': 'ss',
                        'server': server,
                        'port': int(port),
                        'cipher': method,
                        'password': password
                    }
        except Exception as e:
            console.print(f"[red]解析 Shadowsocks URI 失败: {e}[/red]")
        return None
    
    def parse_vmess_uri(self, uri: str) -> Dict[str, Any]:
        """解析 VMess URI"""
        try:
            if uri.startswith('vmess://'):
                encoded = uri[8:]  # 移除 vmess://
                decoded = base64.b64decode(encoded).decode('utf-8')
                config = json.loads(decoded)
                
                return {
                    'name': config.get('ps', 'VMess Node'),
                    'type': 'vmess',
                    'server': config.get('add'),
                    'port': int(config.get('port', 443)),
                    'uuid': config.get('id'),
                    'alterId': int(config.get('aid', 0)),
                    'cipher': config.get('scy', 'auto'),
                    'network': config.get('net', 'tcp'),
                    'tls': config.get('tls') == 'tls',
                    'path': config.get('path', ''),
                    'host': config.get('host', '')
                }
        except Exception as e:
            console.print(f"[red]解析 VMess URI 失败: {e}[/red]")
        return None
    
    def parse_subscription_content(self, content: str) -> List[Dict[str, Any]]:
        """解析订阅内容"""
        format_type = self.detect_format(content)
        nodes = []
        
        console.print(f"[cyan]检测到格式: {format_type}[/cyan]")
        console.print(f"[dim]内容长度: {len(content)} 字符[/dim]")
        
        if format_type == 'clash':
            try:
                data = yaml.safe_load(content)
                console.print(f"[green]成功解析YAML，键: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}[/green]")
                
                if isinstance(data, dict) and 'proxies' in data:
                    nodes = data['proxies']
                    console.print(f"[green]找到 {len(nodes)} 个代理节点[/green]")
                elif isinstance(data, dict):
                    # 尝试其他可能的键名
                    for key in ['proxy', 'Proxy', 'servers', 'nodes']:
                        if key in data:
                            nodes = data[key]
                            console.print(f"[green]在键 '{key}' 中找到 {len(nodes)} 个节点[/green]")
                            break
                    
                    if not nodes:
                        console.print(f"[yellow]未找到代理节点，可用键: {list(data.keys())}[/yellow]")
                        # 如果数据本身就是节点列表
                        if isinstance(data, list):
                            nodes = data
                            console.print(f"[green]内容本身是节点列表，包含 {len(nodes)} 个节点[/green]")
                
            except Exception as e:
                console.print(f"[red]解析 Clash 配置失败: {e}[/red]")
                # 尝试作为纯文本处理
                console.print("[yellow]尝试作为纯文本URI处理...[/yellow]")
                format_type = 'text_uri'
        
        if format_type in ['shadowsocks', 'v2ray_uri', 'trojan', 'text_uri', 'unknown']:
            # 首先尝试Base64解码
            original_content = content
            try:
                if len(content) % 4 == 0 and all(c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=' for c in content.replace('\n', '').replace('\r', '')):
                    decoded = base64.b64decode(content).decode('utf-8')
                    console.print(f"[green]成功Base64解码，解码后长度: {len(decoded)}[/green]")
                    content = decoded
            except Exception as e:
                console.print(f"[yellow]Base64解码失败，使用原始内容: {e}[/yellow]")
                content = original_content
            
            lines = content.strip().split('\n')
            console.print(f"[cyan]处理 {len(lines)} 行内容[/cyan]")
            
            for i, line in enumerate(lines):
                line = line.strip()
                if not line:
                    continue
                
                console.print(f"[dim]处理第 {i+1} 行: {line[:50]}...[/dim]")
                
                if line.startswith('ss://'):
                    node = self.parse_shadowsocks_uri(line)
                    if node:
                        nodes.append(node)
                        console.print(f"[green]✅ 解析SS节点: {node.get('name', 'Unknown')}[/green]")
                elif line.startswith('vmess://'):
                    node = self.parse_vmess_uri(line)
                    if node:
                        nodes.append(node)
                        console.print(f"[green]✅ 解析VMess节点: {node.get('name', 'Unknown')}[/green]")
                elif line.startswith('trojan://'):
                    console.print(f"[yellow]发现Trojan节点但暂不支持解析[/yellow]")
        
        console.print(f"[bold green]总共解析到 {len(nodes)} 个有效节点[/bold green]")
        return nodes
    
    def convert_to_clash(self, nodes: List[Dict[str, Any]]) -> str:
        """转换为 Clash 格式"""
        clash_config = {
            'port': 7890,
            'socks-port': 7891,
            'allow-lan': False,
            'mode': 'rule',
            'log-level': 'info',
            'external-controller': '127.0.0.1:9090',
            'proxies': [],
            'proxy-groups': [
                {
                    'name': '🚀 节点选择',
                    'type': 'select',
                    'proxies': ['♻️ 自动选择', 'DIRECT']
                },
                {
                    'name': '♻️ 自动选择',
                    'type': 'url-test',
                    'proxies': [],
                    'url': 'http://www.gstatic.com/generate_204',
                    'interval': 300
                }
            ],
            'rules': [
                'DOMAIN-SUFFIX,local,DIRECT',
                'IP-CIDR,127.0.0.0/8,DIRECT',
                'IP-CIDR,172.16.0.0/12,DIRECT',
                'IP-CIDR,192.168.0.0/16,DIRECT',
                'IP-CIDR,10.0.0.0/8,DIRECT',
                'GEOIP,CN,DIRECT',
                'MATCH,🚀 节点选择'
            ]
        }
        
        for node in nodes:
            if node['type'] == 'ss':
                clash_node = {
                    'name': node['name'],
                    'type': 'ss',
                    'server': node['server'],
                    'port': node['port'],
                    'cipher': node['cipher'],
                    'password': node['password']
                }
                clash_config['proxies'].append(clash_node)
                clash_config['proxy-groups'][0]['proxies'].append(node['name'])
                clash_config['proxy-groups'][1]['proxies'].append(node['name'])
            
            elif node['type'] == 'vmess':
                clash_node = {
                    'name': node['name'],
                    'type': 'vmess',
                    'server': node['server'],
                    'port': node['port'],
                    'uuid': node['uuid'],
                    'alterId': node['alterId'],
                    'cipher': node['cipher'],
                    'network': node['network']
                }
                
                if node.get('tls'):
                    clash_node['tls'] = True
                if node.get('path'):
                    clash_node['ws-path'] = node['path']
                if node.get('host'):
                    clash_node['ws-headers'] = {'Host': node['host']}
                
                clash_config['proxies'].append(clash_node)
                clash_config['proxy-groups'][0]['proxies'].append(node['name'])
                clash_config['proxy-groups'][1]['proxies'].append(node['name'])
        
        return yaml.dump(clash_config, default_flow_style=False, allow_unicode=True)
    
    def convert_to_shadowsocks(self, nodes: List[Dict[str, Any]]) -> str:
        """转换为 Shadowsocks URI 格式"""
        uris = []
        for node in nodes:
            if node['type'] == 'ss':
                # ss://method:password@server:port#name
                auth = f"{node['cipher']}:{node['password']}"
                auth_b64 = base64.b64encode(auth.encode()).decode()
                uri = f"ss://{auth_b64}@{node['server']}:{node['port']}#{node['name']}"
                uris.append(uri)
        
        return base64.b64encode('\n'.join(uris).encode()).decode()
    
    def convert_to_v2ray(self, nodes: List[Dict[str, Any]]) -> str:
        """转换为 V2Ray 订阅格式"""
        uris = []
        for node in nodes:
            if node['type'] == 'vmess':
                config = {
                    'v': '2',
                    'ps': node['name'],
                    'add': node['server'],
                    'port': str(node['port']),
                    'id': node['uuid'],
                    'aid': str(node['alterId']),
                    'scy': node['cipher'],
                    'net': node['network'],
                    'type': 'none',
                    'host': node.get('host', ''),
                    'path': node.get('path', ''),
                    'tls': 'tls' if node.get('tls') else ''
                }
                config_json = json.dumps(config)
                config_b64 = base64.b64encode(config_json.encode()).decode()
                uri = f"vmess://{config_b64}"
                uris.append(uri)
        
        return base64.b64encode('\n'.join(uris).encode()).decode()

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
    table.add_row("Trojan", "trojan:// URI", "Clash", "🚧 开发中")
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
        
        # 选择输出格式
        console.print("[bold cyan]请选择输出格式:[/bold cyan]")
        console.print("1. Clash YAML")
        console.print("2. Shadowsocks Base64")
        console.print("3. V2Ray Base64")
        
        choice = Prompt.ask("请输入选项 (1-3)", choices=["1", "2", "3"])
        
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
