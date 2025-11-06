# Installation Guide

Luna Hub is designed to run continuously on a dedicated machine—whether that's a home server, cloud VM, or always-on computer. This guide will walk you through the complete installation process.

## Prerequisites

### System Requirements

**Minimum:**
- Linux operating system (Debian, Ubuntu, or compatible)
- 2 GB RAM
- 10 GB free disk space
- Python 3.10 or newer
- Root/sudo access

**Recommended:**
- 4+ GB RAM
- 20+ GB free disk space (for apps/services and logs)
- Ubuntu 22.04 LTS
- Dedicated machine that runs 24/7

**Supported platforms:**
- Physical servers (home lab, NUC, Raspberry Pi 4+)
- Cloud VMs (AWS EC2, DigitalOcean Droplet, Linode, etc.)
- Proxmox VE containers (LXC)
- Docker host machines

### Required Accounts

You'll need accounts for:

1. **GitHub** (required for OAuth authentication)
   - Create at: [https://github.com/signup](https://github.com/signup)
   - You'll create OAuth apps during installation

2. **LLM Provider** (required for AI agents)
   - OpenAI API key ([https://platform.openai.com/api-keys](https://platform.openai.com/api-keys)), OR
   - Anthropic API key ([https://console.anthropic.com/](https://console.anthropic.com/))

3. **Domain/Tunnel Service** (depends on deployment mode—see below)

## Understanding Deployment Modes

Luna Hub supports three deployment modes based on how you'll access the system. Choose the one that fits your infrastructure:

### 1. Ngrok Tunnel (Easiest for Home Networks)

**Best for:** Home networks without port forwarding or dynamic IP addresses

**How it works:**
- Ngrok creates a secure tunnel from your local machine to a public URL
- Luna automatically configures the tunnel on startup
- No router configuration needed
- SSL/TLS provided by ngrok

**Requirements:**
- Ngrok account (free tier works): [https://ngrok.com/signup](https://ngrok.com/signup)
- Ngrok auth token (from dashboard)
- Ngrok static domain (free tier includes one)

**Pros:**
- Zero network configuration
- Works behind strict firewalls/CGNAT
- Built-in SSL certificates
- Perfect for testing and home use

**Cons:**
- Requires ngrok account
- Free tier has connection limits
- Tunnel must restart with Luna

**Example URL:** `https://your-subdomain.ngrok-free.app`

### 2. Nip.io Dynamic DNS (Cloud VMs)

**Best for:** Cloud virtual machines with public IP addresses

**How it works:**
- Uses nip.io's wildcard DNS service
- Automatically detects your public IP
- Generates SSL certificates via Let's Encrypt
- No DNS configuration needed

**Requirements:**
- Public IP address (static or dynamic)
- Ports 80 and 443 open to the internet
- Outbound HTTPS access (for Let's Encrypt)

**Pros:**
- Free and automatic
- Real SSL certificates
- No third-party account needed
- Works immediately on cloud providers

**Cons:**
- Requires public IP and open ports
- Relies on nip.io service availability
- Domain name is tied to IP (e.g., `192-168-1-100.nip.io`)

**Example URL:** `https://192-168-1-100.nip.io` (auto-generated from your IP)

### 3. Custom Domain (Production) 
You can get your own domain for only a few dollars! Personally I use namescheap.com and if you want to be fancy you can use cloudflare for your nameservers if you get bored waiting for the dns to propagate and want more security.
The lunahub.dev domain cost me less than $10 for the first year.
**Best for:** Production deployments, custom branding, or existing domains

**How it works:**
- You provide your own domain name
- Luna configures Caddy with automatic SSL
- You manually configure DNS A record
- Full control over domain and certificates
- **Optional:** Use Cloudflare Tunnel instead of direct access (Cloudflare handles TLS, no ports needed)

**Requirements (Direct Access):**
- Registered domain name (from Namecheap, Cloudflare, etc.)
- Ability to set DNS A records
- Ports 80 and 443 open to the internet
- Public IP address

**Requirements (Cloudflare Tunnel):**
- Registered domain name
- Cloudflare account (free tier works)
- Cloudflare Tunnel configured in Zero Trust dashboard
- Cloudflare Tunnel service running on your server

**Pros:**
- Professional custom domain
- Full control over DNS and certificates
- Best for production use
- Can use subdomains (e.g., `luna.yourdomain.com`)
- **With Cloudflare Tunnel:** No need to open firewall ports, Cloudflare handles TLS termination

**Cons:**
- Requires domain purchase (~$10-15/year)
- Manual DNS configuration
- Must wait for DNS propagation (up to 48 hours)
- **With Cloudflare Tunnel:** Requires Cloudflare account and separate tunnel setup

**Example URL:** `https://luna.yourdomain.com`

**Cloudflare Tunnel Option:**
When selecting custom_domain mode, you can choose to use Cloudflare Tunnel instead of direct access. This option:
- Uses Cloudflare Tunnel to expose your domain (no need to open ports 80/443)
- Cloudflare terminates TLS and forwards HTTP to your server
- Luna automatically configures Caddy to work with Cloudflare Tunnel
- Perfect for servers behind firewalls or NAT

---

## Installation Steps

### Step 1: Clone the Repository

```bash
# Navigate to your preferred installation directory
cd /root  # Or wherever you want Luna installed

# Clone the repository
git clone https://github.com/jbrinkw/luna-hub.git
cd luna-hub
```

### Step 2: Run the Installer

Luna includes an interactive installer that handles all dependencies and configuration:

```bash
sudo ./install.sh
```

!!! warning "Sudo Required"
    The installer must run as root to install system packages (Docker, Caddy, Node.js, etc.). It will drop privileges where appropriate.

### Step 3: Choose Deployment Mode

The installer will prompt you to select a deployment mode:

```
=== Luna Hub Installation ===

Choose your deployment mode:
1) ngrok - Tunnel mode (easiest for home networks)
2) nip.io - Auto-detected IP with SSL (cloud VMs)
3) custom_domain - Your own domain (production)

Enter choice [1-3]:
```

Choose the option that matches your infrastructure (see [Understanding Deployment Modes](#understanding-deployment-modes) above).

### Step 4: Mode-Specific Configuration

#### For Ngrok Mode:

```
Enter your ngrok auth token:
> ngt_your_token_here

Enter your ngrok domain (e.g., my-luna.ngrok-free.app):
> my-luna.ngrok-free.app
```

- Find your auth token at [https://dashboard.ngrok.com/get-started/your-authtoken](https://dashboard.ngrok.com/get-started/your-authtoken)
- Create a domain at [https://dashboard.ngrok.com/domains](https://dashboard.ngrok.com/domains)

#### For Nip.io Mode:

```
Detected public IP: 203.0.113.42
Your Luna Hub will be accessible at: https://203-0-113-42.nip.io

Ensure ports 80 and 443 are open to the internet.
Continue? [y/N]:
```

The installer will automatically detect your public IP and generate the URL.

#### For Custom Domain Mode:

```
Enter your custom domain (e.g., luna.yourdomain.com):
> luna.yourdomain.com
```

- Configure an A record in your DNS provider pointing to your server's IP
- Wait for DNS propagation (usually 5-10 minutes, up to 48 hours)

#### For Cloudflare Tunnel Mode:

```
Enter your Cloudflare Tunnel domain (e.g., meow.sex):
> meow.sex
```

- Set up Cloudflare Tunnel in Cloudflare Zero Trust dashboard
- Configure tunnel to forward to `http://localhost:80`
- Set the hostname to match the domain you entered
- Luna will automatically configure Caddy to work with Cloudflare Tunnel

---

### Step 5: Configure GitHub OAuth

Luna requires **two** GitHub OAuth applications:

1. **Hub UI OAuth App** - For web interface login
2. **MCP OAuth App** - For Claude/AI assistant connections

#### Creating GitHub OAuth Apps

For each app, go to [GitHub Settings > Developer settings > OAuth Apps](https://github.com/settings/developers) and click "New OAuth App":

**Hub UI OAuth App:**
- Application name: `Luna Hub UI`
- Homepage URL: `https://your-domain.com` (use your deployment mode URL)
- Authorization callback URL: `https://your-domain.com/auth/callback`

**MCP OAuth App:**
- Application name: `Luna MCP Server`
- Homepage URL: `https://your-domain.com` (use your deployment mode URL)
- Authorization callback URL: `https://your-domain.com/api/authorize`

After creating each app, copy the **Client ID** and **Client Secret** - you'll need them during installation.

---

### Step 6: Complete Installation

The installer will prompt you for:

1. **GitHub OAuth credentials** (both apps)
2. **Allowed GitHub username** (optional - restricts access to specific user)
3. **LLM API key** (OpenAI or Anthropic)
4. **Timezone** (defaults to UTC)

Once complete, the installer will:

- Create `.env` file with all configuration
- Install Python dependencies
- Set up systemd service for auto-start
- Generate initial configuration files

---

### Step 7: Start Luna

```bash
sudo systemctl start luna
sudo systemctl enable luna  # Enable auto-start on boot
```

Check status:

```bash
sudo systemctl status luna
```

View logs:

```bash
journalctl -u luna -f
```

---

## Post-Installation

### Accessing Luna Hub

Once running, access Luna Hub at:

- **Ngrok mode:** `https://your-subdomain.ngrok-free.app`
- **Nip.io mode:** `https://your-ip.nip.io`
- **Custom domain:** `https://your-domain.com` (direct access or via Cloudflare Tunnel)

### First Login

1. Navigate to your Luna Hub URL
2. Click "Login with GitHub"
3. Authorize the GitHub OAuth app
4. If you set an allowed username, only that user can log in

### Service Management

**Start/Stop/Restart:**
```bash
sudo systemctl start luna
sudo systemctl stop luna
sudo systemctl restart luna
```

**View logs:**
```bash
# All logs
journalctl -u luna -f

# Recent logs only
journalctl -u luna --since "1 hour ago"
```

**Check service status:**
```bash
sudo systemctl status luna
```

---

## Troubleshooting

### Port Already in Use

If you see errors about ports being in use:

```bash
# Check what's using the port
sudo lsof -i :5173  # Hub UI
sudo lsof -i :8080  # Agent API
sudo lsof -i :8765  # Auth service

# Kill the process if needed
sudo kill -9 <PID>
```

### Caddy SSL Certificate Issues

For `nip_io` or `custom_domain` modes, if SSL certificates fail:

1. Ensure ports 80 and 443 are open
2. Check firewall rules: `sudo ufw status`
3. Verify DNS A record points to correct IP
4. Wait for DNS propagation (can take up to 48 hours)
5. Check Caddy logs: `tail -f logs/caddy.log`

### GitHub OAuth Not Working

1. Verify callback URLs match exactly in GitHub OAuth app settings
2. Check that your domain is accessible from the internet
3. Ensure HTTPS is working (required for OAuth)
4. Check auth service logs: `tail -f logs/auth_service.log`

### Cloudflare Tunnel Issues

If using Cloudflare Tunnel mode:

1. Verify Cloudflare Tunnel is running: `systemctl status cloudflared`
2. Check tunnel configuration points to `http://localhost:80`
3. Verify domain hostname matches in Cloudflare dashboard
4. Check Caddy is listening on port 80: `ss -tlnp | grep :80`
5. Review Cloudflare Tunnel logs: `journalctl -u cloudflared -f`

---

## Configuration Files

!!! important "DNS Configuration Required"
    For custom domains, you **must** configure your DNS A record before continuing. Use your domain registrar's control panel or Cloudflare to add the record.

### Step 5: GitHub OAuth Setup

Luna requires two GitHub OAuth apps (one for Hub UI, one for MCP):

```
=== GitHub OAuth Configuration ===

Create TWO GitHub OAuth Apps at:
https://github.com/settings/developers

App 1 - Luna Hub UI:
  Application name: Luna Hub UI
  Homepage URL: https://your-domain
  Authorization callback URL: https://your-domain/auth/callback

App 2 - Luna MCP Server:
  Application name: Luna MCP
  Homepage URL: https://your-domain
  Authorization callback URL: https://your-domain/api/authorize

Enter Hub UI Client ID:
> Ov23liXXXXXXXXXXXXXX

Enter Hub UI Client Secret:
> 9f43730544c633480ce5XXXXXXXXXXXXXXXXXX

Enter MCP Client ID:
> Ov23liiXXXXXXXXXXXXXX

Enter MCP Client Secret:
> 491b4889d0fa9d40be9XXXXXXXXXXXXXXXXXXX
```

**Creating OAuth Apps:**

1. Go to [https://github.com/settings/developers](https://github.com/settings/developers)
2. Click "New OAuth App"
3. Fill in the details using the URLs provided by the installer
4. Click "Register application"
5. Copy the Client ID
6. Click "Generate a new client secret" and copy it
7. Repeat for the second app

### Step 6: Username Restriction (Optional)

```
Restrict access to a specific GitHub username? [y/N]:
> y

Enter allowed GitHub username:
> yourusername
```

This ensures only your GitHub account can log into Luna Hub. Leave empty to allow any GitHub user.

### Step 7: Additional API Keys

```
=== API Configuration ===

Enter your OpenAI API key (or leave empty to configure later):
> sk-proj-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

You can add additional API keys later through the Hub UI's environment manager.

### Step 8: Database Setup

```
=== Database Configuration ===

Luna requires PostgreSQL for memory and automation features.
Install and configure PostgreSQL now? [Y/n]:
> y
```

The installer will:
- Install PostgreSQL via Docker
- Create the `luna` database
- Run schema migrations
- Configure connection details in `.env`

### Step 9: Installation Complete

```
=== Installation Complete ===

Luna Hub is installed and ready to start!

Starting Luna Hub...
✓ Virtual environment created
✓ Dependencies installed
✓ Database initialized
✓ Services starting...

Luna Hub is accessible at:
https://your-domain

Default login: GitHub OAuth (username: yourusername)

Logs are available in:
  - Supervisor: logs/supervisor.log
  - Agent API: logs/agent_api.log
  - Hub UI: logs/hub_ui.log

To manage Luna Hub:
  Start:   sudo systemctl start luna
  Stop:    sudo systemctl stop luna
  Restart: sudo systemctl restart luna
  Status:  sudo systemctl status luna
  Logs:    journalctl -u luna -f
```

---

## Post-Installation

### Verify Installation

1. **Check service status:**
   ```bash
   sudo systemctl status luna
   ```

2. **Access the Hub UI:**
   - Navigate to your Luna Hub URL (from installer output)
   - Click "Login with GitHub"
   - Authorize the OAuth application

3. **Check the dashboard:**
   - You should see system status, discovered agents, and installed extensions
   - Visit `/tools` to see available tools

### First Steps

1. **Configure API Keys:**
   - Go to Settings → Environment Keys
   - Add any missing API keys (OpenAI, Anthropic, service-specific keys)

2. **Install Extensions:**
   - Visit Extensions → Extension Manager
   - **Browse the built-in store** for one-click installation of popular extensions
   - Install ChefByte for kitchen management
   - Install Home Assistant extension if you have HA running
   - Or install from GitHub URL or upload custom ZIP packages

3. **Set Up Apps/Services:**
   - Visit Apps/Services
   - **Use the built-in marketplace** to install pre-configured Docker applications
   - Install Grocy (if using ChefByte) with one click
   - Configure service settings through the web interface
   - Or upload custom service definitions

4. **Test the Agent API:**
   ```bash
   curl -X POST https://your-domain/api/agent/v1/chat/completions \
     -H "Authorization: Bearer YOUR_AGENT_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{
       "model": "passthrough_agent",
       "messages": [{"role": "user", "content": "Hello!"}]
     }'
   ```

5. **Connect Claude Desktop (Optional):**
   - Visit `/tools` to copy MCP connection details
   - Add to Claude Desktop's MCP servers config
   - Restart Claude Desktop

---

## Systemd Service Management

Luna Hub installs as a systemd service for automatic startup and management:

### Basic Commands

```bash
# Start Luna Hub
sudo systemctl start luna

# Stop Luna Hub
sudo systemctl stop luna

# Restart Luna Hub
sudo systemctl restart luna

# Check status
sudo systemctl status luna

# View logs (real-time)
journalctl -u luna -f

# View logs (last 100 lines)
journalctl -u luna -n 100
```

### Enable/Disable Auto-Start

```bash
# Enable auto-start on boot
sudo systemctl enable luna

# Disable auto-start
sudo systemctl disable luna

# Check if enabled
systemctl is-enabled luna
```

### Troubleshooting Service Issues

```bash
# View full service definition
systemctl cat luna

# View service dependencies
systemctl list-dependencies luna

# Reload systemd configuration (after manual edits)
sudo systemctl daemon-reload
```

---

## Configuration Files

Luna Hub stores configuration in several locations:

| File | Purpose | Gitignored |
|------|---------|------------|
| `.env` | Environment variables and secrets | ✅ Yes |
| `core/master_config.json` | Extension and service configuration | ❌ No |
| `install_config.json` | Installer selections | ✅ Yes |
| `.luna/Caddyfile` | Generated reverse proxy config | ✅ Yes |
| `supervisor/state.json` | Runtime process state | ✅ Yes |
| `.venv/` | Python virtual environment | ✅ Yes |

**Important:** Never commit `.env` or `install_config.json` to version control—they contain secrets.

---

## Deployment Mode Comparison

| Feature | Ngrok | Nip.io | Custom Domain | Custom Domain + Cloudflare Tunnel |
|---------|-------|--------|---------------|-----------------------------------|
| **Setup Difficulty** | Easy | Easy | Moderate | Moderate |
| **Network Config** | None | Open ports | Open ports + DNS | None (tunnel) |
| **SSL Certificates** | Automatic | Automatic | Automatic | Cloudflare |
| **Custom Domain** | ❌ No | ❌ No | ✅ Yes | ✅ Yes |
| **Third-Party Account** | ✅ Required | ❌ Not needed | ❌ Not needed | ✅ Required (Cloudflare) |
| **Best For** | Home networks | Cloud VMs | Production | Production (behind firewall) |
| **Connection Limits** | Free tier limits | ✅ None | ✅ None | ✅ None |
| **DNS Dependency** | ❌ No | ✅ nip.io service | ✅ Your registrar | ✅ Cloudflare |
| **Cost** | Free tier OK | ✅ Free | Domain fee (~$10/yr) | Domain fee (~$10/yr) |
| **Firewall Ports** | ❌ None | ✅ 80, 443 | ✅ 80, 443 | ❌ None |

---

## Network Requirements

### Port Requirements

Luna Hub requires these ports **internally** (localhost):

- `5173` - Hub UI dev server (Vite)
- `8080` - Agent API (OpenAI-compatible)
- `8765` - Auth service (GitHub OAuth)
- `8766` - MCP server (main)
- `8767+` - Additional MCP servers (if configured)
- `9999` - Supervisor API (control plane)
- `5200-5299` - Extension UIs (dynamically assigned)
- `5300-5399` - Extension services (dynamically assigned)

**External access** depends on deployment mode:

| Deployment Mode | External Ports | Direction |
|----------------|----------------|-----------|
| **Ngrok** | None | Outbound only to ngrok |
| **Nip.io** | 80, 443 | Inbound TCP |
| **Custom Domain** | 80, 443 | Inbound TCP |

### Firewall Configuration

#### For Nip.io or Custom Domain:

**UFW (Ubuntu/Debian):**
```bash
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

**iptables:**
```bash
sudo iptables -A INPUT -p tcp --dport 80 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 443 -j ACCEPT
sudo iptables-save
```

**Cloud Provider Firewalls:**
- AWS: Configure Security Groups to allow TCP 80, 443
- DigitalOcean: Configure Cloud Firewall to allow HTTP, HTTPS
- Linode: Configure Cloud Firewall to allow TCP 80, 443

#### For Ngrok:

No inbound firewall rules needed. Ensure outbound HTTPS (port 443) is allowed to reach `*.ngrok.io`.

---

## Updating Luna Hub

Luna Hub includes a built-in update system accessible through the Hub UI:

1. **Check for updates:**
   - Visit Dashboard → System Status
   - Or check GitHub releases manually

2. **Stage updates:**
   - Visit Extensions → Update Manager
   - Select "Update Core"
   - Queue the update

3. **Apply updates:**
   - Click "Restart Luna" in the header
   - Updates apply on next startup
   - Check logs for update status

**Manual update (Git):**
```bash
cd /root/luna-hub
git pull origin main
sudo systemctl restart luna
```

---

## Troubleshooting

### Installation Issues

**Installer fails with "Permission denied":**
```bash
# Ensure you're running with sudo
sudo ./install.sh
```

**Ports already in use:**
```bash
# Check what's using the ports
sudo lsof -i :8080
sudo lsof -i :8443

# Kill conflicting processes or change Luna's ports
```

**Ngrok tunnel won't start:**
- Verify auth token is correct
- Ensure ngrok domain is configured in dashboard
- Check ngrok service logs: `journalctl -u ngrok -f`

**Let's Encrypt SSL fails (nip.io/custom domain):**
- Verify ports 80 and 443 are reachable from internet
- Check DNS resolution: `dig your-domain.com`
- Review Caddy logs: `cat logs/caddy.log`

### Runtime Issues

**Luna won't start:**
```bash
# Check systemd status
sudo systemctl status luna

# View detailed logs
journalctl -u luna -n 200

# Check supervisor logs
tail -f logs/supervisor.log
```

**Can't log in via GitHub OAuth:**
- Verify OAuth app callback URLs match your domain exactly
- Check browser console for CORS errors
- Ensure `ISSUER_URL` in `.env` matches your domain

**Extensions won't load:**
```bash
# Check extension discovery
cat supervisor/state.json

# View extension-specific logs
tail -f logs/chefbyte_ui.log
```

**Agent API returns errors:**
```bash
# Check agent API logs
tail -f logs/agent_api.log

# Verify API key is set
grep AGENT_API_KEY .env

# Test API endpoint
curl http://localhost:8080/v1/models
```

### Database Issues

**PostgreSQL connection fails:**
```bash
# Check if PostgreSQL is running
docker ps | grep postgres

# Verify connection details
grep DB_ .env

# Test connection manually
psql postgresql://luna_user:postygresy@127.0.0.1:5432/luna
```

**Database schema out of date:**
```bash
# Re-run migrations
.venv/bin/python3 core/scripts/init_db.py
```

---

## Advanced Configuration

### Custom Port Assignments

Edit `core/master_config.json` to customize port assignments:

```json
{
  "port_assignments": {
    "extensions": {
      "chefbyte": 5200
    },
    "services": {
      "chefbyte.backend": 5300
    }
  }
}
```

Restart Luna to apply changes.

### Multiple MCP Servers

Create additional MCP server instances for specialized tool access:

1. Edit `core/master_config.json`:
   ```json
   {
     "mcp_servers": {
       "main": {
         "name": "main",
         "port": 8766,
         "enabled": true
       },
       "smarthome": {
         "name": "smarthome",
         "port": 8767,
         "enabled": true,
         "tool_config": {
           "home_assistant_turn_on": {"enabled_in_mcp": true},
           "grocy_tools": {"enabled_in_mcp": false}
         }
       }
     }
   }
   ```

2. Restart Luna Hub
3. Access specialized servers at `/api/mcp-smarthome`

### Systemd Service Customization

Edit the systemd service file:

```bash
sudo systemctl edit luna
```

Add custom environment variables or resource limits:

```ini
[Service]
Environment="CUSTOM_VAR=value"
MemoryLimit=2G
CPUQuota=50%
```

Reload and restart:

```bash
sudo systemctl daemon-reload
sudo systemctl restart luna
```

---

## Security Best Practices

1. **Restrict GitHub OAuth:** Always set `ALLOWED_GITHUB_USERNAME` to limit access
2. **Use strong secrets:** Generate secure passwords for database, API keys
3. **Keep updated:** Regularly update Luna Hub and system packages
4. **Monitor logs:** Check logs periodically for unusual activity
5. **Firewall rules:** Only open ports 80/443 externally, block direct access to internal ports
6. **Backup data:** Regularly backup `external_services/*/data/`, `core/master_config.json`, and `.env`

---

## Next Steps

Now that Luna Hub is installed and running:

1. **Explore the Hub UI:** Navigate your Luna Hub URL and familiarize yourself with the dashboard
2. **Install extensions:** Start with ChefByte and Home Assistant to see Luna's capabilities
3. **Configure tools:** Visit `/tools` to enable/disable specific tools per MCP server
4. **Create agent presets:** Build specialized agents for different use cases
5. **Connect Claude Desktop:** Use Luna's tools directly in Claude Desktop via MCP
6. **Build custom tools:** Follow the [Developer Guide](developer-guide/creating-extensions.md) to create your own extensions

For detailed examples of what you can build with Luna Hub, see [Featured Extensions](getting-started/featured-extensions.md).
