# Browser Harness Skill 结构

## 目录结构

```
skills/browser-harness/
├── SKILL.md              # 主文件（必须）
├── scripts/              # 可执行脚本（可选）
│   ├── cookies-cli.sh    # Cookies 管理 CLI
│   └── example.sh        # 示例脚本
├── references/           # 详细参考文档（可选，按需加载）
│   └── cookies-manager.md # Cookies 管理详细文档
├── resources/            # 模板、清单等资源（可选）
│   └── README.md         # 资源说明
└── examples/             # 示例（可选）
    └── USAGE.md          # 使用示例
```

## 文件说明

### SKILL.md（必须）
- 核心浏览器操作
- 常用函数和命令
- 最佳实践和注意事项
- 按需加载引用

### scripts/（可执行脚本）
- `cookies-cli.sh` - Cookies 管理 CLI
- `example.sh` - 完整工作流示例

### references/（详细参考文档）
- `cookies-manager.md` - Cookies 管理详细文档
- 按需加载，遇到登录问题时加载

### resources/（资源文件）
- 模板、清单等
- 配置文件

### examples/（示例）
- 使用示例
- 集成示例

## 使用方式

### Agent 学习
1. 学习 SKILL.md - 核心功能
2. 按需加载 references/ 中的文档
3. 使用 scripts/ 中的工具

### 工作流程
```
Agent 访问网站
    ↓
检测是否需要登录
    ↓
如果需要登录
    - 加载 references/cookies-manager.md
    - 提醒用户
    - 等待用户登录
    - 使用 scripts/cookies-cli.sh 同步
    ↓
继续操作
```

## 最佳实践

1. **按需加载** - 只在需要时加载 references/ 中的文档
2. **脚本优先** - 优先使用 scripts/ 中的工具
3. **示例参考** - 遇到问题时查看 examples/
4. **资源管理** - 使用 resources/ 中的模板