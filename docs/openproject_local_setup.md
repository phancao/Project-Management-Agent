# OpenProject Local Docker Setup

Quick guide for setting up and testing OpenProject locally with our PM middleware.

## Quick Start

### 1. Start OpenProject

```bash
# Start only OpenProject services
docker-compose up -d openproject_db openproject

# Or start everything
docker-compose up -d
```

### 2. Wait for OpenProject to Initialize

OpenProject takes 1-2 minutes to start. Check logs:

```bash
docker-compose logs -f openproject
```

Wait until you see:
```
OpenProject is ready!
```

### 3. Access OpenProject

Open in browser: **http://localhost:8080**

### 4. Initial Setup

1. **First Login**: Create admin account
   - Username: `admin`
   - Email: `admin@example.com`
   - Password: Choose a password (remember it!)

2. **Get API Key**:
   - Login as admin
   - Click your avatar (top right) → **My Account**
   - Go to **Access Token** tab
   - Click **Generate Token**
   - Copy the token (e.g., `a1b2c3d4e5f6g7h8i9j0`)

### 5. Configure Environment

Create API key for authentication:

```bash
# Base64 encode: "apikey:your-token"
echo -n "apikey:YOUR_TOKEN_HERE" | base64
```

Add to `.env` file:

```bash
# PM Provider Configuration
PM_PROVIDER=openproject
OPENPROJECT_URL=http://localhost:8080
OPENPROJECT_API_KEY=<your-base64-encoded-key>

# Example:
# PM_PROVIDER=openproject
# OPENPROJECT_URL=http://localhost:8080
# OPENPROJECT_API_KEY=YXBpa2V5OnlvdXItdG9rZW4taGVyZQ==
```

### 6. Test Connection

```python
# Test script
from src.pm_providers import build_pm_provider
from database import get_db_session

db = next(get_db_session())
provider = build_pm_provider(db_session=db)

# Test health
if await provider.health_check():
    print("✅ OpenProject connection successful!")
    
    # List projects
    projects = await provider.list_projects()
    print(f"Found {len(projects)} projects")
else:
    print("❌ Connection failed - check credentials")
```

## Verification Steps

### Check OpenProject is Running

```bash
# Check container status
docker-compose ps openproject

# Check health
curl http://localhost:8080/api/v3/status

# View logs
docker-compose logs openproject
```

### Test API Access

```bash
# Replace YOUR_TOKEN with your actual token
curl -H "Authorization: Basic $(echo -n 'apikey:YOUR_TOKEN' | base64)" \
     http://localhost:8080/api/v3/projects
```

## Common Issues

### Port Already in Use

If port 8080 is taken, change it in `docker-compose.yml`:

```yaml
openproject:
  ports:
    - "8081:80"  # Use 8081 instead
```

Then update `.env`:
```bash
OPENPROJECT_URL=http://localhost:8081
```

### Database Connection Issues

```bash
# Check database is running
docker-compose ps openproject_db

# Check database logs
docker-compose logs openproject_db

# Restart if needed
docker-compose restart openproject_db openproject
```

### API Authentication Fails

1. Verify token is correct
2. Check base64 encoding: `echo -n "apikey:TOKEN" | base64`
3. Ensure token hasn't expired
4. Try regenerating token in OpenProject UI

### Slow Startup

OpenProject can take 2-3 minutes on first start. This is normal!
Check logs: `docker-compose logs -f openproject`

## Stopping OpenProject

```bash
# Stop OpenProject
docker-compose stop openproject openproject_db

# Stop and remove volumes (⚠️ deletes all data)
docker-compose down -v
```

## Next Steps

Once OpenProject is running and configured:

1. **Test PM Middleware**: Use the test script above
2. **Create Test Project**: Via UI or API
3. **Integrate with Flow Manager**: Update handlers to use provider
4. **Sync Data**: Test bi-directional sync

## Default Credentials

After first setup:
- **URL**: http://localhost:8080
- **Admin Username**: `admin` (or whatever you set)
- **Admin Password**: (what you chose during setup)
- **API Token**: Generate in My Account → Access Token

## Production Notes

⚠️ **For Production Use**:
- Change `SECRET_KEY_BASE` environment variable
- Use HTTPS
- Set strong admin password
- Enable authentication
- Configure proper backups

## Resources

- [OpenProject Docker Documentation](https://www.openproject.org/docs/installation-and-operations/installation/docker/)
- [OpenProject API Documentation](https://www.openproject.org/docs/api/)
- [OpenProject Community Edition](https://www.openproject.org/open-source/)

