#!/bin/bash
# Luna Initial Installation Script (Fixed Version)
# Installs all dependencies, configures services, and prepares Luna for first run

set -e  # Exit on error

# Script directory (Luna repository root)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Virtual environment path
VENV_PATH="$SCRIPT_DIR/.venv"

# Configuration file path
CONFIG_FILE="$SCRIPT_DIR/install_config.json"

# --- Log Functions ---
log_info() { echo "[INFO] $1"; }
log_success() { echo "[OK] $1"; }
log_warn() { echo "[WARN] $1"; }
log_error() { echo "[ERROR] $1"; }
log_section() {
    echo ""
    echo "========================================"
    echo "$1"
    echo "========================================"
    echo ""
}

# --- Check Functions ---
check_root() {
    if [ "$EUID" -ne 0 ]; then
        log_error "This script must be run as root (use sudo)"
        exit 1
    fi
    if [ -z "$SUDO_USER" ]; then
        log_error "This script must be run with sudo, not directly as root."
        log_error "Please run as: sudo ./install.sh"
        exit 1
    fi
    log_success "Running as root (called by $SUDO_USER)"
}

load_config() {
    log_section "Loading Configuration"
    
    if [ ! -f "$CONFIG_FILE" ]; then
        log_error "Configuration file not found: $CONFIG_FILE"
        log_info "Please create install_config.json with the required structure."
        exit 1
    fi
    
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

check_system_requirements() {
    log_section "Checking System Requirements"
    
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        log_info "OS: $NAME $VERSION"
    else
        log_warn "Cannot detect OS version"
    fi
    
    AVAILABLE_SPACE=$(df -BG "$SCRIPT_DIR" | awk 'NR==2 {print $4}' | sed 's/G//')
    log_info "Available disk space: ${AVAILABLE_SPACE}GB"
    if [ "$AVAILABLE_SPACE" -lt 5 ]; then
        log_warn "Low disk space (< 5GB). Installation may fail."
    fi
    
    TOTAL_MEM=$(free -g | awk 'NR==2 {print $2}')
    log_info "Total memory: ${TOTAL_MEM}GB"
    if [ "$TOTAL_MEM" -lt 2 ]; then
        log_warn "Low memory (< 2GB). Luna may run slowly."
    fi
    
    log_success "System requirements checked"
}

# --- Installation Functions ---
install_system_packages() {
    log_section "Installing System Packages"
    log_info "Updating package lists..."
    apt-get update -qq
    
    log_info "Installing essential packages..."
    apt-get install -y \
        curl wget git build-essential lsof jq unzip \
        ca-certificates gnupg debian-keyring debian-archive-keyring apt-transport-https \
        software-properties-common
    
    log_success "System packages installed"
}

install_python() {
    log_section "Installing Python 3.11"
    
    if command -v python3.11 &> /dev/null; then
        log_success "Python 3.11 is already installed."
        return 0
    fi

    log_info "Installing Python 3.11..."
    
    # Add deadsnakes PPA for newer Python versions
    add-apt-repository -y ppa:deadsnakes/ppa
    apt-get update -qq
    
    # Install Python 3.11 and dependencies
    apt-get install -y \
        python3.11 \
        python3.11-dev \
        python3.11-venv \
        python3.11-distutils
    
    # *** CRITICAL FIX: ***
    # We DO NOT run `update-alternatives`.
    # This leaves the system's `python3` (3.10) as the default to protect `apt`.
    
    PYTHON_VERSION=$(python3.11 --version | awk '{print $2}')
    log_success "Python $PYTHON_VERSION installed successfully."
}

create_venv() {
    log_section "Creating Virtual Environment"
    
    if [ -d "$VENV_PATH" ]; then
        log_info "Virtual environment already exists. Removing and recreating..."
        rm -rf "$VENV_PATH"
    fi
    
    log_info "Creating virtual environment at $VENV_PATH..."
    
    # *** CRITICAL FIX: ***
    # We explicitly use `python3.11` to create the venv.
    python3.11 -m venv "$VENV_PATH"
    
    if [ -f "$VENV_PATH/bin/activate" ] && [ -f "$VENV_PATH/bin/python3" ]; then
        log_success "Virtual environment created successfully"
    else
        log_error "Failed to create virtual environment"
        exit 1
    fi
    
    # Set permissions for the venv now
    chown -R "$SUDO_USER:$SUDO_USER" "$VENV_PATH"
}

activate_venv_and_install_uv() {
    log_section "Installing uv Package Manager"
    
    log_info "Installing uv via pip (in venv)..."
    # Run pip as the $SUDO_USER to ensure correct permissions inside the venv
    sudo -u "$SUDO_USER" "$VENV_PATH/bin/pip" install --upgrade pip
    sudo -u "$SUDO_USER" "$VENV_PATH/bin/pip" install uv
    
    if sudo -u "$SUDO_USER" "$VENV_PATH/bin/pip" show uv &> /dev/null; then
        log_success "uv installed in venv"
    else
        log_error "uv installation failed"
        exit 1
    fi
}

install_nodejs() {
    log_section "Installing Node.js and npm"
    
    if command -v node &> /dev/null && command -v npm &> /dev/null; then
        NODE_VERSION=$(node --version)
        if [[ "$NODE_VERSION" == "v20"* ]]; then
            log_success "Node.js $NODE_VERSION and npm $(npm --version) already installed."
            return 0
        else
            log_warn "Found wrong Node.js version ($NODE_VERSION). Reinstalling v20..."
        fi
    fi
    
    log_info "Installing Node.js v20 (LTS)..."
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
    apt-get install -y nodejs
    
    log_success "Node.js $(node --version) and npm $(npm --version) installed"
}

install_pnpm() {
    log_section "Installing pnpm"
    
    if command -v pnpm &> /dev/null; then
        log_success "pnpm already installed: $(pnpm --version)"
        return 0
    fi
    
    log_info "Installing pnpm via npm..."
    npm install -g pnpm
    
    log_success "pnpm $(pnpm --version) installed"
}

install_ngrok() {
    log_section "Installing ngrok"
    
    if command -v ngrok &> /dev/null; then
        log_success "ngrok already installed: $(ngrok version | head -n1)"
    else
        log_info "Installing ngrok..."
        curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null
        echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | tee /etc/apt/sources.list.d/ngrok.list
        apt-get update -qq
        apt-get install -y ngrok
        log_success "ngrok $(ngrok version | head -n1) installed"
    fi
    
    if [ -n "$NGROK_API_KEY" ] && [ "$NGROK_API_KEY" != "null" ]; then
        log_info "Configuring ngrok with API key..."
        ngrok config add-authtoken "$NGROK_API_KEY"
        log_success "ngrok configured with authtoken"
    else
        log_warn "No ngrok API key provided, skipping authtoken setup"
    fi
}

install_caddy() {
    log_section "Installing Caddy"
    
    if command -v caddy &> /dev/null; then
        log_success "Caddy already installed: $(caddy version | head -n1)"
        return 0
    fi
    
    log_info "Installing Caddy..."
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list
    apt-get update -qq
    apt-get install -y caddy
    
    log_success "Caddy $(caddy version | head -n1) installed"
}

setup_caddy_auth() {
    log_section "Setting up Caddy Authentication"
    
    if [ -z "$CADDY_USERNAME" ] || [ -z "$CADDY_PASSWORD" ]; then
        log_warn "Caddy username or password not provided, skipping auth setup"
        return 0
    fi
    
    log_info "Generating bcrypt hash for password..."
    CADDY_HASH=$(caddy hash-password --plaintext "$CADDY_PASSWORD" 2>/dev/null)
    
    if [ -z "$CADDY_HASH" ]; then
        log_error "Failed to generate password hash"
        exit 1
    fi
    
    log_info "Creating Caddy auth file..."
    echo "$CADDY_USERNAME $CADDY_HASH" > "$SCRIPT_DIR/caddy_auth.txt"
    echo "" >> "$SCRIPT_DIR/caddy_auth.txt"
    chmod 600 "$SCRIPT_DIR/caddy_auth.txt"
    
    log_success "Caddy authentication configured (Username: $CADDY_USERNAME)"
}

install_docker() {
    log_section "Installing Docker"
    
    if command -v docker &> /dev/null; then
        log_success "Docker already installed: $(docker --version | awk '{print $3}' | sed 's/,//')"
    else
        log_info "Installing Docker..."
        apt-get remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true
        curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
        echo \
          "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
          $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
        apt-get update -qq
        apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
        log_success "Docker installed"
    fi
    
    if systemctl is-active --quiet docker; then
        log_success "Docker service is running"
    else
        log_info "Starting and enabling Docker service..."
        systemctl start docker
        systemctl enable docker
    fi
    
    if [ -n "$SUDO_USER" ]; then
        log_info "Adding $SUDO_USER to docker group..."
        usermod -aG docker "$SUDO_USER"
        log_warn "You may need to log out and back in for docker group membership to take effect"
    fi
}

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

setup_ngrok_service() {
    log_section "Setting up ngrok Auto-Start Service"
    
    if [ -z "$NGROK_DOMAIN" ] || [ "$NGROK_DOMAIN" = "null" ]; then
        log_warn "No ngrok domain configured, skipping ngrok service setup"
        return 0
    fi
    
    log_info "Creating ngrok systemd service..."
    
    cat > /etc/systemd/system/luna-ngrok.service <<EOF
[Unit]
Description=Luna ngrok Tunnel
After=network.target

[Service]
Type=simple
User=root
ExecStart=/usr/local/bin/ngrok http --domain=$NGROK_DOMAIN 8443
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    
    systemctl daemon-reload
    systemctl enable luna-ngrok
    systemctl start luna-ngrok
    
    log_success "ngrok service created and started"
    log_info "Check status: systemctl status luna-ngrok"
}

install_luna_dependencies() {
    log_section "Installing All Dependencies"
    
    log_info "Running install_deps.py (in venv as $SUDO_USER)..."
    log_info "This will install:"
    log_info "  - Core Python packages (uv)"
    log_info "  - Hub UI Node.js packages (pnpm)"
    log_info "  - Extension Python packages (uv)"
    log_info "  - Extension UI Node.js packages (pnpm)"
    echo ""
    
    cd "$SCRIPT_DIR"
    sudo -u "$SUDO_USER" "$VENV_PATH/bin/python3" core/scripts/install_deps.py
    
    if [ $? -eq 0 ]; then
        log_success "All dependencies installed successfully"
    else
        log_error "Dependency installation failed"
        exit 1
    fi
}


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

set_permissions() {
    log_section "Setting Permissions"
    
    log_info "Setting executable permissions..."
    find "$SCRIPT_DIR" -name "*.sh" -type f -exec chmod +x {} \;
    chmod +x "$SCRIPT_DIR/luna.sh"
    
    # Set proper ownership for the entire app directory
    if [ -n "$SUDO_USER" ]; then
        log_info "Setting ownership of all files to $SUDO_USER..."
        chown -R "$SUDO_USER:$SUDO_USER" "$SCRIPT_DIR"
    fi
    
    log_success "Permissions set"
}

setup_bootstrap_service() {
    log_section "Setting up Luna Auto-Start Service"
    
    log_info "Creating Luna bootstrap systemd service..."
    
    # *** CRITICAL FIX: ***
    # Run the service as the non-root user who ran `sudo`.
    # This prevents all file permission errors during runtime.
    cat > /etc/systemd/system/luna.service <<EOF
[Unit]
Description=Luna Personal Assistant
After=network.target
Wants=network.target

[Service]
Type=simple
User=$SUDO_USER
Group=$SUDO_USER
WorkingDirectory=$SCRIPT_DIR
Environment="LUNA_VENV=$VENV_PATH"
ExecStart=$SCRIPT_DIR/luna.sh
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
    
    systemctl daemon-reload
    systemctl enable luna
    systemctl start luna
    
    log_success "Luna bootstrap service created and started"
    log_info "Service: luna.service"
    log_info "Check status: systemctl status luna"
    
    log_info "Waiting 5s for services to start..."
    sleep 5
    
    if pgrep -f "supervisor/supervisor.py" > /dev/null 2>&1; then
        log_success "Supervisor is running"
    else
        log_warn "Supervisor may not have started. Check logs: journalctl -u luna -f"
    fi
}

print_summary() {
    log_section "Installation Complete!"
    
    echo "Luna has been installed and started successfully!"
    echo ""
    echo "Luna is now running as a systemd service and will auto-start on reboot."
    echo ""
    echo "Service management:"
    echo "  Start:   systemctl start luna"
    echo "  Stop:    systemctl stop luna"
    echo "  Restart: systemctl restart luna"
    echo "  Status:  systemctl status luna"
    echo "  Logs:    journalctl -u luna -f"
    echo ""
    echo "Ngrok tunnel:"
    echo "  Status:  systemctl status luna-ngrok"
    echo "  Logs:    journalctl -u luna-ngrok -f"
    echo ""
    echo "Installed components:"
    echo "  - System Python: $(python3 --version | awk '{print $2}')"
    echo "  - Venv Python:   $($VENV_PATH/bin/python3 --version | awk '{print $2}')"
    echo "  - Node.js:       $(node --version)"
    echo "  - pnpm:          $(pnpm --version)"
    echo "  - ngrok:         $(ngrok version | head -n1)"
    echo "  - Caddy:         $(caddy version | head -n1)"
    echo "  - Docker:        $(docker --version | awk '{print $3}' | sed 's/,//')"
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
    create_venv
    activate_venv_and_install_uv
    install_nodejs
    install_pnpm
    install_ngrok
    install_caddy
    setup_caddy_auth
    install_docker
    create_directories
    create_env_file
    
    # Set permissions *before* installing dependencies as the user
    set_permissions
    
    install_luna_dependencies
    
    # Setup auto-start services
    setup_ngrok_service
    setup_bootstrap_service
    
    # Print summary
    print_summary
}

# Run main installation
main