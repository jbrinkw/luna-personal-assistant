#!/bin/bash
# Luna Initial Installation Script
# Installs all dependencies, configures services, and prepares Luna for first run

set -e  # Exit on error

# Script directory (Luna repository root)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Configuration file path
CONFIG_FILE="$SCRIPT_DIR/install_config.json"

# Log functions
log_info() {
    echo "[INFO] $1"
}

log_success() {
    echo "[OK] $1"
}

log_warn() {
    echo "[WARN] $1"
}

log_error() {
    echo "[ERROR] $1"
}

log_section() {
    echo ""
    echo "========================================"
    echo "$1"
    echo "========================================"
    echo ""
}

# Check if running as root
check_root() {
    if [ "$EUID" -ne 0 ]; then
        log_error "This script must be run as root (use sudo)"
        exit 1
    fi
    log_success "Running as root"
}

# Load configuration from install_config.json
load_config() {
    log_section "Loading Configuration"
    
    if [ ! -f "$CONFIG_FILE" ]; then
        log_error "Configuration file not found: $CONFIG_FILE"
        log_info "Please create install_config.json with the following structure:"
        cat <<EOF
{
  "ngrok": {
    "api_key": "your_ngrok_api_key",
    "domain": "your-domain.ngrok-free.app"
  },
  "caddy": {
    "username": "admin",
    "password": "your_secure_password"
  }
}
EOF
        exit 1
    fi
    
    # Parse JSON (requires jq)
    if ! command -v jq &> /dev/null; then
        log_info "Installing jq for JSON parsing..."
        apt-get install -y jq
    fi
    
    NGROK_API_KEY=$(jq -r '.ngrok.api_key' "$CONFIG_FILE")
    NGROK_DOMAIN=$(jq -r '.ngrok.domain' "$CONFIG_FILE")
    CADDY_USERNAME=$(jq -r '.caddy.username' "$CONFIG_FILE")
    CADDY_PASSWORD=$(jq -r '.caddy.password' "$CONFIG_FILE")
    
    log_success "Configuration loaded"
    log_info "Ngrok domain: $NGROK_DOMAIN"
    log_info "Caddy username: $CADDY_USERNAME"
}

# Check system requirements
check_system_requirements() {
    log_section "Checking System Requirements"
    
    # Check OS
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        log_info "OS: $NAME $VERSION"
    else
        log_warn "Cannot detect OS version"
    fi
    
    # Check available disk space (need at least 5GB)
    AVAILABLE_SPACE=$(df -BG "$SCRIPT_DIR" | awk 'NR==2 {print $4}' | sed 's/G//')
    log_info "Available disk space: ${AVAILABLE_SPACE}GB"
    if [ "$AVAILABLE_SPACE" -lt 5 ]; then
        log_warn "Low disk space (< 5GB). Installation may fail."
    fi
    
    # Check memory (recommend at least 2GB)
    TOTAL_MEM=$(free -g | awk 'NR==2 {print $2}')
    log_info "Total memory: ${TOTAL_MEM}GB"
    if [ "$TOTAL_MEM" -lt 2 ]; then
        log_warn "Low memory (< 2GB). Luna may run slowly."
    fi
    
    log_success "System requirements checked"
}

# Install basic system packages
install_system_packages() {
    log_section "Installing System Packages"
    
    log_info "Updating package lists..."
    apt-get update -qq
    
    log_info "Installing essential packages..."
    apt-get install -y \
        curl \
        wget \
        git \
        build-essential \
        lsof \
        jq \
        unzip \
        ca-certificates \
        gnupg \
        debian-keyring \
        debian-archive-keyring \
        apt-transport-https
    
    log_success "System packages installed"
}

# Install Python 3.11.2+
install_python() {
    log_section "Installing Python"
    
    # Check if Python 3.11+ is already installed
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version | awk '{print $2}')
        PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
        PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)
        
        log_info "Found Python $PYTHON_VERSION"
        
        if [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -ge 11 ]; then
            log_success "Python $PYTHON_VERSION meets requirements (3.11.2+)"
            return 0
        else
            log_warn "Python $PYTHON_VERSION is too old (need 3.11.2+)"
        fi
    fi
    
    log_info "Installing Python 3.11..."
    
    # Add deadsnakes PPA for newer Python versions
    apt-get install -y software-properties-common
    add-apt-repository -y ppa:deadsnakes/ppa
    apt-get update -qq
    
    # Install Python 3.11 and dependencies
    apt-get install -y \
        python3.11 \
        python3.11-dev \
        python3.11-venv \
        python3.11-distutils \
        python3-pip
    
    # Set Python 3.11 as default python3
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
    
    # Verify installation
    PYTHON_VERSION=$(python3 --version | awk '{print $2}')
    log_success "Python $PYTHON_VERSION installed"
}

# Install uv package manager
install_uv() {
    log_section "Installing uv Package Manager"
    
    if command -v uv &> /dev/null; then
        UV_VERSION=$(uv --version)
        log_success "uv already installed: $UV_VERSION"
        return 0
    fi
    
    log_info "Installing uv via pip..."
    python3 -m pip install --upgrade pip
    python3 -m pip install uv
    
    # Verify installation
    if command -v uv &> /dev/null; then
        UV_VERSION=$(uv --version)
        log_success "uv installed: $UV_VERSION"
    else
        log_error "uv installation failed"
        exit 1
    fi
}

# Install Node.js and npm
install_nodejs() {
    log_section "Installing Node.js and npm"
    
    if command -v node &> /dev/null; then
        NODE_VERSION=$(node --version)
        log_info "Found Node.js $NODE_VERSION"
    else
        log_info "Installing Node.js..."
        
        # Install Node.js 20.x LTS
        curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
        apt-get install -y nodejs
        
        NODE_VERSION=$(node --version)
        log_success "Node.js $NODE_VERSION installed"
    fi
    
    # Verify npm is installed
    if command -v npm &> /dev/null; then
        NPM_VERSION=$(npm --version)
        log_success "npm $NPM_VERSION installed"
    else
        log_error "npm installation failed"
        exit 1
    fi
}

# Install pnpm
install_pnpm() {
    log_section "Installing pnpm"
    
    if command -v pnpm &> /dev/null; then
        PNPM_VERSION=$(pnpm --version)
        log_success "pnpm already installed: $PNPM_VERSION"
        return 0
    fi
    
    log_info "Installing pnpm via npm..."
    npm install -g pnpm
    
    # Verify installation
    if command -v pnpm &> /dev/null; then
        PNPM_VERSION=$(pnpm --version)
        log_success "pnpm $PNPM_VERSION installed"
    else
        log_error "pnpm installation failed"
        exit 1
    fi
}

# Install ngrok
install_ngrok() {
    log_section "Installing ngrok"
    
    if command -v ngrok &> /dev/null; then
        NGROK_VERSION=$(ngrok version)
        log_success "ngrok already installed: $NGROK_VERSION"
        return 0
    fi
    
    log_info "Installing ngrok..."
    
    # Download and install ngrok
    curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | \
        tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null
    echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | \
        tee /etc/apt/sources.list.d/ngrok.list
    apt-get update -qq
    apt-get install -y ngrok
    
    # Configure ngrok with API key
    if [ -n "$NGROK_API_KEY" ] && [ "$NGROK_API_KEY" != "null" ]; then
        log_info "Configuring ngrok with API key..."
        ngrok config add-authtoken "$NGROK_API_KEY"
        log_success "ngrok configured with authtoken"
    else
        log_warn "No ngrok API key provided, skipping authtoken setup"
    fi
    
    # Verify installation
    if command -v ngrok &> /dev/null; then
        NGROK_VERSION=$(ngrok version)
        log_success "ngrok $NGROK_VERSION installed"
    else
        log_error "ngrok installation failed"
        exit 1
    fi
}

# Install Caddy
install_caddy() {
    log_section "Installing Caddy"
    
    if command -v caddy &> /dev/null; then
        CADDY_VERSION=$(caddy version)
        log_success "Caddy already installed: $CADDY_VERSION"
        return 0
    fi
    
    log_info "Installing Caddy..."
    
    # Use existing install_caddy.sh script if available
    if [ -f "$SCRIPT_DIR/core/scripts/install_caddy.sh" ]; then
        bash "$SCRIPT_DIR/core/scripts/install_caddy.sh"
    else
        # Install Caddy manually
        curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | \
            gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
        curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | \
            tee /etc/apt/sources.list.d/caddy-stable.list
        apt-get update -qq
        apt-get install -y caddy
    fi
    
    # Verify installation
    if command -v caddy &> /dev/null; then
        CADDY_VERSION=$(caddy version)
        log_success "Caddy $CADDY_VERSION installed"
    else
        log_error "Caddy installation failed"
        exit 1
    fi
}

# Setup Caddy authentication
setup_caddy_auth() {
    log_section "Setting up Caddy Authentication"
    
    if [ -z "$CADDY_USERNAME" ] || [ -z "$CADDY_PASSWORD" ]; then
        log_warn "Caddy username or password not provided, skipping auth setup"
        return 0
    fi
    
    log_info "Generating bcrypt hash for password..."
    
    # Generate bcrypt hash using caddy hash-password
    CADDY_HASH=$(caddy hash-password --plaintext "$CADDY_PASSWORD" 2>/dev/null)
    
    if [ -z "$CADDY_HASH" ]; then
        log_error "Failed to generate password hash"
        exit 1
    fi
    
    log_info "Creating Caddy auth file..."
    
    # Create caddy_auth.txt with username and hash
    echo "$CADDY_USERNAME $CADDY_HASH" > "$SCRIPT_DIR/caddy_auth.txt"
    echo "" >> "$SCRIPT_DIR/caddy_auth.txt"
    
    # Set proper permissions
    chmod 600 "$SCRIPT_DIR/caddy_auth.txt"
    
    log_success "Caddy authentication configured"
    log_info "Username: $CADDY_USERNAME"
}

# Install Docker
install_docker() {
    log_section "Installing Docker"
    
    if command -v docker &> /dev/null; then
        DOCKER_VERSION=$(docker --version | awk '{print $3}' | sed 's/,//')
        log_success "Docker already installed: $DOCKER_VERSION"
        
        # Check if service is running
        if systemctl is-active --quiet docker; then
            log_success "Docker service is running"
        else
            log_info "Starting Docker service..."
            systemctl start docker
            systemctl enable docker
        fi
        return 0
    fi
    
    log_info "Installing Docker..."
    
    # Remove old versions if any
    apt-get remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true
    
    # Install prerequisites
    apt-get install -y \
        apt-transport-https \
        ca-certificates \
        curl \
        gnupg \
        lsb-release
    
    # Add Docker's official GPG key
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
    
    # Set up the stable repository
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
      $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
    
    # Install Docker Engine
    apt-get update -qq
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    
    # Start and enable service
    systemctl start docker
    systemctl enable docker
    
    # Add current user to docker group if not root
    if [ -n "$SUDO_USER" ]; then
        log_info "Adding $SUDO_USER to docker group..."
        usermod -aG docker "$SUDO_USER"
        log_warn "You may need to log out and back in for docker group membership to take effect"
    fi
    
    # Verify installation
    if command -v docker &> /dev/null; then
        DOCKER_VERSION=$(docker --version | awk '{print $3}' | sed 's/,//')
        log_success "Docker $DOCKER_VERSION installed and running"
    else
        log_error "Docker installation failed"
        exit 1
    fi
}

# Create .env file
create_env_file() {
    log_section "Creating .env File"
    
    ENV_FILE="$SCRIPT_DIR/.env"
    
    if [ -f "$ENV_FILE" ]; then
        log_warn ".env file already exists, backing up to .env.backup"
        cp "$ENV_FILE" "$ENV_FILE.backup"
    fi
    
    log_info "Creating .env file..."
    
    cat > "$ENV_FILE" <<EOF
# Luna Environment Configuration
# Generated by install.sh on $(date)

# Ngrok Tunnel
NGROK_AUTHTOKEN=$NGROK_API_KEY
TUNNEL_HOST=$NGROK_DOMAIN
EOF
    
    chmod 600 "$ENV_FILE"
    
    log_success ".env file created at $ENV_FILE"
}

# Start ngrok tunnel
start_ngrok() {
    log_section "Starting ngrok Tunnel"
    
    if [ -z "$NGROK_DOMAIN" ] || [ "$NGROK_DOMAIN" = "null" ]; then
        log_warn "No ngrok domain configured, skipping ngrok startup"
        return 0
    fi
    
    # Check if ngrok is already running
    if pgrep -f "ngrok http" > /dev/null 2>&1; then
        log_info "ngrok is already running"
        return 0
    fi
    
    log_info "Starting ngrok tunnel on domain: $NGROK_DOMAIN"
    
    # Start ngrok in background
    nohup ngrok http --domain="$NGROK_DOMAIN" 8443 > "$SCRIPT_DIR/logs/ngrok.log" 2>&1 &
    NGROK_PID=$!
    
    log_success "ngrok started with PID: $NGROK_PID"
    log_info "Tunnel URL: https://$NGROK_DOMAIN"
    log_info "ngrok logs: $SCRIPT_DIR/logs/ngrok.log"
    
    # Wait a moment for ngrok to establish connection
    sleep 3
}

# Install Luna dependencies
install_luna_dependencies() {
    log_section "Installing Luna Dependencies"
    
    log_info "Running install_deps.py..."
    
    cd "$SCRIPT_DIR"
    python3 core/scripts/install_deps.py
    
    if [ $? -eq 0 ]; then
        log_success "Luna dependencies installed successfully"
    else
        log_error "Luna dependency installation failed"
        exit 1
    fi
}

# Install Hub UI dependencies
install_hub_ui_dependencies() {
    log_section "Installing Hub UI Dependencies"
    
    HUB_UI_DIR="$SCRIPT_DIR/hub_ui"
    
    if [ ! -d "$HUB_UI_DIR" ]; then
        log_warn "hub_ui directory not found, skipping"
        return 0
    fi
    
    if [ ! -f "$HUB_UI_DIR/package.json" ]; then
        log_warn "hub_ui/package.json not found, skipping"
        return 0
    fi
    
    log_info "Installing Hub UI dependencies with pnpm..."
    cd "$HUB_UI_DIR"
    pnpm install
    
    if [ $? -eq 0 ]; then
        log_success "Hub UI dependencies installed"
    else
        log_error "Hub UI dependency installation failed"
        exit 1
    fi
    
    cd "$SCRIPT_DIR"
}

# Create necessary directories
create_directories() {
    log_section "Creating Directories"
    
    log_info "Creating Luna directories..."
    
    mkdir -p "$SCRIPT_DIR/logs"
    mkdir -p "$SCRIPT_DIR/.luna"
    mkdir -p "$SCRIPT_DIR/supervisor"
    mkdir -p "$SCRIPT_DIR/core/scripts"
    mkdir -p "$SCRIPT_DIR/extensions"
    mkdir -p "$SCRIPT_DIR/external_services"
    
    log_success "Directories created"
}

# Set file permissions
set_permissions() {
    log_section "Setting Permissions"
    
    log_info "Setting executable permissions..."
    
    # Make shell scripts executable
    find "$SCRIPT_DIR" -name "*.sh" -type f -exec chmod +x {} \;
    
    # Make luna.sh executable
    chmod +x "$SCRIPT_DIR/luna.sh"
    
    # Set proper ownership (assuming running as root, set to calling user)
    if [ -n "$SUDO_USER" ]; then
        log_info "Setting ownership to $SUDO_USER..."
        chown -R "$SUDO_USER:$SUDO_USER" "$SCRIPT_DIR"
    fi
    
    log_success "Permissions set"
}

# Start bootstrap
start_bootstrap() {
    log_section "Starting Luna Bootstrap"
    
    # Check if bootstrap is already running
    if pgrep -f "supervisor/supervisor.py" > /dev/null 2>&1; then
        log_info "Luna is already running"
        return 0
    fi
    
    log_info "Starting Luna bootstrap..."
    
    cd "$SCRIPT_DIR"
    
    # Start luna.sh in background
    nohup ./luna.sh > "$SCRIPT_DIR/logs/luna_startup.log" 2>&1 &
    LUNA_PID=$!
    
    log_success "Luna bootstrap started with PID: $LUNA_PID"
    log_info "Startup logs: $SCRIPT_DIR/logs/luna_startup.log"
    
    # Wait for services to start
    log_info "Waiting for services to start..."
    sleep 5
    
    # Check if supervisor is running
    if pgrep -f "supervisor/supervisor.py" > /dev/null 2>&1; then
        log_success "Supervisor is running"
    else
        log_warn "Supervisor may not have started. Check logs: tail -f $SCRIPT_DIR/logs/bootstrap.log"
    fi
}

# Print summary
print_summary() {
    log_section "Installation Complete!"
    
    echo "Luna has been installed and started successfully!"
    echo ""
    echo "Luna is now running in the background."
    echo ""
    echo "To stop Luna:"
    echo "  ./scripts/kill_luna.sh"
    echo ""
    echo "To view logs:"
    echo "  tail -f logs/bootstrap.log"
    echo "  tail -f logs/supervisor.log"
    echo ""
    echo "Installed components:"
    echo "  - Python $(python3 --version | awk '{print $2}')"
    echo "  - uv $(uv --version 2>/dev/null || echo 'package manager')"
    echo "  - Node.js $(node --version)"
    echo "  - pnpm $(pnpm --version)"
    echo "  - ngrok $(ngrok version | head -n1)"
    echo "  - Caddy $(caddy version | head -n1)"
    echo "  - Docker $(docker --version | awk '{print $3}' | sed 's/,//')"
    echo ""
    echo "Service URLs (when running):"
    echo "  - Hub UI:     http://127.0.0.1:5173"
    echo "  - Agent API:  http://127.0.0.1:8080"
    echo "  - MCP Server: http://127.0.0.1:8765"
    echo "  - Supervisor: http://127.0.0.1:9999"
    if [ -n "$NGROK_DOMAIN" ] && [ "$NGROK_DOMAIN" != "null" ]; then
        echo "  - Public URL: https://$NGROK_DOMAIN"
    fi
    echo ""
    echo "Note: Luna and ngrok are running but will NOT auto-restart on reboot."
    echo "To manually restart: cd $SCRIPT_DIR && ./luna.sh"
    echo ""
}

# Main installation flow
main() {
    cat <<'EOF'
==============================================================
              Luna Personal Assistant
              Initial Installation Script
==============================================================
EOF
    
    # Run installation steps
    check_root
    load_config
    check_system_requirements
    install_system_packages
    install_python
    install_uv
    install_nodejs
    install_pnpm
    install_ngrok
    install_caddy
    setup_caddy_auth
    install_docker
    create_directories
    create_env_file
    install_luna_dependencies
    install_hub_ui_dependencies
    set_permissions
    
    # Start services
    start_ngrok
    start_bootstrap
    
    # Print summary
    print_summary
}

# Run main installation
main

