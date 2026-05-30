# -*- coding: utf-8 -*-
"""Hulink 核心转换逻辑（不强依赖 rich，可用于桌面 CLI/GUI 与移动端复用）"""
import sys
import json
import base64
import re as _re
import yaml
import requests
from urllib.parse import urlparse, parse_qs, unquote, quote, urlencode
from typing import Dict, List, Any, Optional


class _PlainConsole:
    """无 rich 环境（如 Android）下的降级输出：去除富文本标记后打印"""
    def print(self, *args, **kwargs):
        try:
            msg = " ".join(str(a) for a in args)
            sys.stdout.write(_re.sub(r"\[/?[^\]]*\]", "", msg) + "\n")
        except Exception:
            pass

    def clear(self):
        pass


try:
    from rich.console import Console
    console = Console()
except Exception:
    console = _PlainConsole()


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
        # 默认启用SSL证书验证，仅在证书校验失败时按需回退（见 fetch_subscription）
        self.session.verify = True
        # 预先静默回退场景下的 InsecureRequestWarning
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
                    # 创建新的session以避免cookie干扰
                    session = requests.Session()
                    session.headers.update(method['headers'])

                    try:
                        response = session.get(url, timeout=60, allow_redirects=True)
                    except requests.exceptions.SSLError:
                        console.print("[yellow]  SSL 证书验证失败，将以不验证证书的方式重试（请确认链接来源可信）[/yellow]")
                        response = session.get(url, timeout=60, allow_redirects=True, verify=False)

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
    
    def _uri_scheme_format(self, line: str) -> Optional[str]:
        """根据 URI 前缀判断协议格式"""
        line = line.strip()
        for prefix, fmt in (
            ('ssr://', 'ssr'), ('ss://', 'shadowsocks'), ('vmess://', 'v2ray_uri'),
            ('trojan://', 'trojan'), ('vless://', 'vless'),
            ('hysteria2://', 'hysteria2'), ('hy2://', 'hysteria2'), ('hysteria://', 'hysteria'),
            ('tuic://', 'tuic'), ('anytls://', 'anytls'),
        ):
            if line.startswith(prefix):
                return fmt
        return None
    
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
            fmt = self._uri_scheme_format(lines[0])
            if fmt:
                return fmt
        
        # 检测 Base64 编码的内容
        try:
            # 检查是否为有效的Base64
            if len(content) % 4 == 0 and all(c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=' for c in content):
                decoded = base64.b64decode(content).decode('utf-8')
                lines = decoded.strip().split('\n')
                if lines:
                    fmt = self._uri_scheme_format(lines[0])
                    if fmt:
                        return fmt
        except:
            pass
        
        return 'unknown'
    
    def parse_shadowsocks_uri(self, uri: str) -> Dict[str, Any]:
        """解析 Shadowsocks URI（兼容 SIP002 与旧版整体 Base64 格式）"""
        try:
            if not uri.startswith('ss://'):
                return None
            body = uri[5:]

            # 分离节点名称
            name = 'Shadowsocks Node'
            if '#' in body:
                body, fragment = body.split('#', 1)
                name = unquote(fragment)

            # 分离 SIP002 query 参数（如 plugin）
            plugin = ''
            if '?' in body:
                body, query = body.split('?', 1)
                plugin = unquote(parse_qs(query).get('plugin', [''])[0])

            def b64decode(s: str) -> str:
                s = s.strip()
                return base64.urlsafe_b64decode(s + '=' * (-len(s) % 4)).decode('utf-8')

            if '@' in body:
                # SIP002 / 明文：userinfo@server:port，userinfo 可能为 Base64
                auth_part, server_part = body.rsplit('@', 1)
                try:
                    auth_part = b64decode(auth_part)
                except Exception:
                    pass  # 已是明文 method:password
            else:
                # 旧版：整体 Base64 编码 method:password@server:port
                auth_part, server_part = b64decode(body).rsplit('@', 1)

            method, password = auth_part.split(':', 1)
            server, port = server_part.rsplit(':', 1)

            node = {
                'name': name,
                'type': 'ss',
                'server': server,
                'port': int(port),
                'cipher': method,
                'password': password
            }
            if plugin:
                node['plugin'] = plugin
            return node
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
    
    def parse_trojan_uri(self, uri: str) -> Dict[str, Any]:
        """解析 Trojan URI: trojan://password@server:port?sni=xxx&allowInsecure=1#name"""
        try:
            if uri.startswith('trojan://'):
                parsed = urlparse(uri)
                query = parse_qs(parsed.query)
                return {
                    'name': unquote(parsed.fragment) if parsed.fragment else 'Trojan Node',
                    'type': 'trojan',
                    'server': parsed.hostname,
                    'port': parsed.port or 443,
                    'password': unquote(parsed.username or ''),
                    'sni': query.get('sni', query.get('peer', ['']))[0],
                    'skip-cert-verify': query.get('allowInsecure', ['0'])[0] in ('1', 'true')
                }
        except Exception as e:
            console.print(f"[red]解析 Trojan URI 失败: {e}[/red]")
        return None
    
    def parse_vless_uri(self, uri: str) -> Dict[str, Any]:
        """解析 VLESS URI: vless://uuid@server:port?security=tls&type=ws&sni=...#name"""
        try:
            if uri.startswith('vless://'):
                p = urlparse(uri)
                q = parse_qs(p.query)
                g = lambda k, d='': q.get(k, [d])[0]
                return {
                    'name': unquote(p.fragment) if p.fragment else 'VLESS Node',
                    'type': 'vless',
                    'server': p.hostname,
                    'port': p.port or 443,
                    'uuid': p.username,
                    'network': g('type', 'tcp'),
                    'security': g('security', 'none'),  # tls / reality / none
                    'sni': g('sni') or g('host'),
                    'flow': g('flow'),
                    'path': unquote(g('path')),
                    'host': g('host'),
                    'pbk': g('pbk'),  # reality 公钥
                    'sid': g('sid'),  # reality short id
                    'fp': g('fp')     # 指纹
                }
        except Exception as e:
            console.print(f"[red]解析 VLESS URI 失败: {e}[/red]")
        return None
    
    def parse_hysteria2_uri(self, uri: str) -> Dict[str, Any]:
        """解析 Hysteria2 URI: hysteria2://auth@host:port/?sni=&obfs=&insecure=1#name"""
        try:
            if uri.startswith(('hysteria2://', 'hy2://')):
                p = urlparse(uri)
                q = parse_qs(p.query)
                g = lambda k, d='': q.get(k, [d])[0]
                auth = p.username or ''
                if p.password is not None:
                    auth = f"{auth}:{p.password}"
                return {
                    'name': unquote(p.fragment) if p.fragment else 'Hysteria2 Node',
                    'type': 'hysteria2',
                    'server': p.hostname,
                    'port': p.port or 443,
                    'password': unquote(auth),
                    'sni': g('sni'),
                    'obfs': g('obfs'),
                    'obfs-password': g('obfs-password'),
                    'skip-cert-verify': g('insecure', '0') in ('1', 'true')
                }
        except Exception as e:
            console.print(f"[red]解析 Hysteria2 URI 失败: {e}[/red]")
        return None
    
    def parse_tuic_uri(self, uri: str) -> Dict[str, Any]:
        """解析 TUIC v5 URI: tuic://uuid:password@host:port?sni=&alpn=&congestion_control=#name"""
        try:
            if uri.startswith('tuic://'):
                p = urlparse(uri)
                q = parse_qs(p.query)
                g = lambda k, d='': q.get(k, [d])[0]
                return {
                    'name': unquote(p.fragment) if p.fragment else 'TUIC Node',
                    'type': 'tuic',
                    'server': p.hostname,
                    'port': p.port or 443,
                    'uuid': unquote(p.username or ''),
                    'password': unquote(p.password or ''),
                    'sni': g('sni'),
                    'alpn': g('alpn'),
                    'congestion-controller': g('congestion_control', 'bbr'),
                    'udp-relay-mode': g('udp_relay_mode', 'native'),
                    'skip-cert-verify': g('allow_insecure', '0') in ('1', 'true')
                }
        except Exception as e:
            console.print(f"[red]解析 TUIC URI 失败: {e}[/red]")
        return None
    
    def parse_ssr_uri(self, uri: str) -> Dict[str, Any]:
        """解析 ShadowsocksR URI: ssr://b64(host:port:protocol:method:obfs:b64pass/?params)"""
        try:
            if uri.startswith('ssr://'):
                def b64(s: str) -> str:
                    s = s.strip().replace('\n', '').replace('\r', '')
                    return base64.urlsafe_b64decode(s + '=' * (-len(s) % 4)).decode('utf-8')
                main, _, query = b64(uri[6:]).partition('/?')
                parts = main.split(':')
                if len(parts) < 6:
                    return None
                q = parse_qs(query)
                g = lambda k, d='': b64(q[k][0]) if q.get(k, [''])[0] else d
                return {
                    'name': g('remarks', 'SSR Node'),
                    'type': 'ssr',
                    'server': parts[0],
                    'port': int(parts[1]),
                    'protocol': parts[2],
                    'cipher': parts[3],
                    'obfs': parts[4],
                    'password': b64(parts[5]),
                    'protocol-param': g('protoparam') or g('protocolparam'),
                    'obfs-param': g('obfsparam')
                }
        except Exception as e:
            console.print(f"[red]解析 SSR URI 失败: {e}[/red]")
        return None
    
    def parse_hysteria_uri(self, uri: str) -> Dict[str, Any]:
        """解析 Hysteria v1 URI: hysteria://host:port?auth=&peer=&upmbps=&downmbps=#name"""
        try:
            if uri.startswith('hysteria://'):
                p = urlparse(uri)
                q = parse_qs(p.query)
                g = lambda k, d='': q.get(k, [d])[0]
                return {
                    'name': unquote(p.fragment) if p.fragment else 'Hysteria Node',
                    'type': 'hysteria',
                    'server': p.hostname,
                    'port': p.port or 443,
                    'auth_str': unquote(g('auth') or g('auth_str')),
                    'sni': g('peer') or g('sni'),
                    'up': g('upmbps'),
                    'down': g('downmbps'),
                    'obfs': g('obfs'),
                    'alpn': g('alpn'),
                    'protocol': g('protocol', 'udp'),
                    'skip-cert-verify': g('insecure', '0') in ('1', 'true')
                }
        except Exception as e:
            console.print(f"[red]解析 Hysteria URI 失败: {e}[/red]")
        return None
    
    def parse_anytls_uri(self, uri: str) -> Dict[str, Any]:
        """解析 AnyTLS URI: anytls://password@host:port?sni=&insecure=1#name"""
        try:
            if uri.startswith('anytls://'):
                p = urlparse(uri)
                q = parse_qs(p.query)
                g = lambda k, d='': q.get(k, [d])[0]
                pw = p.username or ''
                if p.password is not None:
                    pw = f"{pw}:{p.password}"
                return {
                    'name': unquote(p.fragment) if p.fragment else 'AnyTLS Node',
                    'type': 'anytls',
                    'server': p.hostname,
                    'port': p.port or 443,
                    'password': unquote(pw),
                    'sni': g('sni'),
                    'alpn': g('alpn'),
                    'fp': g('fp'),
                    'skip-cert-verify': g('insecure', g('allowInsecure', '0')) in ('1', 'true')
                }
        except Exception as e:
            console.print(f"[red]解析 AnyTLS URI 失败: {e}[/red]")
        return None
    
    def parse_subscription_content(self, content: str) -> List[Dict[str, Any]]:
        """解析订阅内容"""
        format_type = self.detect_format(content)
        nodes = []

        console.print(f"[cyan]检测到格式: {format_type}[/cyan]")

        if format_type == 'clash':
            try:
                data = yaml.safe_load(content)
                if isinstance(data, dict) and 'proxies' in data:
                    nodes = data['proxies']
                elif isinstance(data, dict):
                    # 尝试其他可能的键名
                    for key in ['proxy', 'Proxy', 'servers', 'nodes']:
                        if key in data:
                            nodes = data[key]
                            break
                elif isinstance(data, list):
                    nodes = data
            except Exception as e:
                console.print(f"[red]解析 Clash 配置失败: {e}[/red]")
                # 回退为纯文本 URI 处理
                format_type = 'text_uri'

        if format_type in ['shadowsocks', 'ssr', 'v2ray_uri', 'trojan', 'vless', 'hysteria2', 'hysteria', 'tuic', 'anytls', 'text_uri', 'unknown']:
            # 首先尝试Base64解码
            try:
                stripped = content.replace('\n', '').replace('\r', '')
                if len(stripped) % 4 == 0 and all(c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=' for c in stripped):
                    content = base64.b64decode(stripped).decode('utf-8')
            except Exception:
                pass

            for line in content.strip().split('\n'):
                line = line.strip()
                if not line:
                    continue
                if line.startswith('ssr://'):
                    node = self.parse_ssr_uri(line)
                elif line.startswith('ss://'):
                    node = self.parse_shadowsocks_uri(line)
                elif line.startswith('vmess://'):
                    node = self.parse_vmess_uri(line)
                elif line.startswith('trojan://'):
                    node = self.parse_trojan_uri(line)
                elif line.startswith('vless://'):
                    node = self.parse_vless_uri(line)
                elif line.startswith(('hysteria2://', 'hy2://')):
                    node = self.parse_hysteria2_uri(line)
                elif line.startswith('hysteria://'):
                    node = self.parse_hysteria_uri(line)
                elif line.startswith('tuic://'):
                    node = self.parse_tuic_uri(line)
                elif line.startswith('anytls://'):
                    node = self.parse_anytls_uri(line)
                else:
                    node = None
                if node:
                    nodes.append(node)

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
            clash_node = self._clash_proxy(node)
            if not clash_node:
                continue
            clash_config['proxies'].append(clash_node)
            clash_config['proxy-groups'][0]['proxies'].append(clash_node['name'])
            clash_config['proxy-groups'][1]['proxies'].append(clash_node['name'])
        
        return yaml.dump(clash_config, default_flow_style=False, allow_unicode=True)
    
    def _clash_proxy(self, node: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """将内部节点转换为 Clash Meta (mihomo) proxy 配置；不支持的类型返回 None"""
        t = node.get('type')
        if t == 'ss':
            return {
                'name': node['name'], 'type': 'ss', 'server': node['server'],
                'port': node['port'], 'cipher': node['cipher'], 'password': node['password']
            }
        if t == 'vmess':
            cn = {
                'name': node['name'], 'type': 'vmess', 'server': node['server'],
                'port': node['port'], 'uuid': node['uuid'], 'alterId': node.get('alterId', 0),
                'cipher': node.get('cipher', 'auto'), 'network': node.get('network', 'tcp')
            }
            if node.get('tls'):
                cn['tls'] = True
            if node.get('network') == 'ws':
                ws = {}
                if node.get('path'):
                    ws['path'] = node['path']
                if node.get('host'):
                    ws['headers'] = {'Host': node['host']}
                if ws:
                    cn['ws-opts'] = ws
            return cn
        if t == 'trojan':
            cn = {
                'name': node['name'], 'type': 'trojan', 'server': node['server'],
                'port': node['port'], 'password': node['password']
            }
            if node.get('sni'):
                cn['sni'] = node['sni']
            if node.get('skip-cert-verify'):
                cn['skip-cert-verify'] = True
            return cn
        if t == 'vless':
            cn = {
                'name': node['name'], 'type': 'vless', 'server': node['server'],
                'port': node['port'], 'uuid': node['uuid'],
                'network': node.get('network', 'tcp'), 'udp': True
            }
            if node.get('security') in ('tls', 'reality', 'xtls'):
                cn['tls'] = True
                if node.get('sni'):
                    cn['servername'] = node['sni']
                if node.get('fp'):
                    cn['client-fingerprint'] = node['fp']
                if node.get('security') == 'reality':
                    ro = {}
                    if node.get('pbk'):
                        ro['public-key'] = node['pbk']
                    if node.get('sid'):
                        ro['short-id'] = node['sid']
                    if ro:
                        cn['reality-opts'] = ro
            if node.get('flow'):
                cn['flow'] = node['flow']
            if node.get('network') == 'ws':
                ws = {}
                if node.get('path'):
                    ws['path'] = node['path']
                if node.get('host'):
                    ws['headers'] = {'Host': node['host']}
                if ws:
                    cn['ws-opts'] = ws
            return cn
        if t == 'hysteria2':
            cn = {
                'name': node['name'], 'type': 'hysteria2', 'server': node['server'],
                'port': node['port'], 'password': node['password']
            }
            if node.get('sni'):
                cn['sni'] = node['sni']
            if node.get('obfs'):
                cn['obfs'] = node['obfs']
                if node.get('obfs-password'):
                    cn['obfs-password'] = node['obfs-password']
            if node.get('skip-cert-verify'):
                cn['skip-cert-verify'] = True
            return cn
        if t == 'tuic':
            cn = {
                'name': node['name'], 'type': 'tuic', 'server': node['server'],
                'port': node['port'], 'uuid': node['uuid'], 'password': node['password'],
                'congestion-controller': node.get('congestion-controller', 'bbr'),
                'udp-relay-mode': node.get('udp-relay-mode', 'native')
            }
            if node.get('sni'):
                cn['sni'] = node['sni']
            if node.get('alpn'):
                cn['alpn'] = [node['alpn']]
            if node.get('skip-cert-verify'):
                cn['skip-cert-verify'] = True
            return cn
        if t == 'ssr':
            cn = {
                'name': node['name'], 'type': 'ssr', 'server': node['server'],
                'port': node['port'], 'cipher': node['cipher'], 'password': node['password'],
                'protocol': node.get('protocol', 'origin'), 'obfs': node.get('obfs', 'plain'),
                'udp': True
            }
            if node.get('protocol-param'):
                cn['protocol-param'] = node['protocol-param']
            if node.get('obfs-param'):
                cn['obfs-param'] = node['obfs-param']
            return cn
        if t == 'hysteria':
            cn = {
                'name': node['name'], 'type': 'hysteria', 'server': node['server'],
                'port': node['port']
            }
            if node.get('auth_str'):
                cn['auth-str'] = node['auth_str']
            if node.get('up'):
                cn['up'] = node['up']
            if node.get('down'):
                cn['down'] = node['down']
            if node.get('sni'):
                cn['sni'] = node['sni']
            if node.get('obfs'):
                cn['obfs'] = node['obfs']
            if node.get('alpn'):
                cn['alpn'] = [node['alpn']]
            if node.get('protocol'):
                cn['protocol'] = node['protocol']
            if node.get('skip-cert-verify'):
                cn['skip-cert-verify'] = True
            return cn
        if t == 'anytls':
            cn = {
                'name': node['name'], 'type': 'anytls', 'server': node['server'],
                'port': node['port'], 'password': node['password'], 'udp': True
            }
            if node.get('sni'):
                cn['sni'] = node['sni']
            if node.get('alpn'):
                cn['alpn'] = [node['alpn']]
            if node.get('fp'):
                cn['client-fingerprint'] = node['fp']
            if node.get('skip-cert-verify'):
                cn['skip-cert-verify'] = True
            return cn
        return None
    
    def node_to_uri(self, node: Dict[str, Any]) -> Optional[str]:
        """将内部节点还原为标准分享链接（用于通用订阅输出）"""
        t = node.get('type')
        name = quote(node.get('name', ''), safe='')
        if t == 'ss':
            auth = base64.urlsafe_b64encode(f"{node['cipher']}:{node['password']}".encode()).decode().rstrip('=')
            return f"ss://{auth}@{node['server']}:{node['port']}#{name}"
        if t == 'vmess':
            cfg = {
                'v': '2', 'ps': node.get('name', ''), 'add': node['server'], 'port': str(node['port']),
                'id': node['uuid'], 'aid': str(node.get('alterId', 0)), 'scy': node.get('cipher', 'auto'),
                'net': node.get('network', 'tcp'), 'type': 'none', 'host': node.get('host', ''),
                'path': node.get('path', ''), 'tls': 'tls' if node.get('tls') else ''
            }
            return 'vmess://' + base64.b64encode(json.dumps(cfg).encode()).decode()
        if t == 'trojan':
            q = {}
            if node.get('sni'):
                q['sni'] = node['sni']
            if node.get('skip-cert-verify'):
                q['allowInsecure'] = '1'
            qs = ('?' + urlencode(q)) if q else ''
            return f"trojan://{quote(node['password'], safe='')}@{node['server']}:{node['port']}{qs}#{name}"
        if t == 'vless':
            q = {'encryption': 'none', 'type': node.get('network', 'tcp')}
            if node.get('security'):
                q['security'] = node['security']
            for k in ('sni', 'flow', 'host', 'pbk', 'sid', 'fp'):
                if node.get(k):
                    q[k] = node[k]
            if node.get('path'):
                q['path'] = node['path']
            return f"vless://{node['uuid']}@{node['server']}:{node['port']}?{urlencode(q)}#{name}"
        if t == 'hysteria2':
            q = {}
            for k in ('sni', 'obfs', 'obfs-password'):
                if node.get(k):
                    q[k] = node[k]
            if node.get('skip-cert-verify'):
                q['insecure'] = '1'
            qs = ('?' + urlencode(q)) if q else ''
            return f"hysteria2://{quote(node.get('password', ''), safe='')}@{node['server']}:{node['port']}/{qs}#{name}"
        if t == 'tuic':
            q = {
                'congestion_control': node.get('congestion-controller', 'bbr'),
                'udp_relay_mode': node.get('udp-relay-mode', 'native')
            }
            if node.get('sni'):
                q['sni'] = node['sni']
            if node.get('alpn'):
                q['alpn'] = node['alpn']
            if node.get('skip-cert-verify'):
                q['allow_insecure'] = '1'
            return f"tuic://{node['uuid']}:{quote(node.get('password', ''), safe='')}@{node['server']}:{node['port']}?{urlencode(q)}#{name}"
        if t == 'ssr':
            enc = lambda s: base64.urlsafe_b64encode((s or '').encode()).decode().rstrip('=')
            main = f"{node['server']}:{node['port']}:{node.get('protocol', 'origin')}:{node['cipher']}:{node.get('obfs', 'plain')}:{enc(node['password'])}"
            q = urlencode({
                'obfsparam': enc(node.get('obfs-param', '')),
                'protoparam': enc(node.get('protocol-param', '')),
                'remarks': enc(node.get('name', ''))
            })
            return 'ssr://' + base64.urlsafe_b64encode(f"{main}/?{q}".encode()).decode().rstrip('=')
        if t == 'hysteria':
            q = {}
            if node.get('auth_str'):
                q['auth'] = node['auth_str']
            if node.get('sni'):
                q['peer'] = node['sni']
            if node.get('up'):
                q['upmbps'] = node['up']
            if node.get('down'):
                q['downmbps'] = node['down']
            for k in ('obfs', 'alpn', 'protocol'):
                if node.get(k):
                    q[k] = node[k]
            if node.get('skip-cert-verify'):
                q['insecure'] = '1'
            return f"hysteria://{node['server']}:{node['port']}?{urlencode(q)}#{name}"
        if t == 'anytls':
            q = {}
            for k in ('sni', 'alpn', 'fp'):
                if node.get(k):
                    q[k] = node[k]
            if node.get('skip-cert-verify'):
                q['insecure'] = '1'
            qs = ('?' + urlencode(q)) if q else ''
            return f"anytls://{quote(node.get('password', ''), safe='')}@{node['server']}:{node['port']}{qs}#{name}"
        return None
    
    def convert_to_uri(self, nodes: List[Dict[str, Any]]) -> str:
        """转换为通用 URI 订阅（Base64，全协议）"""
        uris = [u for u in (self.node_to_uri(n) for n in nodes) if u]
        return base64.b64encode('\n'.join(uris).encode()).decode()
    
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
