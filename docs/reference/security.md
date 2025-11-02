# Security Model

Understanding Luna's authentication, authorization, and security practices.

---

## Overview

Luna uses a layered security model:

1. **GitHub OAuth** - User authentication for Hub UI and main MCP server
2. **API Keys** - Service-to-service authentication (Agent API, named MCP hubs)
3. **Caddy Proxy** - TLS termination, header injection, unified entry point
4. **Environment Secrets** - Secure storage of credentials
5. **Username Restrictions** - Optional access control

---

## Authentication Flow

### Hub UI Authentication

```mermaid
User → Caddy → Hub UI → Auth Service → GitHub OAuth → Session Cookie → Access Granted
```

**Steps:**
1. User visits `https://your-domain.com`
2. Hub UI checks `/auth/me` for valid session
3. If not authenticated, redirects to `/auth/login`
4. Auth service redirects to GitHub OAuth
5. User authorizes on GitHub
6. GitHub redirects to `/auth/callback` with code
7. Auth service exchanges code for user info
8. Signed session cookie issued
9. User redirected to Hub UI

**Session Storage:**
- Cookies: Signed with secret key, httpOnly, secure
- Optional Postgres persistence: `sessions` table stores username, token, expiry

### MCP Server Authentication

**Main Hub (`/api/mcp`):**
- Uses GitHub OAuth via FastMCP
- Clients must complete OAuth flow
- No API key required

**Named Hubs (`/api/mcp-{name}`):**
- API key authentication
- Header: `Authorization: Bearer <MCP_SERVER_{NAME}_API_KEY>`
- Keys generated during hub creation
- Stored in `.env` and `master_config.json`

### Agent API Authentication

**OpenAI-Compatible Endpoints:**
- Requires `AGENT_API_KEY` in `Authorization: Bearer` header
- Key auto-generated on first start
- Stored in `.env`
- Can be regenerated via Hub UI or API

---

## API Key Management

### Agent API Key

**Generation:**
```python
# Format: sk-luna-<base64url(32 random bytes)>
AGENT_API_KEY = f"sk-luna-{secrets.token_urlsafe(32)}"
```

**Storage:**
- `.env` file (git-ignored)
- Retrieved via `/api/supervisor/agents/api-key`

**Rotation:**
```bash
# Via API
curl -X POST https://your-domain.com/api/supervisor/agents/api-key/regenerate

# Or via Hub UI Tools page (Agent Presets mode)
```

**Usage:**
```bash
curl -H "Authorization: Bearer $AGENT_API_KEY" \
  https://your-domain.com/api/agent/v1/models
```

### MCP Server API Keys

**Generation:**
- Automatically created when adding named MCP hub
- Same format as Agent API key
- One key per hub

**Storage:**
- `.env` as `MCP_SERVER_{NAME}_API_KEY` (uppercase)
- `master_config.json` under `mcp_servers.{name}.api_key`

**Viewing:**
- Hub UI Tools page → Select MCP hub → View/copy key (eye icon)

**Regeneration:**
- Hub UI Tools page → Regenerate button
- Invalidates old key immediately

---

## Authorization

### Username Restrictions

**Optional enforcement:**
```bash
# In .env
ALLOWED_GITHUB_USERNAME=your-github-username
```

- When set, only this GitHub user can authenticate
- Checked during OAuth callback
- Useful for single-user deployments
- Leave unset for multi-user access

### Service-Level Authorization

**Current model:**
- Hub UI: GitHub OAuth required
- Agent API: Valid API key = full access
- MCP Servers: Auth token/key = full tool access
- Supervisor API: Optional `SUPERVISOR_API_TOKEN`

**No per-tool or per-endpoint authorization** (all-or-nothing)

---

## TLS & Transport Security

### Caddy Automatic HTTPS

**Deployment Modes:**

**ngrok:**
- Caddy listens on port 80
- ngrok tunnel provides TLS
- Caddy config: `http://`

**nip.io / custom_domain:**
- Caddy listens on ports 80/443
- Caddy obtains Let's Encrypt certificates automatically
- Automatic HTTP→HTTPS redirect
- Caddy config: `https://`

### Certificate Management

**Let's Encrypt:**
- Caddy handles ACME challenges
- Certificates stored in Caddy data directory
- Auto-renewal before expiry

**Manual certificates:**
- Not currently supported
- Could be added to Caddy config generator

### Internal Communication

**Between services:**
- Plain HTTP on localhost
- No TLS (services trust local connections)
- Caddy is the only public entry point

---

## Secret Management

### Environment Variables

**Storage:**
- `.env` file (must be in `.gitignore`)
- File permissions should be `600` (owner read/write only)

**Access Control:**
- Managed via Hub UI or Supervisor API
- Never returned in full via API (masked)
- Updates write directly to `.env` and reload

**Best Practices:**
```bash
# Set restrictive permissions
chmod 600 .env

# Never commit to git
git ls-files | grep .env  # Should be empty
```

### Extension Secrets

**Declaration:**
```json
// extensions/my_ext/config.json
{
  "required_secrets": ["MY_API_KEY", "MY_SECRET"]
}
```

**Discovery:**
```bash
# Supervisor API shows missing secrets
GET /api/supervisor/keys/required
```

**Hub UI:**
- Shows which extensions need which secrets
- Prompts user to add missing keys

---

## Session Security

### Cookie Attributes

```python
# Session cookie configuration
cookie = {
    "httpOnly": True,      # No JavaScript access
    "secure": True,        # HTTPS only (production)
    "sameSite": "Lax",     # CSRF protection
    "maxAge": 86400,       # 24 hours
    "signed": True         # HMAC signature
}
```

### Session Expiry

**Default:** 24 hours

**Extension:** Sessions renewed on each request

**Logout:** Clears cookie and (if Postgres) deletes session record

---

## Security Headers

Caddy configuration includes:

```caddyfile
header {
    X-Frame-Options "SAMEORIGIN"
    X-Content-Type-Options "nosniff"
    X-XSS-Protection "1; mode=block"
    Referrer-Policy "strict-origin-when-cross-origin"
}
```

**Note:** CSP not currently configured (would break dynamic content loading)

---

## Attack Surface Analysis

### Public Endpoints

**GitHub OAuth callbacks:**
- Risk: OAuth misconfiguration, open redirect
- Mitigation: State parameter validation, redirect URI whitelist

**Hub UI:**
- Risk: XSS, CSRF
- Mitigation: React escaping, SameSite cookies, httpOnly

**Agent API:**
- Risk: API key compromise, injection attacks
- Mitigation: Input validation, parameterized queries, tool sandboxing

**MCP Servers:**
- Risk: Tool abuse, data exfiltration
- Mitigation: Authentication required, tool-level permissions (future)

### Internal Endpoints

**Supervisor API:**
- Listens on `0.0.0.0:9999` (accessible on local network)
- Optional `SUPERVISOR_API_TOKEN` for mutations
- Risk: Local network attacks
- Mitigation: Firewall rules, use token in multi-user environments

**Service ports:**
- Extension UIs/services on `5200-5399`
- Not directly exposed (proxied via Caddy)
- Risk: Bypass Caddy, access without auth
- Mitigation: Firewall rules, bind to localhost only

---

## Vulnerability Handling

### Reporting Security Issues

**DO NOT** file public GitHub issues for security vulnerabilities.

**Contact:** (Specify security contact email or private reporting method)

### Update Policy

- Security fixes released as soon as possible
- Announced in release notes
- Users notified via GitHub (watch releases)

---

## Hardening Recommendations

### Production Deployment

**Firewall:**
```bash
# Allow only Caddy ports
ufw allow 80/tcp
ufw allow 443/tcp
ufw deny 9999/tcp  # Supervisor
ufw deny 8080/tcp  # Agent API
ufw deny 5000:5999/tcp  # Extension/service ports
ufw enable
```

**Environment:**
```bash
# Set supervisor token
SUPERVISOR_API_TOKEN=$(openssl rand -base64 32)

# Restrict to single user
ALLOWED_GITHUB_USERNAME=your-username

# Use secure database password
DB_PASSWORD=$(openssl rand -base64 32)
```

**File Permissions:**
```bash
chmod 600 .env
chmod 700 .luna
chmod 600 core/master_config.json
```

### Multi-User Considerations

**Current limitations:**
- No per-user tool access control
- All authenticated users have full Hub UI access
- Agent API key is shared (no per-user keys)

**Recommendations:**
- Use `ALLOWED_GITHUB_USERNAME` for single-user
- For multi-user, all users are equally privileged
- Plan for per-user authorization in future releases

### Extension Security

**Risks:**
- Malicious extensions can access `.env` secrets
- Tools run with Luna's permissions
- No sandboxing of extension code

**Mitigations:**
- Only install trusted extensions
- Review extension code before installation
- Use separate service accounts for sensitive integrations
- Monitor extension behavior in logs

---

## Threat Model

### Trusted

- GitHub (OAuth provider)
- LLM providers (OpenAI, Anthropic, etc.)
- Luna repository maintainers
- Local network (internal service communication)

### Untrusted

- Public internet
- Extension authors (until vetted)
- Remote MCP servers (Smithery integrations)
- User input to agents/tools

### Out of Scope

- Physical access to server
- Compromise of underlying OS
- Social engineering of GitHub account
- Supply chain attacks on dependencies (Python packages, npm modules)

---

## Security Checklist

**Before Going Live:**

- [ ] Set `ALLOWED_GITHUB_USERNAME` or implement user allowlist
- [ ] Configure firewall to block internal ports
- [ ] Set `SUPERVISOR_API_TOKEN`
- [ ] Use strong database password
- [ ] Verify `.env` is in `.gitignore`
- [ ] Check file permissions (`chmod 600 .env`)
- [ ] Enable automatic security updates on host OS
- [ ] Review installed extensions
- [ ] Test OAuth flow end-to-end
- [ ] Verify TLS certificate auto-renewal
- [ ] Set up log monitoring/alerting
- [ ] Document incident response plan

---

## Future Improvements

**Planned:**
- Per-user API keys
- Role-based access control (RBAC)
- Tool-level permissions
- Extension sandboxing
- Audit logging
- Rate limiting
- TOTP/2FA option
- Service account tokens (non-expiring)

**Under Consideration:**
- OAuth providers beyond GitHub
- SAML/SSO integration
- Secrets management integration (Vault, AWS Secrets Manager)
- Container isolation for extensions
- Principle of least privilege for tool execution
