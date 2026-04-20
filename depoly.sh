#!/bin/bash
# ============================================================
# 本地 AI 助理系统 - Mac Studio 端一键部署脚本
# 适用环境：macOS (Apple Silicon)，已安装 Xcode Command Line Tools
# 功能：安装 Homebrew, Docker, Ollama, 并启动 n8n, Dify, Paperless-ngx, Open WebUI
# ============================================================

set -e  # 遇到错误立即退出

# ---------- 颜色定义 ----------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ---------- 辅助函数 ----------
print_step() {
    echo -e "\n${BLUE}▶ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

confirm() {
    read -p "$(echo -e "${YELLOW}? $1 (y/n) ${NC}")" -n 1 -r
    echo
    [[ $REPLY =~ ^[Yy]$ ]]
}

# ---------- 检查网络与科学上网 ----------
check_network() {
    print_step "检查网络连接及科学上网环境"
    if curl -s --max-time 5 https://hub.docker.com > /dev/null; then
        print_success "网络通畅，可访问 Docker Hub"
    else
        print_warning "无法访问 Docker Hub，请确保科学上网已开启（后续拉取镜像可能失败）"
        if ! confirm "是否继续？"; then
            exit 1
        fi
    fi
}

# ---------- 安装 Homebrew ----------
install_homebrew() {
    if command -v brew &> /dev/null; then
        print_success "Homebrew 已安装"
    else
        print_step "安装 Homebrew"
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        # 自动添加到 PATH（Apple Silicon 默认路径）
        echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
        eval "$(/opt/homebrew/bin/brew shellenv)"
        print_success "Homebrew 安装完成"
    fi
}

# ---------- 安装 Docker ----------
install_docker() {
    if command -v docker &> /dev/null; then
        print_success "Docker 已安装"
    else
        print_step "安装 Docker Desktop"
        brew install --cask docker
        print_warning "请手动启动 Docker Desktop 应用并完成初始化设置"
        open /Applications/Docker.app
        echo "等待 Docker 启动..."
        while ! docker system info > /dev/null 2>&1; do
            sleep 2
        done
        print_success "Docker 已就绪"
    fi
}

# ---------- 安装 Ollama ----------
install_ollama() {
    if command -v ollama &> /dev/null; then
        print_success "Ollama 已安装"
    else
        print_step "安装 Ollama"
        brew install ollama
        # 启动 Ollama 服务
        brew services start ollama
        print_success "Ollama 安装并启动"
    fi

    # 下载推荐模型 (Gemma2 27B)
    print_step "拉取推荐模型 gemma2:27b (约 16GB，耗时较长)"
    if ollama list | grep -q "gemma2:27b"; then
        print_success "模型 gemma2:27b 已存在"
    else
        ollama pull gemma2:27b
        print_success "模型 gemma2:27b 下载完成"
    fi
}

# ---------- 启动 n8n ----------
start_n8n() {
    print_step "启动 n8n 工作流引擎"
    if docker ps -a --format '{{.Names}}' | grep -q "^n8n$"; then
        print_success "n8n 容器已存在，跳过创建"
    else
        docker run -d \
            --name n8n \
            --restart unless-stopped \
            -p 5678:5678 \
            -v n8n_data:/home/node/.n8n \
            -e N8N_SECURE_COOKIE=false \
            n8nio/n8n
        print_success "n8n 已启动，访问 http://localhost:5678"
    fi
}

# ---------- 启动 Dify ----------
start_dify() {
    print_step "启动 Dify AI 编排平台"
    if [ -d "$HOME/dify" ]; then
        print_success "Dify 目录已存在"
    else
        git clone https://github.com/langgenius/dify.git "$HOME/dify"
    fi
    cd "$HOME/dify/docker"
    if [ ! -f ".env" ]; then
        cp .env.example .env
    fi
    docker compose up -d
    print_success "Dify 已启动，访问 http://localhost (默认端口80)"
    cd - > /dev/null
}

# ---------- 启动 Paperless-ngx ----------
start_paperless() {
    print_step "启动 Paperless-ngx 文档管理系统"
    if docker ps -a --format '{{.Names}}' | grep -q "paperless"; then
        print_success "Paperless-ngx 容器已存在"
    else
        # 使用官方一键安装脚本（自动生成 docker-compose）
        bash -c "$(curl --location --silent --show-error https://raw.githubusercontent.com/paperless-ngx/paperless-ngx/main/install-paperless-ngx.sh)"
        print_success "Paperless-ngx 已启动，访问 http://localhost:8000"
        print_warning "请编辑 ~/.paperless/paperless-ngx.env 配置消费目录指向 NAS 挂载点"
    fi
}

# ---------- 启动 Open WebUI ----------
start_openwebui() {
    print_step "启动 Open WebUI 统一交互界面"
    if docker ps -a --format '{{.Names}}' | grep -q "open-webui"; then
        print_success "Open WebUI 容器已存在"
    else
	docker run -d \
	  -p 3000:8080 \
	  --name open-webui \
	  --add-host=host.docker.internal:host-gateway \
	  -e OLLAMA_BASE_URL=http://host.docker.internal:11434 \
	  -e OPENAI_API_BASE_URLS="http://host.docker.internal:9080/v1;http://host.docker.internal:9081/v1;http://host.docker.internal:9082/v1" \
	  -e OPENAI_API_KEYS="ignored;ignored;ignored" \
	  -e WEBUI_AUTH=False \
	  --restart unless-stopped \
	  -v open-webui:/app/backend/data \
	  ghcr.io/open-webui/open-webui:main
        # docker run -d \
        #     -p 3000:8080 \
        #     --name open-webui \
        #     --restart unless-stopped \
        #     -v open-webui:/app/backend/data \
        #     -e OLLAMA_BASE_URL=http://host.docker.internal:11434 \
        #     ghcr.io/open-webui/open-webui:main
        print_success "Open WebUI 已启动，访问 http://localhost:3000"
    fi
}

# ---------- 配置 Dify 连接 Ollama ----------
configure_dify_ollama() {
    print_step "配置 Dify 连接本地 Ollama"
    cat <<EOF

${YELLOW}请手动完成以下步骤以连接 Dify 与 Ollama：${NC}
1. 访问 http://localhost/install 完成 Dify 初始化（设置管理员邮箱密码）
2. 登录后进入「设置」->「模型供应商」
3. 找到「Ollama」，点击「安装」
4. 点击「添加模型」，填写：
   - 基础 URL: http://host.docker.internal:11434
   - 模型名称: gemma2:27b
5. 点击保存

EOF
}

# ---------- 显示最终信息 ----------
show_summary() {
    echo -e "\n${GREEN}========================================${NC}"
    echo -e "${GREEN}     ð 部署完成！服务访问地址如下     ${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo -e "ð¹ n8n 工作流引擎:        ${BLUE}http://localhost:5678${NC}"
    echo -e "ð¹ Dify AI 编排平台:      ${BLUE}http://localhost${NC}"
    echo -e "ð¹ Paperless-ngx 文档库:  ${BLUE}http://localhost:8000${NC}"
    echo -e "ð¹ Open WebUI 交互界面:   ${BLUE}http://localhost:3000${NC}"
    echo -e "ð¹ Ollama API 服务:       ${BLUE}http://localhost:11434${NC}"
    echo -e "\n${YELLOW}ð 下一步建议：${NC}"
    echo -e "1. 将 NAS 文件夹挂载到 Mac，并在 Paperless-ngx 中设置为消费目录"
    echo -e "2. 在 n8n 中创建自动化工作流串联各服务"
    echo -e "3. 配置飞书机器人以接收指令和推送通知"
    echo -e "\n${GREEN}========================================${NC}"
}

# ---------- 主流程 ----------
main() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}    本地 AI 助理系统 - 一键部署脚本    ${NC}"
    echo -e "${BLUE}========================================${NC}"

    check_network
    install_homebrew
    install_docker
    install_ollama

    # 拉取必要 Docker 镜像（并行加速）
    print_step "预拉取 Docker 镜像"
    docker pull n8nio/n8n &
    docker pull ghcr.io/open-webui/open-webui:main &
    wait
    print_success "镜像拉取完成"

    start_n8n
    start_dify
    start_paperless
    start_openwebui

    configure_dify_ollama

    show_summary
}

main "$@"
