#!/bin/bash

# Quick setup script for OpenProject Docker instance

set -e

echo "🚀 Setting up OpenProject for local testing..."
echo ""

# Check if Docker is running
if ! docker ps > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Start OpenProject services
echo "📦 Starting OpenProject containers..."
docker-compose up -d openproject_db openproject

echo ""
echo "⏳ Waiting for OpenProject to initialize (this may take 1-2 minutes)..."
echo ""

# Wait for OpenProject to be ready
MAX_WAIT=180
WAITED=0
while [ $WAITED -lt $MAX_WAIT ]; do
    if curl -s -f http://localhost:8080/api/v3/status > /dev/null 2>&1; then
        echo ""
        echo "✅ OpenProject is ready!"
        break
    fi
    echo -n "."
    sleep 5
    WAITED=$((WAITED + 5))
done

if [ $WAITED -ge $MAX_WAIT ]; then
    echo ""
    echo "⚠️  OpenProject is taking longer than expected."
    echo "   Check logs: docker-compose logs openproject"
    echo "   Or access http://localhost:8080 manually"
    exit 1
fi

echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "✅ OpenProject is running!"
echo ""
echo "📍 Access URL: http://localhost:8080"
echo ""
echo "📝 Next Steps:"
echo "   1. Open http://localhost:8080 in your browser"
echo "   2. Create admin account (first time only)"
echo "   3. Go to My Account → Access Token → Generate Token"
echo "   4. Base64 encode: echo -n 'apikey:YOUR_TOKEN' | base64"
echo "   5. Add to .env:"
echo "      PM_PROVIDER=openproject"
echo "      OPENPROJECT_URL=http://localhost:8080"
echo "      OPENPROJECT_API_KEY=<your-base64-key>"
echo ""
echo "🧪 Test connection:"
echo "   python scripts/test_openproject.py"
echo ""
echo "📚 Full guide: docs/openproject_local_setup.md"
echo "═══════════════════════════════════════════════════════════════════"

