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
    
    if ! command -v jq &> /dev/null; then
        log_info "Installing jq for JSON parsing..."
        apt-get install -y jq
    fi
    
    # Create minimal config file if it doesn't exist
    if [ ! -f "$CONFIG_FILE" ]; then
        log_warn "Configuration file not found, creating minimal config..."
        cat > "$CONFIG_FILE" <<'EOF'
{
  "deployment_mode": "",
  "ngrok": {
    "api_key": "",
    "domain": ""
  },
  "nip_io": {},
  "custom_domain": {
    "domain": "",
    "use_cloudflare_tunnel": false
  },
  "github_oauth": {
    "client_id": "",
    "client_secret": "",
    "allowed_username": ""
  }
}
EOF
        log_success "Created install_config.json - you will be prompted for required values"
    fi
    
    # Load deployment mode
    DEPLOYMENT_MODE=$(jq -r '.deployment_mode // ""' "$CONFIG_FILE")
    
    # Prompt for deployment mode if not set
    if [ -z "$DEPLOYMENT_MODE" ] || [ "$DEPLOYMENT_MODE" = "null" ] || [ "$DEPLOYMENT_MODE" = "" ]; then
        log_warn "Deployment mode is not set in install_config.json"
        echo ""
        echo "========================================"
        echo "Select Deployment Mode"
        echo "========================================"
        echo ""
        echo "1) ngrok       - Tunnel mode for home networks without port forwarding"
        echo "                 (uses ngrok service, easiest setup)"
        echo ""
        echo "2) nip_io      - Cloud VPS mode with auto-detected public IP"
        echo "                 (requires open ports 80/443 for Let's Encrypt SSL)"
        echo ""
        echo "3) custom_domain - Production mode with your own domain"
        echo "                   (requires open ports 80/443 and manual DNS setup)"
        echo "                   (optionally use Cloudflare Tunnel instead of direct access)"
        echo ""
        read -p "Enter your choice (1-3): " -r DEPLOY_CHOICE
        echo ""
        
        case "$DEPLOY_CHOICE" in
            1)
                DEPLOYMENT_MODE="ngrok"
                log_info "Selected: ngrok tunnel mode"
                ;;
            2)
                DEPLOYMENT_MODE="nip_io"
                log_info "Selected: nip.io mode (auto-detected IP)"
                ;;
            3)
                DEPLOYMENT_MODE="custom_domain"
                log_info "Selected: custom domain mode"
                ;;
            *)
                log_error "Invalid choice. Please select 1, 2, or 3"
                exit 1
                ;;
        esac
        
        # Update config file with deployment mode
        log_info "Updating install_config.json with deployment mode..."
        TMP_CONFIG=$(mktemp)
        jq --arg mode "$DEPLOYMENT_MODE" '.deployment_mode = $mode' "$CONFIG_FILE" > "$TMP_CONFIG"
        mv "$TMP_CONFIG" "$CONFIG_FILE"
    fi
    
    # Load mode-specific configuration
    NGROK_API_KEY=$(jq -r '.ngrok.api_key // ""' "$CONFIG_FILE")
    NGROK_DOMAIN=$(jq -r '.ngrok.domain // ""' "$CONFIG_FILE")
    CUSTOM_DOMAIN=$(jq -r '.custom_domain.domain // ""' "$CONFIG_FILE")
    USE_CLOUDFLARE_TUNNEL=$(jq -r 'if .custom_domain.use_cloudflare_tunnel == true then "true" else "false" end' "$CONFIG_FILE")
    
    log_success "Configuration loaded"
    log_info "Deployment mode: $DEPLOYMENT_MODE"
    
    # Validate and prompt for deployment mode-specific fields
    case "$DEPLOYMENT_MODE" in
        ngrok)
            # Check for ngrok API key
            if [ -z "$NGROK_API_KEY" ] || [ "$NGROK_API_KEY" = "null" ] || [ "$NGROK_API_KEY" = "your_ngrok_api_key_here" ]; then
                log_warn "ngrok API key is not set"
                echo ""
                echo "You need an ngrok API key to use tunnel mode."
                echo "Sign up at: https://dashboard.ngrok.com/signup"
                echo "Find your authtoken at: https://dashboard.ngrok.com/get-started/your-authtoken"
                echo ""
                read -p "Enter your ngrok API key: " NGROK_API_KEY
                echo ""
                
                if [ -z "$NGROK_API_KEY" ]; then
                    log_error "ngrok API key cannot be empty for ngrok mode"
                    exit 1
                fi
                
                # Update config file
                TMP_CONFIG=$(mktemp)
                jq --arg key "$NGROK_API_KEY" '.ngrok.api_key = $key' "$CONFIG_FILE" > "$TMP_CONFIG"
                mv "$TMP_CONFIG" "$CONFIG_FILE"
            fi
            
            # Check for ngrok domain
            if [ -z "$NGROK_DOMAIN" ] || [ "$NGROK_DOMAIN" = "null" ] || [ "$NGROK_DOMAIN" = "your-domain.ngrok-free.app" ] || [ "$NGROK_DOMAIN" = "" ]; then
                log_warn "ngrok domain is not set"
                echo ""
                echo "You need a static ngrok domain (available on free plan)."
                echo "Claim a free domain at: https://dashboard.ngrok.com/domains"
                echo "Example: my-luna-app.ngrok-free.app"
                echo ""
                read -p "Enter your ngrok domain: " NGROK_DOMAIN
                echo ""
                
                if [ -z "$NGROK_DOMAIN" ]; then
                    log_error "ngrok domain cannot be empty for ngrok mode"
                    exit 1
                fi
                
                # Update config file
                TMP_CONFIG=$(mktemp)
                jq --arg domain "$NGROK_DOMAIN" '.ngrok.domain = $domain' "$CONFIG_FILE" > "$TMP_CONFIG"
                mv "$TMP_CONFIG" "$CONFIG_FILE"
            fi
            
            log_info "ngrok domain: $NGROK_DOMAIN"
            ;;
            
        nip_io)
            log_info "Using nip.io magic DNS (IP will be auto-detected)"
            echo ""
            log_warn "IMPORTANT: Make sure ports 80 and 443 are open on your firewall"
            log_warn "Let's Encrypt needs these ports to provision SSL certificates"
            echo ""
            read -p "Press Enter to continue once ports are confirmed open..."
            ;;
            
        custom_domain)
            # Check for custom domain
            if [ -z "$CUSTOM_DOMAIN" ] || [ "$CUSTOM_DOMAIN" = "null" ] || [ "$CUSTOM_DOMAIN" = "lunahub.dev" ] || [ "$CUSTOM_DOMAIN" = "" ]; then
                log_warn "Custom domain is not set"
                echo ""
                echo "Enter the domain name you want to use for Luna."
                echo "Example: luna.yourdomain.com"
                echo ""
                echo "IMPORTANT: Before continuing, you must:"
                echo "  1. Create an A record in your DNS provider"
                echo "  2. Point it to this server's public IP address"
                echo "  3. Wait for DNS propagation (usually 5-10 minutes)"
                echo ""
                read -p "Enter your custom domain: " CUSTOM_DOMAIN
                echo ""
                
                if [ -z "$CUSTOM_DOMAIN" ]; then
                    log_error "Custom domain cannot be empty for custom_domain mode"
                    exit 1
                fi
                
                # Update config file
                TMP_CONFIG=$(mktemp)
                jq --arg domain "$CUSTOM_DOMAIN" '.custom_domain.domain = $domain' "$CONFIG_FILE" > "$TMP_CONFIG"
                mv "$TMP_CONFIG" "$CONFIG_FILE"
            fi
            
            log_info "Custom domain: $CUSTOM_DOMAIN"
            echo ""
            
            # Ask if using Cloudflare Tunnel
            if [ "$USE_CLOUDFLARE_TUNNEL" != "true" ] && [ "$USE_CLOUDFLARE_TUNNEL" != "false" ]; then
                echo "Do you want to use Cloudflare Tunnel to expose this domain?"
                echo "  - Yes: Cloudflare handles TLS, no need to open ports 80/443"
                echo "  - No:  Direct access, requires ports 80/443 open and DNS A record"
                echo ""
                read -p "Use Cloudflare Tunnel? (y/N): " -r USE_TUNNEL_RESPONSE
                echo ""
                
                if [[ $USE_TUNNEL_RESPONSE =~ ^[Yy]$ ]]; then
                    USE_CLOUDFLARE_TUNNEL="true"
                else
                    USE_CLOUDFLARE_TUNNEL="false"
                fi
                
                # Update config file
                TMP_CONFIG=$(mktemp)
                if [ "$USE_CLOUDFLARE_TUNNEL" = "true" ]; then
                    jq '.custom_domain.use_cloudflare_tunnel = true' "$CONFIG_FILE" > "$TMP_CONFIG"
                else
                    jq '.custom_domain.use_cloudflare_tunnel = false' "$CONFIG_FILE" > "$TMP_CONFIG"
                fi
                mv "$TMP_CONFIG" "$CONFIG_FILE"
            fi
            
            if [ "$USE_CLOUDFLARE_TUNNEL" = "true" ]; then
                log_info "Using Cloudflare Tunnel for domain exposure"
                echo ""
                log_warn "IMPORTANT: You must configure Cloudflare Tunnel separately:"
                log_warn "  1. Set up Cloudflare Tunnel in Cloudflare Zero Trust dashboard"
                log_warn "  2. Configure tunnel to forward to http://localhost:80"
                log_warn "  3. Set the hostname to: $CUSTOM_DOMAIN"
                echo ""
                read -p "Press Enter to continue once Cloudflare Tunnel is configured..."
            else
                log_warn "IMPORTANT: Make sure ports 80 and 443 are open on your firewall"
                log_warn "Make sure your domain's A record points to this server's public IP"
                echo ""
                read -p "Press Enter to continue once DNS and firewall are configured..."
            fi
            ;;
            
        *)
            log_error "Invalid deployment_mode: $DEPLOYMENT_MODE"
            log_error "Valid options: ngrok, nip_io, custom_domain"
            exit 1
            ;;
    esac
    
    # Determine PUBLIC_DOMAIN based on deployment mode before GitHub OAuth setup
    case "$DEPLOYMENT_MODE" in
        ngrok)
            PUBLIC_DOMAIN="$NGROK_DOMAIN"
            ;;
        nip_io)
            # Detect public IP for nip.io
            log_info "Detecting public IP for nip.io domain..."
            PUBLIC_IP=$(curl -s --max-time 5 ifconfig.me 2>/dev/null || curl -s --max-time 5 icanhazip.com 2>/dev/null || curl -s --max-time 5 api.ipify.org 2>/dev/null)
            if [ -z "$PUBLIC_IP" ]; then
                log_error "Failed to detect public IP address"
                log_error "Please check your internet connection"
                exit 1
            fi
            PUBLIC_DOMAIN="${PUBLIC_IP}.nip.io"
            log_success "Detected public domain: $PUBLIC_DOMAIN"
            ;;
        custom_domain)
            PUBLIC_DOMAIN="$CUSTOM_DOMAIN"
            ;;
        *)
            PUBLIC_DOMAIN="localhost:5173"
            ;;
    esac
    
    # GitHub OAuth Setup (Required - TWO OAuth Apps)
    GITHUB_CLIENT_ID=$(jq -r '.github_oauth.client_id // ""' "$CONFIG_FILE")
    GITHUB_CLIENT_SECRET=$(jq -r '.github_oauth.client_secret // ""' "$CONFIG_FILE")
    MCP_GITHUB_CLIENT_ID=$(jq -r '.mcp_oauth.client_id // ""' "$CONFIG_FILE")
    MCP_GITHUB_CLIENT_SECRET=$(jq -r '.mcp_oauth.client_secret // ""' "$CONFIG_FILE")
    ALLOWED_GITHUB_USERNAME=$(jq -r '.github_oauth.allowed_username // ""' "$CONFIG_FILE")
    
    if [ -z "$GITHUB_CLIENT_ID" ] || [ "$GITHUB_CLIENT_ID" = "null" ] || [ "$GITHUB_CLIENT_ID" = "" ] || \
       [ -z "$GITHUB_CLIENT_SECRET" ] || [ "$GITHUB_CLIENT_SECRET" = "null" ] || [ "$GITHUB_CLIENT_SECRET" = "" ] || \
       [ -z "$MCP_GITHUB_CLIENT_ID" ] || [ "$MCP_GITHUB_CLIENT_ID" = "null" ] || [ "$MCP_GITHUB_CLIENT_ID" = "" ] || \
       [ -z "$MCP_GITHUB_CLIENT_SECRET" ] || [ "$MCP_GITHUB_CLIENT_SECRET" = "null" ] || [ "$MCP_GITHUB_CLIENT_SECRET" = "" ] || \
       [ -z "$ALLOWED_GITHUB_USERNAME" ] || [ "$ALLOWED_GITHUB_USERNAME" = "null" ] || [ "$ALLOWED_GITHUB_USERNAME" = "" ]; then
        log_warn "GitHub OAuth is not fully configured in install_config.json"
        echo ""
        echo "============================================================"
        echo "GitHub OAuth Setup (Required - Two OAuth Apps)"
        echo "============================================================"
        echo ""
        echo "Luna requires TWO separate GitHub OAuth applications:"
        echo ""
        echo "  1. Hub UI OAuth - For web interface login"
        echo "  2. MCP OAuth     - For Claude/AI assistant connections"
        echo ""
        echo "Why two apps? They use different callback URLs and serve"
        echo "different purposes. This is the standard architecture."
        echo ""
        echo "Your Luna domain: https://$PUBLIC_DOMAIN"
        echo ""
        echo "============================================================"
        echo "STEP 1: Create Hub UI OAuth App"
        echo "============================================================"
        echo ""
        echo "This app authenticates YOU when you log into Luna's web interface."
        echo ""
        echo "To set up Hub UI OAuth:"
        echo "  1. Go to: https://github.com/settings/developers"
        echo "  2. Click 'New OAuth App'"
        echo "  3. Application name: Luna Hub UI"
        echo "  4. Homepage URL: https://$PUBLIC_DOMAIN"
        echo "  5. Authorization callback URL: https://$PUBLIC_DOMAIN/auth/callback"
        echo "  6. Click 'Register application'"
        echo "  7. Copy your Client ID and generate a Client Secret"
        echo ""
        echo "IMPORTANT: Note the callback URL is /auth/callback"
        echo ""
        read -p "Press Enter once you have your Hub UI OAuth credentials ready..."
        echo ""
        
        if [ -z "$GITHUB_CLIENT_ID" ] || [ "$GITHUB_CLIENT_ID" = "null" ] || [ "$GITHUB_CLIENT_ID" = "" ]; then
            read -p "Hub UI OAuth Client ID: " GITHUB_CLIENT_ID
            echo ""
        fi
        
        if [ -z "$GITHUB_CLIENT_SECRET" ] || [ "$GITHUB_CLIENT_SECRET" = "null" ] || [ "$GITHUB_CLIENT_SECRET" = "" ]; then
            read -p "Hub UI OAuth Client Secret: " GITHUB_CLIENT_SECRET
            echo ""
        fi
        
        echo "============================================================"
        echo "STEP 2: Create MCP OAuth App"
        echo "============================================================"
        echo ""
        echo "This app authenticates Claude/AI assistants connecting to your tools."
        echo ""
        echo "To set up MCP OAuth:"
        echo "  1. Go to: https://github.com/settings/developers (same page)"
        echo "  2. Click 'New OAuth App' again"
        echo "  3. Application name: Luna MCP Server"
        echo "  4. Homepage URL: https://$PUBLIC_DOMAIN"
        echo "  5. Authorization callback URL: https://$PUBLIC_DOMAIN/api/auth/callback"
        echo "  6. Click 'Register application'"
        echo "  7. Copy your Client ID and generate a Client Secret"
        echo ""
        echo "IMPORTANT: Note the callback URL is /api/auth/callback (different!)"
        echo ""
        read -p "Press Enter once you have your MCP OAuth credentials ready..."
        echo ""
        
        if [ -z "$MCP_GITHUB_CLIENT_ID" ] || [ "$MCP_GITHUB_CLIENT_ID" = "null" ] || [ "$MCP_GITHUB_CLIENT_ID" = "" ]; then
            read -p "MCP OAuth Client ID: " MCP_GITHUB_CLIENT_ID
            echo ""
        fi
        
        if [ -z "$MCP_GITHUB_CLIENT_SECRET" ] || [ "$MCP_GITHUB_CLIENT_SECRET" = "null" ] || [ "$MCP_GITHUB_CLIENT_SECRET" = "" ]; then
            read -p "MCP OAuth Client Secret: " MCP_GITHUB_CLIENT_SECRET
            echo ""
        fi
        
        if [ -z "$ALLOWED_GITHUB_USERNAME" ] || [ "$ALLOWED_GITHUB_USERNAME" = "null" ] || [ "$ALLOWED_GITHUB_USERNAME" = "" ]; then
            while true; do
                read -p "Your GitHub username (only this user will be allowed access): " ALLOWED_GITHUB_USERNAME
                echo ""
                
                if [ -z "$ALLOWED_GITHUB_USERNAME" ]; then
                    log_error "GitHub username cannot be empty"
                    continue
                fi
                
                # Validate that the GitHub username exists
                log_info "Validating GitHub username..."
                HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "https://api.github.com/users/$ALLOWED_GITHUB_USERNAME")
                
                if [ "$HTTP_CODE" = "200" ]; then
                    log_success "GitHub username '$ALLOWED_GITHUB_USERNAME' validated"
                    break
                elif [ "$HTTP_CODE" = "404" ]; then
                    log_error "GitHub user '$ALLOWED_GITHUB_USERNAME' not found. Please enter a valid GitHub username."
                    echo ""
                else
                    log_error "Failed to validate GitHub username (HTTP $HTTP_CODE). Please check your internet connection."
                    echo ""
                fi
            done
        fi
        
        if [ -z "$GITHUB_CLIENT_ID" ] || [ -z "$GITHUB_CLIENT_SECRET" ] || \
           [ -z "$MCP_GITHUB_CLIENT_ID" ] || [ -z "$MCP_GITHUB_CLIENT_SECRET" ] || \
           [ -z "$ALLOWED_GITHUB_USERNAME" ]; then
            log_error "GitHub OAuth setup is incomplete"
            exit 1
        fi
        
        # Update config file
        TMP_CONFIG=$(mktemp)
        jq --arg hub_id "$GITHUB_CLIENT_ID" \
           --arg hub_secret "$GITHUB_CLIENT_SECRET" \
           --arg mcp_id "$MCP_GITHUB_CLIENT_ID" \
           --arg mcp_secret "$MCP_GITHUB_CLIENT_SECRET" \
           --arg user "$ALLOWED_GITHUB_USERNAME" \
           '.github_oauth.client_id = $hub_id | 
            .github_oauth.client_secret = $hub_secret | 
            .github_oauth.allowed_username = $user |
            .mcp_oauth.client_id = $mcp_id |
            .mcp_oauth.client_secret = $mcp_secret' \
           "$CONFIG_FILE" > "$TMP_CONFIG"
        mv "$TMP_CONFIG" "$CONFIG_FILE"
        
        log_success "GitHub OAuth configured"
        log_info "Hub UI OAuth: $GITHUB_CLIENT_ID"
        log_info "MCP OAuth: $MCP_GITHUB_CLIENT_ID"
        log_info "Only '$ALLOWED_GITHUB_USERNAME' will be allowed to access Luna"
    else
        # Validate existing username
        log_info "Validating allowed GitHub username: $ALLOWED_GITHUB_USERNAME"
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "https://api.github.com/users/$ALLOWED_GITHUB_USERNAME")
        
        if [ "$HTTP_CODE" = "200" ]; then
            log_success "GitHub username validated"
        else
            log_warn "Saved GitHub username '$ALLOWED_GITHUB_USERNAME' could not be validated"
        fi
        
        log_info "GitHub OAuth already configured"
        log_info "Hub UI OAuth: ${GITHUB_CLIENT_ID:0:20}..."
        log_info "MCP OAuth: ${MCP_GITHUB_CLIENT_ID:0:20}..."
        log_info "Allowed user: $ALLOWED_GITHUB_USERNAME"
    fi

    # Timezone Configuration
    TIMEZONE=$(jq -r '.timezone // ""' "$CONFIG_FILE")

    if [ -z "$TIMEZONE" ] || [ "$TIMEZONE" = "null" ] || [ "$TIMEZONE" = "" ]; then
        log_warn "Timezone is not configured in install_config.json"
        echo ""
        echo "============================================================"
        echo "Timezone Configuration"
        echo "============================================================"
        echo ""
        echo "Luna supports timezone-aware date calculations for features"
        echo "like meal planning and daily summaries."
        echo ""
        echo "Supported timezone codes (3-letter format):"
        echo "  EST/EDT - Eastern Time (New York)"
        echo "  CST/CDT - Central Time (Chicago)"
        echo "  MST/MDT - Mountain Time (Denver)"
        echo "  PST/PDT - Pacific Time (Los Angeles)"
        echo "  AST/ADT - Atlantic Time (Halifax)"
        echo "  HST     - Hawaii-Aleutian Time (Honolulu)"
        echo "  AKST/AKDT - Alaska Time (Anchorage)"
        echo ""
        echo "You can also enter a full IANA timezone name (e.g., America/New_York)"
        echo "or leave empty to use server's local timezone."
        echo ""

        while true; do
            read -p "Enter your timezone (e.g., EST, PST) [leave empty for local]: " TIMEZONE
            echo ""

            # Allow empty input
            if [ -z "$TIMEZONE" ]; then
                log_info "Using server's local timezone"
                TIMEZONE=""
                break
            fi

            # Convert to uppercase for validation
            TIMEZONE_UPPER=$(echo "$TIMEZONE" | tr '[:lower:]' '[:upper:]')

            # List of valid 3-letter timezone codes
            VALID_TIMEZONES="EST EDT CST CDT MST MDT PST PDT AST ADT HST AKST AKDT"

            # Check if it's a valid 3-letter code
            if echo "$VALID_TIMEZONES" | grep -qw "$TIMEZONE_UPPER"; then
                TIMEZONE="$TIMEZONE_UPPER"
                log_success "Timezone set to $TIMEZONE"
                break
            # Check if it looks like an IANA timezone (contains /)
            elif [[ "$TIMEZONE" == */* ]]; then
                log_info "Using IANA timezone: $TIMEZONE"
                break
            else
                log_error "Invalid timezone code: $TIMEZONE"
                log_error "Please enter one of: $VALID_TIMEZONES"
                log_error "Or enter a full IANA timezone name (e.g., America/New_York)"
                echo ""
            fi
        done

        # Update config file
        TMP_CONFIG=$(mktemp)
        jq --arg tz "$TIMEZONE" \
           '.timezone = $tz' \
           "$CONFIG_FILE" > "$TMP_CONFIG"
        mv "$TMP_CONFIG" "$CONFIG_FILE"

        log_success "Timezone configured"
    else
        log_info "Timezone already configured: $TIMEZONE"
    fi
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
    # Try to create venv and capture any errors
    # Temporarily disable exit-on-error to handle venv creation failure gracefully
    set +e
    python3.11 -m venv "$VENV_PATH" > /tmp/venv_creation.log 2>&1
    VENV_EXIT_CODE=$?
    set -e
    
    if [ $VENV_EXIT_CODE -ne 0 ]; then
        # Check if the error is about missing ensurepip/venv package
        if grep -q "ensurepip" /tmp/venv_creation.log || grep -q "No module named venv" /tmp/venv_creation.log; then
            log_warn "Python venv package not found. Installing python3.11-venv..."
            apt-get install -y python3.11-venv 2>&1 | tail -5
            
            if [ $? -ne 0 ]; then
                log_error "Failed to install python3.11-venv package"
                exit 1
            fi
            
            log_info "Retrying virtual environment creation..."
            python3.11 -m venv "$VENV_PATH" > /tmp/venv_creation_retry.log 2>&1
            
            if [ $? -ne 0 ]; then
                log_error "Failed to create virtual environment even after installing python3.11-venv"
                log_error "Error output:"
                cat /tmp/venv_creation_retry.log
                rm -f /tmp/venv_creation.log /tmp/venv_creation_retry.log
                exit 1
            fi
        else
            log_error "Failed to create virtual environment with unknown error"
            cat /tmp/venv_creation.log
            rm -f /tmp/venv_creation.log
            exit 1
        fi
    fi
    
    if [ -f "$VENV_PATH/bin/activate" ] && [ -f "$VENV_PATH/bin/python3" ]; then
        log_success "Virtual environment created successfully"
    else
        log_error "Failed to create virtual environment"
        exit 1
    fi
    
    # Set permissions for the venv now
    chown -R "$SUDO_USER:$SUDO_USER" "$VENV_PATH"
    
    # Cleanup temp log file
    rm -f /tmp/venv_creation.log /tmp/venv_creation_retry.log
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

detect_public_ip() {
    log_section "Detecting Public IP Address"
    
    log_info "Attempting to detect public IP..."
    PUBLIC_IP=$(curl -s --max-time 5 ifconfig.me 2>/dev/null || curl -s --max-time 5 icanhazip.com 2>/dev/null || curl -s --max-time 5 api.ipify.org 2>/dev/null)
    
    if [ -z "$PUBLIC_IP" ]; then
        log_error "Failed to detect public IP address"
        log_error "Please check your internet connection or use a different deployment mode"
        exit 1
    fi
    
    log_success "Detected public IP: $PUBLIC_IP"
    PUBLIC_DOMAIN="${PUBLIC_IP}.nip.io"
    log_info "nip.io domain: $PUBLIC_DOMAIN"
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
    log_section "Caddy Setup"
    
    log_info "Authentication will be handled by GitHub OAuth"
    log_info "No local auth file needed - Caddy will proxy to auth service"
    log_success "Caddy is ready for OAuth mode"
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

# Deployment Configuration
DEPLOYMENT_MODE=$DEPLOYMENT_MODE
PUBLIC_DOMAIN=$PUBLIC_DOMAIN
PUBLIC_URL=https://$PUBLIC_DOMAIN/api
ISSUER_URL=https://$PUBLIC_DOMAIN

# Timezone Configuration
TIME_ZONE=$TIMEZONE

# Ngrok Tunnel (only used if DEPLOYMENT_MODE=ngrok)
NGROK_AUTHTOKEN=$NGROK_API_KEY
TUNNEL_HOST=$NGROK_DOMAIN

# Cloudflare Tunnel (only used if custom_domain mode with Cloudflare Tunnel enabled)
EOF
    if [ "$DEPLOYMENT_MODE" = "custom_domain" ] && [ "$USE_CLOUDFLARE_TUNNEL" = "true" ]; then
        echo "CLOUDFLARE_TUNNEL=true" >> "$ENV_FILE"
    fi
    cat >> "$ENV_FILE" <<EOF

# GitHub OAuth Authentication
# Hub UI OAuth (web interface login)
GITHUB_CLIENT_ID=$GITHUB_CLIENT_ID
GITHUB_CLIENT_SECRET=$GITHUB_CLIENT_SECRET

# MCP OAuth (Claude/AI assistant connections)
MCP_GITHUB_CLIENT_ID=$MCP_GITHUB_CLIENT_ID
MCP_GITHUB_CLIENT_SECRET=$MCP_GITHUB_CLIENT_SECRET

# Username restriction (applies to both Hub UI and MCP)
ALLOWED_GITHUB_USERNAME=$ALLOWED_GITHUB_USERNAME
EOF
    
    chmod 600 "$ENV_FILE"
    log_success ".env file created at $ENV_FILE"
    log_info "Deployment mode: $DEPLOYMENT_MODE"
    log_info "Public domain: $PUBLIC_DOMAIN"
}

setup_ngrok_service() {
    log_section "Setting up ngrok Auto-Start Service"
    
    # Cleanup ngrok service if switching away from ngrok mode
    if [ "$DEPLOYMENT_MODE" != "ngrok" ]; then
        if systemctl is-enabled luna-ngrok &>/dev/null || systemctl is-active luna-ngrok &>/dev/null; then
            log_info "Detected existing ngrok service - cleaning up (switching to $DEPLOYMENT_MODE)"
            systemctl stop luna-ngrok 2>/dev/null || true
            systemctl disable luna-ngrok 2>/dev/null || true
            rm -f /etc/systemd/system/luna-ngrok.service
            systemctl daemon-reload
            log_success "ngrok service removed"
        fi
        log_info "Deployment mode is $DEPLOYMENT_MODE, skipping ngrok service setup"
        return 0
    fi
    
    if [ -z "$NGROK_DOMAIN" ] || [ "$NGROK_DOMAIN" = "null" ] || [ "$NGROK_DOMAIN" = "" ]; then
        log_error "ngrok mode selected but no ngrok domain configured"
        log_error "Please set ngrok.domain in install_config.json"
        exit 1
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
    
    # Show ngrok-specific info only if in ngrok mode
    if [ "$DEPLOYMENT_MODE" = "ngrok" ]; then
        echo "Ngrok tunnel:"
        echo "  Status:  systemctl status luna-ngrok"
        echo "  Logs:    journalctl -u luna-ngrok -f"
        echo ""
    fi
    
    echo "Installed components:"
    echo "  - System Python: $(python3 --version | awk '{print $2}')"
    echo "  - Venv Python:   $($VENV_PATH/bin/python3 --version | awk '{print $2}')"
    echo "  - Node.js:       $(node --version)"
    echo "  - pnpm:          $(pnpm --version)"
    if [ "$DEPLOYMENT_MODE" = "ngrok" ]; then
        echo "  - ngrok:         $(ngrok version | head -n1)"
    fi
    echo "  - Caddy:         $(caddy version | head -n1)"
    echo "  - Docker:        $(docker --version | awk '{print $3}' | sed 's/,//')"
    echo ""
    echo "Deployment mode: $DEPLOYMENT_MODE"
    echo ""
    echo "Authentication:"
    echo "  - Method: GitHub OAuth"
    echo "  - Allowed User: $ALLOWED_GITHUB_USERNAME"
    echo ""
    echo "Service URLs (when running):"
    echo "  - Hub UI:     http://127.0.0.1:5173"
    echo "  - Agent API:  http://127.0.0.1:8080"
    echo "  - MCP Server: http://127.0.0.1:8765"
    echo "  - Supervisor: http://127.0.0.1:9999"
    
    # Show public URL based on deployment mode
    case "$DEPLOYMENT_MODE" in
        ngrok)
            if [ -n "$NGROK_DOMAIN" ] && [ "$NGROK_DOMAIN" != "null" ] && [ "$NGROK_DOMAIN" != "" ]; then
                echo "  - Public URL: https://$NGROK_DOMAIN"
            fi
            ;;
        nip_io)
            if [ -n "$PUBLIC_DOMAIN" ]; then
                echo "  - Public URL: https://$PUBLIC_DOMAIN"
                echo ""
                echo "IMPORTANT: Ensure ports 80 and 443 are open for Let's Encrypt SSL provisioning"
            fi
            ;;
        custom_domain)
            if [ -n "$PUBLIC_DOMAIN" ]; then
                echo "  - Public URL: https://$PUBLIC_DOMAIN"
                echo ""
                if [ "$USE_CLOUDFLARE_TUNNEL" = "true" ]; then
                    echo "IMPORTANT: Ensure Cloudflare Tunnel is configured to forward to http://localhost:80"
                    echo "IMPORTANT: Caddy will automatically disable HTTPS redirects for Cloudflare Tunnel"
                else
                    echo "IMPORTANT: Ensure ports 80 and 443 are open for Let's Encrypt SSL provisioning"
                    echo "IMPORTANT: Make sure your domain's A record points to this server's public IP"
                fi
            fi
            ;;
    esac
    echo ""
}

cleanup_config() {
    log_section "Configuration Cleanup"
    
    echo "The installation is complete. Your settings have been saved to:"
    echo "  - .env (environment variables)"
    echo "  - install_config.json (installation settings)"
    echo ""
    echo "The install_config.json file is no longer needed for Luna to run,"
    echo "but it's useful if you need to re-run the installer in the future."
    echo ""
    read -p "Would you like to delete install_config.json? (y/N): " -r
    echo ""
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if [ -f "$CONFIG_FILE" ]; then
            rm -f "$CONFIG_FILE"
            log_success "install_config.json has been deleted"
        fi
    else
        log_info "Keeping install_config.json - it's safe to delete manually later if needed"
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
    
    # Handle deployment mode-specific setup
    case "$DEPLOYMENT_MODE" in
        ngrok)
            install_ngrok
            # PUBLIC_DOMAIN was already set earlier in load_config
            ;;
        nip_io)
            # PUBLIC_DOMAIN was already set earlier in load_config
            log_info "Using nip.io domain: $PUBLIC_DOMAIN"
            ;;
        custom_domain)
            # PUBLIC_DOMAIN was already set earlier in load_config
            if [ "$USE_CLOUDFLARE_TUNNEL" = "true" ]; then
                log_info "Using custom domain with Cloudflare Tunnel: $PUBLIC_DOMAIN"
            else
                log_info "Using custom domain: $PUBLIC_DOMAIN"
            fi
            ;;
    esac
    
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
    
    # Cleanup config file
    cleanup_config
}

# Run main installation
main