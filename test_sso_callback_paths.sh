#!/bin/bash
# Test common Azure AD callback paths
# Usage: ./test_sso_callback_paths.sh

echo "=============================================="
echo "Azure AD OAuth Callback Path Tester"
echo "=============================================="
echo ""
echo "This script helps you find the correct callback path"
echo "that matches your Azure Portal configuration."
echo ""
echo "Common callback paths to try:"
echo ""
echo "  1. (empty)                    -> http://localhost:8080"
echo "  2. /callback                  -> http://localhost:8080/callback"
echo "  3. /auth/callback             -> http://localhost:8080/auth/callback"  
echo "  4. /oauth/callback            -> http://localhost:8080/oauth/callback"
echo "  5. /api/auth/callback/azure-ad -> http://localhost:8080/api/auth/callback/azure-ad (NextAuth)"
echo "  6. /signin-oidc               -> http://localhost:8080/signin-oidc (ASP.NET)"
echo ""
echo "=============================================="
echo ""

# Get user choice
read -p "Enter the callback path to test (e.g., /callback): " callback_path

# Update .env file
if grep -q "AUTH_CALLBACK_PATH" .env; then
    # Update existing
    sed -i '' "s|AUTH_CALLBACK_PATH=.*|AUTH_CALLBACK_PATH=${callback_path}|" .env
else
    # Add new
    echo "AUTH_CALLBACK_PATH=${callback_path}" >> .env
fi

echo ""
echo "Updated .env with AUTH_CALLBACK_PATH=${callback_path}"
echo ""
echo "Full redirect URI will be: http://localhost:8080${callback_path}"
echo ""

# Restart backend to pick up changes
echo "Restarting backend..."
docker compose up -d api --force-recreate

echo ""
echo "Done! Try logging in again at http://localhost:8080/login"
echo ""
echo "If it still fails, run this script again with a different path."
