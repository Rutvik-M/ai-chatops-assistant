# Network Access and Security Guidelines

## Network Credentials

### Active Directory Login
- Username format: `firstname.lastname`
- Domain: `COMPANY`
- Full login: `COMPANY\firstname.lastname`

### WiFi Networks

#### Primary Office Network: **CompanyNet**
- SSID: `CompanyNet`
- Security: WPA2-Enterprise
- Authentication: Use AD credentials
- Certificate: Auto-installed on company devices

#### Guest Network: **CompanyGuest**
- SSID: `CompanyGuest`
- Password: `Welcome2025` (changes quarterly)
- No access to internal resources
- Internet only, speed limited to 10 Mbps

#### Executive Network: **CompanyExec**
- SSID: `CompanyExec-5G`
- Password: Contact IT for access
- Reserved for C-level and VPs
- Priority QoS, no bandwidth limits

## VPN Access

### Cisco AnyConnect VPN
- Download: `vpn.company.com/download`
- Server: `vpn.company.com`
- Group: `RemoteAccess`

### Connection Steps:
1. Launch Cisco AnyConnect
2. Enter server: `vpn.company.com`
3. Select group: RemoteAccess
4. Enter AD username and password
5. Enter MFA code from authenticator app

### Troubleshooting VPN:
- Clear saved credentials if login fails
- Reinstall client if connection drops repeatedly
- Use backup server: `vpn2.company.com`

## File Server Access

### Shared Drives
- Department drives: \\fileserver\departments\[dept_name]
- Personal drives: \\fileserver\users\[username]
- Project drives: \\fileserver\projects\[project_code]

### Mapped Drive Letters:
- H: Drive - Personal home folder
- S: Drive - Shared departmental folder
- P: Drive - Current project folder

## Remote Desktop

### Accessing Work Computer Remotely
1. Connect to VPN first
2. Open Remote Desktop Connection
3. Enter computer name: `[username]-PC.company.com`
4. Login with AD credentials

### Requirements:
- Computer must be powered on
- Connected to network
- RDP enabled by IT

## Security Policies

### Multi-Factor Authentication (MFA)
- Required for: VPN, email, file servers
- Recommended app: Microsoft Authenticator
- Backup codes: Save in secure location

### Password Policy
- Change every 90 days
- 12 characters minimum
- Complexity required
- No password reuse (last 5)

### Device Management
- All devices must be encrypted (BitLocker)
- Antivirus required (Symantec Endpoint Protection)
- Automatic updates enabled
- Screen lock after 10 minutes idle

## Firewall Rules

### Allowed Ports:
- 80, 443 (HTTP/HTTPS)
- 22 (SSH)
- 3389 (RDP)
- 445 (SMB file sharing)

### Blocked by Default:
- Peer-to-peer file sharing
- Torrent protocols
- Cryptocurrency mining
- Gaming servers

## Cloud Services

### Approved Services:
- Microsoft 365 (email, OneDrive, Teams)
- Google Workspace (limited to contractors)
- Zoom (video conferencing)
- Slack (team communication)
- GitHub (code repositories)

### Unapproved Services:
- Personal Dropbox, Google Drive
- WeTransfer
- WhatsApp for business communication
- Personal email for work files

## Contact IT Support
- Email: it@company.com
- Phone: Ext. 5000
- Portal: support.company.com
- Emergency: +1-555-IT-URGENT
