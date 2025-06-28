#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试脚本 - 验证示例链接的转换功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import ProxyConverter
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import print as rprint

console = Console()

def test_subscription_link(url: str, link_name: str):
    """测试单个订阅链接"""
    console.print(f"\n[bold cyan]测试链接: {link_name}[/bold cyan]")
    console.print(f"[dim]URL: {url}[/dim]")
    console.print("[yellow]正在获取和解析...[/yellow]")
    
    converter = ProxyConverter()
    
    try:
        # 获取订阅内容
        content = converter.fetch_subscription(url)
        console.print(f"[green]✅ 成功获取订阅内容 ({len(content)} 字符)[/green]")
        
        # 检测格式
        format_type = converter.detect_format(content)
        console.print(f"[green]✅ 检测到格式: {format_type}[/green]")
        
        # 解析节点
        nodes = converter.parse_subscription_content(content)
        console.print(f"[green]✅ 成功解析 {len(nodes)} 个节点[/green]")
        
        if nodes:
            # 显示前3个节点信息
            table = Table(show_header=True, header_style="bold magenta", title=f"{link_name} - 节点信息")
            table.add_column("序号", width=4)
            table.add_column("节点名称")
            table.add_column("类型")
            table.add_column("服务器")
            table.add_column("端口")
            
            for i, node in enumerate(nodes[:3], 1):
                table.add_row(
                    str(i),
                    node.get('name', 'Unknown')[:30] + ('...' if len(node.get('name', '')) > 30 else ''),
                    node.get('type', 'Unknown'),
                    node.get('server', 'Unknown'),
                    str(node.get('port', 'Unknown'))
                )
            
            if len(nodes) > 3:
                table.add_row("...", f"还有 {len(nodes) - 3} 个节点", "", "", "")
            
            console.print(table)
            
            # 测试转换功能
            console.print("\n[yellow]测试格式转换...[/yellow]")
            
            try:
                # 转换为 Clash 格式
                clash_config = converter.convert_to_clash(nodes)
                console.print(f"[green]✅ Clash 格式转换成功 ({len(clash_config)} 字符)[/green]")
                
                # 保存测试文件
                test_filename = f"test_{link_name.lower().replace(' ', '_')}_clash.yaml"
                with open(test_filename, 'w', encoding='utf-8') as f:
                    f.write(clash_config)
                console.print(f"[green]✅ 已保存测试文件: {test_filename}[/green]")
                
            except Exception as e:
                console.print(f"[red]❌ Clash 格式转换失败: {str(e)}[/red]")
            
            try:
                # 转换为 Shadowsocks 格式（如果有SS节点）
                ss_nodes = [node for node in nodes if node.get('type') == 'ss']
                if ss_nodes:
                    ss_config = converter.convert_to_shadowsocks(ss_nodes)
                    console.print(f"[green]✅ Shadowsocks 格式转换成功 ({len(ss_nodes)} 个SS节点)[/green]")
                else:
                    console.print("[yellow]⚠️  无SS节点，跳过Shadowsocks格式转换[/yellow]")
                    
            except Exception as e:
                console.print(f"[red]❌ Shadowsocks 格式转换失败: {str(e)}[/red]")
            
            try:
                # 转换为 V2Ray 格式（如果有VMess节点）
                vmess_nodes = [node for node in nodes if node.get('type') == 'vmess']
                if vmess_nodes:
                    v2ray_config = converter.convert_to_v2ray(vmess_nodes)
                    console.print(f"[green]✅ V2Ray 格式转换成功 ({len(vmess_nodes)} 个VMess节点)[/green]")
                else:
                    console.print("[yellow]⚠️  无VMess节点，跳过V2Ray格式转换[/yellow]")
                    
            except Exception as e:
                console.print(f"[red]❌ V2Ray 格式转换失败: {str(e)}[/red]")
        
        else:
            console.print("[red]❌ 未解析到任何节点[/red]")
            
        return True
        
    except Exception as e:
        console.print(f"[red]❌ 测试失败: {str(e)}[/red]")
        return False

def main():
    """主测试函数"""
    console.print(Panel(
        "[bold blue]Hulink 测试脚本[/bold blue]\n"
        "[dim]自动测试示例链接的转换功能[/dim]",
        border_style="blue"
    ))
    
    # 测试链接
    test_links = [
        {
            "url": "https://raw.githubusercontent.com/peasoft/NoMoreWalls/master/list.txt",
            "name": "测试链接1"
        },
        {
            "url": "https://feed.iggv5.com/c/afe61b0f-0e99-4479-b711-3b6465435df9#afe61b0f-0e99-4479-b711-3b6465435df9",
            "name": "测试链接2"
        }
    ]
    
    results = []
    
    for link in test_links:
        success = test_subscription_link(link["url"], link["name"])
        results.append((link["name"], success))
        console.print("\n" + "="*60)
    
    # 显示测试结果汇总
    console.print("\n[bold yellow]测试结果汇总:[/bold yellow]")
    
    summary_table = Table(show_header=True, header_style="bold green")
    summary_table.add_column("测试项目")
    summary_table.add_column("结果")
    
    for name, success in results:
        status = "[green]✅ 成功[/green]" if success else "[red]❌ 失败[/red]"
        summary_table.add_row(name, status)
    
    console.print(summary_table)
    
    success_count = sum(1 for _, success in results if success)
    total_count = len(results)
    
    if success_count == total_count:
        console.print(f"\n[bold green]🎉 所有测试通过! ({success_count}/{total_count})[/bold green]")
    else:
        console.print(f"\n[bold yellow]⚠️  部分测试失败 ({success_count}/{total_count})[/bold yellow]")
    
    console.print("\n[dim]测试完成，生成的文件可在当前目录查看[/dim]")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n\n[bold red]测试被用户中断[/bold red]")
    except Exception as e:
        console.print(f"\n\n[bold red]测试过程中发生错误: {str(e)}[/bold red]")