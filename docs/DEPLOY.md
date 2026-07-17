# DEPLOY — 部署与免费 Demo

## 原则

**在线 Demo 尽量免费、国内可访问。**  
禁止作为主验收：Hugging Face Spaces、Streamlit Cloud、Vercel、Netlify、Railway、Render。

## 推荐顺序（免费 → 付费备选）

| 优先级 | 方案 | 费用 | 备注 |
|:------:|------|------|------|
| 1 | [Sealos](https://sealos.io) 免费额度 / 公网应用 | 免费档优先 | 容器部署 `docker-compose` 或单镜像 |
| 2 | 魔搭创空间（若适配 Gradio/静态+API 形态） | 免费档 | 需确认是否便于挂 FastAPI；不适合则跳过 |
| 3 | 本机 + Cloudflare Quick Tunnel | 免费 | 电脑需在线；适合临时演示 |
| 4 | 阿里云轻量应用服务器 | 付费 | 稳定长期 Demo 备选 |

## 本地一键

```bash
cp .env.example .env   # 填 DEEPSEEK_API_KEY
docker-compose up --build
# 浏览器打开 http://127.0.0.1:5173 或 compose 映射端口
```

## 环境变量

见根目录 `.env.example`（实现阶段补齐）：

- `OPENAI_API_KEY` / `DEEPSEEK_API_KEY`
- `OPENAI_BASE_URL=https://api.deepseek.com/v1`
- `MODEL_NAME=deepseek-chat`
- `FEATURE_SUMMARY=1`
- `FEATURE_CACHE=1`

## GitHub

- README 顶部预留：`Demo: <URL>` 占位
- License：Apache-2.0
- 推送步骤写入 README「Publish」小节

## 当前 Demo

- Cloudflare Quick Tunnel（免费、国内可访问）：见根目录 `README.md` 顶部链接；日志在 `logs/public_url.txt`。
- 长期：建议迁 Sealos 免费容器，把同一 `docker-compose` 镜像拉起。

## 验收

- [x] 国内网络可打开主路径（告警页可提交）— Tunnel 演示
- [x] README Demo 链接非 HF/Vercel/Railway/Streamlit Cloud
