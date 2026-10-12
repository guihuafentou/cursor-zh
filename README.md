# Cursor 简体中文汉化工具（cursor-zh）

一键把 Cursor 的自研界面（侧边栏、设置页、命令面板、菜单、弹窗、MCP 管理页等）汉化为简体中文，**不改任何运行逻辑，可随时还原**。

- 词表基于 **Cursor 3.24（Windows）** 实测提取，双文件累计 **3400+ 处**替换
- 每个替换位都经过**安全过滤**：比较位、枚举映射、逻辑字段、函数参数、nls 本地化位一律跳过
- 自动备份英文原版，`--restore` 一键还原
- 每次替换自动跑 `node --check` 语法验证，**语法不通过就不写入**

## 为什么需要它

Cursor 的自研界面（非 VS Code 继承部分）**不走官方语言包**。官方中文语言包 `ms-ceintl` 只能翻译 VS Code 继承的界面，而侧边栏、Agent 面板、设置页、命令面板、右键菜单等自研区域始终是英文。本工具直接安全改写界面显示字符串。

## 使用方法

```bash
# 1. 自动定位 Cursor 并汉化（自动备份原文件）
python hanhua.py

# 2. 如果没自动找到，手动指定 Cursor 的 resources\app 目录
python hanhua.py --path "D:\cursor\resources\app"

# 3. 还原英文原版
python hanhua.py --restore

# 4. 只看会替换多少处（不写入）
python hanhua.py --dry-run
```

汉化完成后**重启 Cursor** 生效。

> 需要 Python 3.6+。语法验证需要 Node.js（没有也会继续，只是跳过验证）。

### 常见 Cursor 安装位置（自动探测）

| 系统 | 路径 |
|---|---|
| Windows | `C:\Users\<你>\AppData\Local\Programs\cursor\resources\app` |
| Windows | `C:\Program Files\Cursor\resources\app` |
| Windows | `D:\cursor\resources\app` 等 |
| macOS | `/Applications/Cursor.app/Contents/Resources/app` |

## 工作原理

目标文件（两个，都会处理）：
- `resources\app\out\vs\workbench\workbench.glass.main.js`
- `resources\app\out\vs\workbench\workbench.desktop.main.js`（命令面板/设置条目等也分布在此文件）

1. 读取词表 `words.json`（`global` 短词 + `anchor` 长句/锚定）
2. 逐词查找显示位并替换，**只改引号内的显示文本**
3. 安全规则：
   - 跳过 `===`/`!==` 等**比较位**（翻了会断逻辑）
   - 跳过 `t[t.X=1]="X"` 等**枚举映射**
   - 跳过 `.includes("X")` 等**方法调用参数**
   - 只翻 `label:`/`title:`/`children:`/`description:` 等**显示字段**和三目/默认值位
4. 替换后写临时文件跑 `node --check`，通过才写回正式文件

## 文件结构

```
cursor-zh/
├── hanhua.py     # 汉化器主脚本
├── words.json    # 词表（global + anchor）
└── README.md
```

## 已知限制

| 限制 | 说明 |
|---|---|
| 服务端下发的文案 | 主页按钮（"Start from scratch" 等）、模型名等由 Cursor 服务器下发，本地文件里没有，**任何本地汉化都覆盖不到** |
| 设置搜索条目 | 部分设置搜索条目是压缩后变量名锚定（如 `d3("Settings")`），变量名随版本变化，词表无法精确匹配 |
| 模板插值 | 少量 `` `在 ${xxx}` `` 模板内的插值位需要随版本维护 |
| Cursor 更新 | Cursor 更新会覆盖汉化文件，**重新运行一次脚本即可** |
| 版本兼容 | 词表基于 3.24 构建；新版本个别字符串变化时，脚本会自动跳过未匹配项，**不会破坏文件** |

## 免责声明（必读）

- 本项目**仅用于个人学习与界面本地化研究**
- 修改 Cursor 安装文件**不符合其服务条款（ToS）**，请自行评估风险
- 本项目**不捆绑、不修改**任何 Cursor 官方文件，只提供一个本地替换脚本
- 使用本工具产生的一切后果由使用者自行承担
- 请勿用于商业用途或传播修改后的 Cursor 安装包

## 词表维护 / 贡献

- `words.json` 的 `global` 是"英文短词 → 中文"映射（自动安全过滤）
- `anchor` 是长句/精确锚定（直接替换）
- 发现漏翻的界面词，欢迎提 Issue / PR，把"英文词 + 界面位置截图"一起发

## License

MIT