# FreqTrade Docker 常用命令

## 📋 基本操作

### 进入项目目录
```bash
cd /Users/Jason/Desktop/code/ft_userdata
```

### 启动服务
```bash
# 启动 FreqTrade（后台运行）
docker compose up -d

# 启动并查看日志
docker compose up
```

### 停止服务
```bash
# 停止 FreqTrade
docker compose down

# 停止但保留数据卷
docker compose stop
```

### 重启服务
```bash
# 重启 FreqTrade
docker compose restart

# 重启并强制重新创建容器
docker compose up -d --force-recreate
```

### 查看状态
```bash
# 查看容器状态
docker compose ps

# 查看容器详细信息
docker compose ps -a
```

## 📊 日志查看

### 实时日志
```bash
# 查看实时日志（按 Ctrl+C 退出）
docker compose logs -f

# 查看最近的日志（最后 50 行）
docker compose logs --tail=50

# 查看最近日志并持续跟踪
docker compose logs --tail=50 -f
```

### 过滤日志
```bash
# 查看错误日志
docker compose logs | grep ERROR

# 查看包含特定关键词的日志
docker compose logs | grep "Bot heartbeat"

# 查看最近 100 行错误日志
docker compose logs --tail=100 | grep ERROR
```

### 导出日志
```bash
# 导出所有日志到文件
docker compose logs --no-log-prefix > freqtrade.log

# 导出最近 500 行日志
docker compose logs --tail=500 > freqtrade_recent.log
```

## ⚙️ 配置修改流程

### 修改配置后重启
```bash
# 1. 编辑配置文件
# 使用编辑器修改 user_data/config.json

# 2. 验证配置（可选）
docker compose run --rm freqtrade show-config

# 3. 重启服务
docker compose restart

# 4. 查看启动日志确认无错误
docker compose logs --tail=30
```

### 快速重启流程
```bash
cd /Users/Jason/Desktop/code/ft_userdata
docker compose restart && docker compose logs --tail=20 -f
```

## 🔄 镜像更新

### 更新到最新版本
```bash
# 1. 拉取最新镜像
docker compose pull

# 2. 停止当前服务
docker compose down

# 3. 启动新版本
docker compose up -d

# 4. 查看日志
docker compose logs -f
```

### 切换版本
```bash
# 编辑 docker-compose.yml，修改 image 行
# image: freqtradeorg/freqtrade:stable      # 稳定版
# image: freqtradeorg/freqtrade:develop     # 开发版
# image: freqtradeorg/freqtrade:2026.1      # 指定版本

# 然后重新启动
docker compose up -d --force-recreate
```

## 🐚 容器内部操作

### 进入容器
```bash
# 进入 FreqTrade 容器
docker compose exec freqtrade /bin/bash

# 退出容器（在容器内执行）
exit
```

### 执行单个命令
```bash
# 查看 FreqTrade 版本
docker compose exec freqtrade freqtrade --version

# 查看帮助
docker compose exec freqtrade freqtrade --help

# 查看策略列表
docker compose exec freqtrade freqtrade list-strategies

# 查看交易对
docker compose exec freqtrade freqtrade list-pairs
```

## 📈 数据管理

### 下载历史数据
```bash
# 下载指定交易对的历史数据
docker compose run --rm freqtrade download-data \
  --exchange okx \
  --pairs BTC/USDT:USDT ETH/USDT:USDT SOL/USDT:USDT \
  --timeframes 5m 1h \
  --days 30

# 下载配置中所有交易对的数据
docker compose run --rm freqtrade download-data \
  --timeframes 5m \
  --days 30
```

### 查看已下载数据
```bash
# 列出所有已下载的数据
docker compose run --rm freqtrade list-data

# 查看数据目录
ls -lh user_data/data/okx/
```

## 🧪 回测与策略测试

### 回测策略
```bash
# 回测指定策略
docker compose run --rm freqtrade backtesting \
  --strategy SampleStrategy \
  --timerange 20260101-20260215

# 回测并输出详细信息
docker compose run --rm freqtrade backtesting \
  --strategy SampleStrategy \
  --timerange 20260101-20260215 \
  --export trades
```

### 查看策略信息
```bash
# 查看策略列表
docker compose run --rm freqtrade list-strategies

# 查看策略详情
docker compose run --rm freqtrade show-strategy \
  --strategy SampleStrategy
```

### 参数优化
```bash
# 使用 Hyperopt 优化参数
docker compose run --rm freqtrade hyperopt \
  --strategy SampleStrategy \
  --hyperopt-loss SharpeHyperOptLoss \
  --epochs 100
```

## 🔍 API 测试

### 测试 API 连接
```bash
# 测试 ping
curl http://localhost:8080/api/v1/ping

# 查看 Bot 状态
curl -u Jason:SZph985211 http://localhost:8080/api/v1/status

# 查看余额
curl -u Jason:SZph985211 http://localhost:8080/api/v1/balance

# 查看交易对白名单
curl -u Jason:SZph985211 http://localhost:8080/api/v1/whitelist
```

### 使用 JWT Token
```bash
# 获取 token（使用 ws_token）
curl -X POST http://localhost:8080/api/v1/token/login \
  -H "Content-Type: application/json" \
  -d '{"username":"Jason","password":"SZph985211"}'

# 使用 token 查询（替换 YOUR_TOKEN）
curl http://localhost:8080/api/v1/status \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## 🛠️ 故障排查

### 查看详细错误
```bash
# 查看所有错误日志
docker compose logs | grep -i error

# 查看最近的错误和警告
docker compose logs --tail=200 | grep -E "(ERROR|WARNING)"

# 查看容器启动失败原因
docker compose logs --tail=100
```

### 验证配置
```bash
# 显示当前配置
docker compose run --rm freqtrade show-config

# 验证策略是否有效
docker compose run --rm freqtrade test-strategy \
  --strategy SampleStrategy
```

### 重置容器
```bash
# 完全停止并删除容器
docker compose down

# 删除容器和卷（⚠️ 会删除所有数据）
docker compose down -v

# 重新创建
docker compose up -d
```

## 🧹 清理操作

### 清理日志
```bash
# 查看日志大小
docker compose logs --tail=1000 | wc -l

# 清空 Docker 日志
docker compose down
docker compose up -d
```

### 清理未使用的镜像
```bash
# 查看所有镜像
docker images | grep freqtrade

# 删除旧版本镜像
docker image prune -a
```

### 清理 FreqTrade 数据
```bash
# 清理回测结果
rm -rf user_data/backtest_results/*

# 清理旧的历史数据
rm -rf user_data/data/okx/*

# 清理日志文件
rm -f user_data/logs/*.log
```

## 📊 监控与维护

### 查看资源占用
```bash
# 查看容器资源使用情况
docker stats freqtrade

# 查看容器详细信息
docker inspect freqtrade
```

### 定期维护
```bash
# 每日检查运行状态
docker compose ps

# 查看最近是否有错误
docker compose logs --since 24h | grep ERROR

# 定期更新镜像（每周）
docker compose pull && docker compose up -d
```

## 🔐 安全操作

### 备份配置
```bash
# 备份配置文件
cp user_data/config.json user_data/config.json.backup

# 备份整个 user_data 目录
tar -czf user_data_backup_$(date +%Y%m%d).tar.gz user_data/
```

### 恢复配置
```bash
# 恢复配置文件
cp user_data/config.json.backup user_data/config.json

# 恢复后重启
docker compose restart
```

## 📝 实用组合命令

### 快速诊断
```bash
# 一键查看状态、日志和错误
docker compose ps && \
docker compose logs --tail=20 && \
docker compose logs | grep ERROR | tail -10
```

### 完全重启
```bash
# 停止 → 拉取新镜像 → 启动 → 查看日志
cd /Users/Jason/Desktop/code/ft_userdata && \
docker compose down && \
docker compose pull && \
docker compose up -d && \
docker compose logs -f
```

### 配置修改快捷流程
```bash
# 重启并持续查看日志
docker compose restart && sleep 3 && docker compose logs -f
```

## 🌐 Web UI 访问

### 访问地址
```
http://localhost:8080
```

### 登录信息
- **用户名**: Jason
- **密码**: SZph985211
- **API URL**: http://localhost:8080

### 添加 Bot 到 UI
1. 打开 Web UI
2. 点击右上角的登录/添加按钮
3. 填写：
   - Bot Name: freqtrade1
   - API URL: http://localhost:8080
   - Username: Jason
   - Password: SZph985211
4. 点击 Login

## 📞 Telegram 机器人命令

常用 Telegram 命令（在配置了 Telegram 的情况下）：

- `/status` - 查看当前持仓
- `/profit` - 查看收益统计
- `/balance` - 查看账户余额
- `/daily` - 每日收益
- `/count` - 交易统计
- `/performance` - 性能分析
- `/whitelist` - 查看交易对白名单
- `/help` - 查看所有命令

## 🚀 快速参考

| 操作 | 命令 |
|------|------|
| 启动 | `docker compose up -d` |
| 停止 | `docker compose down` |
| 重启 | `docker compose restart` |
| 查看日志 | `docker compose logs -f` |
| 查看状态 | `docker compose ps` |
| 进入容器 | `docker compose exec freqtrade bash` |
| 更新镜像 | `docker compose pull` |
| 查看配置 | `docker compose run --rm freqtrade show-config` |

---

**项目路径**: `/Users/Jason/Desktop/code/ft_userdata`  
**配置文件**: `user_data/config.json`  
**日志文件**: `user_data/logs/freqtrade.log`  
**数据目录**: `user_data/data/okx/`
