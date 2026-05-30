# Hulink - 代理节点订阅链接转换工具

一个功能强大的代理节点订阅链接转换工具，支持 Shadowsocks、Clash、V2Ray、Surge 等多种代理协议的互相转换。

## 功能特性

- 🔄 **多格式支持**: 支持 Shadowsocks、VMess、Clash、V2Ray 等主流代理协议
- 🎯 **智能识别**: 自动检测订阅链接的格式类型
- 🔧 **灵活转换**: 支持多种输出格式，满足不同客户端需求
- 🖥️ **友好界面**: 清晰简洁的中文终端界面
- 📦 **开箱即用**: 无需复杂配置，下载即可使用
- 🛡️ **兼容性强**: 适配最新版本的代理协议规范

## 支持的协议格式

### 输入格式
- **Shadowsocks**: `ss://` URI 格式、Base64 编码订阅
- **VMess**: `vmess://` URI 格式、Base64 编码订阅
- **Clash**: YAML 配置文件格式
- **V2Ray**: JSON 配置文件、vmess:// 链接
- **Trojan**: `trojan://` URI 格式
- **VLESS**: `vless://` URI 格式（支持 TLS / Reality / WS）
- **Hysteria2**: `hysteria2://`、`hy2://` URI 格式
- **TUIC**: `tuic://` URI 格式（v5）
- **ShadowsocksR**: `ssr://` URI 格式
- **Hysteria v1**: `hysteria://` URI 格式
- **AnyTLS**: `anytls://` URI 格式

### 输出格式
- **Clash YAML**: 完整的 Clash Meta (mihomo) 配置文件
- **Shadowsocks Base64**: 标准的 SS 订阅格式
- **V2Ray Base64**: 标准的 V2Ray 订阅格式
- **通用 URI 订阅 Base64**: 各协议分享链接打包，兼容主流客户端

## 安装和使用

### 环境要求
- Python 3.7+
- 网络连接（用于获取订阅链接）

### 安装依赖

```bash
# 克隆项目
git clone https://github.com/ink1ing/hulink.git
cd hulink

# 安装依赖包
pip3 install -r requirements.txt
```

### 运行程序

```bash
python3 main.py
```

或使用启动脚本：

```bash
./start.sh        # macOS / Linux
run.bat           # Windows
```

### 图形用户面板（GUI）

无需命令行，直接运行跨平台图形面板（基于 Tkinter，无额外依赖）：

```bash
python3 gui.py
```

面板流程：输入订阅链接 → 「获取并解析」→ 选择输出格式 → 「预览」或「转换并保存」。

## 构建与发布（桌面端）

> 官方 Release 仅发布源码版，社区开发者下载源码后按下方脚本自行构建可执行程序。

打包为各平台原生程序（基于 PyInstaller）：

```bash
# Windows: 生成 dist\Hulink.exe
packaging\build_windows.bat

# macOS: 生成 dist/Hulink.app、Hulink.dmg、Hulink.pkg
./packaging/build_macos.sh
```

发布矩阵：

| 平台 | 产物 | 构建脚本 | 说明 |
|---|---|---|---|
| Windows | `Hulink.exe` | `packaging/build_windows.bat` | 需在 Windows 上构建 |
| macOS | `Hulink.app` / `.dmg` / `.pkg` | `packaging/build_macos.sh` | 需在 macOS 上构建；未签名时 Gatekeeper 会拦截，正式发布需 `codesign` + `notarytool` |
| Android | `Hulink.apk` | `mobile/` (Kivy + Buildozer) | 见下方说明；CI 自动构建，正式发布需 keystore 签名 |

### Android 构建

移动端为独立的 Kivy 应用（`mobile/`），复用根目录的 `converter.py` 核心。

```bash
# 本地（需 Linux + Android SDK/NDK；buildozer 仅支持在 Linux 上构建）
cp converter.py mobile/converter.py
cd mobile && buildozer android debug   # 产物: mobile/bin/*.apk
```

也可直接用 CI：推送 `v*` 标签或手动触发 `.github/workflows/android.yml`，由 GitHub Actions 自动产出 APK 工件。正式上架需用 release keystore 对 APK 签名。

## 使用指南

### 主要功能

1. **订阅链接转换**
   - 输入任意支持的订阅链接
   - 自动检测格式并解析节点信息
   - 选择目标输出格式进行转换
   - 支持保存为文件或预览结果

2. **测试示例链接**
   - 内置测试链接验证功能
   - 快速测试程序的转换能力

3. **查看支持格式**
   - 详细的格式支持说明
   - 了解各协议的兼容性状态

### 操作流程

1. 启动程序后，选择 "订阅链接转换"
2. 输入你的订阅链接 URL
3. 程序自动获取并解析订阅内容
4. 查看解析出的节点信息
5. 选择目标输出格式（Clash/Shadowsocks/V2Ray）
6. 选择保存文件或查看预览

## 项目结构

```
hulink/
├── main.py              # 主程序文件
├── requirements.txt     # 依赖包列表
├── converter.py        # 核心转换逻辑 (各端复用，rich 可选)
├── gui.py              # 图形用户面板 (Tkinter)
├── start.sh            # 启动脚本 (macOS/Linux)
├── run.bat             # 启动脚本 (Windows)
├── packaging/          # 桌面端打包脚本 (exe/dmg/pkg)
├── mobile/             # Android 应用 (Kivy + buildozer.spec)
├── test_links.py       # 测试脚本
├── README.md           # 项目说明文档
├── LICENSE             # MIT 许可证
└── .gitignore          # Git 忽略文件
```

## 技术特点

### 核心功能
- **智能格式检测**: 通过内容特征自动识别订阅格式
- **多协议解析**: 支持解析各种代理协议的配置参数
- **标准化输出**: 生成符合各客户端标准的配置文件
- **错误处理**: 完善的异常处理和用户提示
- **网络优化**: 多种请求方式，增强连接成功率

### 代码架构
- **模块化设计**: 清晰的类和方法结构
- **可扩展性**: 易于添加新的协议支持
- **用户体验**: 丰富的终端界面和交互设计

## 注意事项

1. **网络要求**: 需要能够访问订阅链接的网络环境
2. **格式兼容**: 部分特殊格式可能需要手动调整
3. **安全提醒**: 请确保订阅链接来源可信
4. **版本更新**: 建议定期更新以支持最新的协议版本

## 开发计划

- [x] 支持 Trojan 协议
- [x] 支持 VLESS 协议
- [x] 支持 Hysteria2 协议
- [x] 支持 TUIC 协议
- [x] 支持 ShadowsocksR 协议
- [x] 支持 Hysteria v1 协议
- [x] 支持 AnyTLS 协议
- [ ] 支持 Surge 配置格式
- [ ] 添加配置文件验证功能
- [ ] 支持批量订阅链接处理
- [ ] 添加节点测速功能
- [ ] 支持自定义规则配置
- [ ] Web 界面支持

## 许可证

本项目采用 MIT 许可证，详情请查看 [LICENSE](LICENSE) 文件。

## 贡献

欢迎提交 Issue 和 Pull Request 来帮助改进这个项目！

### 贡献指南

1. Fork 本仓库
2. 创建你的特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交你的修改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开一个 Pull Request

## 联系方式

如果你有任何问题或建议，欢迎通过以下方式联系：

- 提交 [Issue](https://github.com/ink1ing/hulink/issues)
- 发起 [Discussion](https://github.com/ink1ing/hulink/discussions)

---

**Hulink** - 让代理配置转换变得简单高效！ 🚀
