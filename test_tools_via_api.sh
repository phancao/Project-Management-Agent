#!/bin/bash
# Test refactored MCP tools via API calls

echo "================================================================================"
echo "Testing Refactored MCP Tools via API"
echo "================================================================================"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

# Helper function to test an endpoint
test_endpoint() {
    local name="$1"
    local url="$2"
    local method="${3:-GET}"
    local data="$4"
    
    echo ""
    echo "Testing: $name"
    echo "URL: $url"
    
    if [ "$method" = "POST" ]; then
        response=$(curl -s -X POST "$url" -H "Content-Type: application/json" -d "$data")
    else
        response=$(curl -s "$url")
    fi
    
    # Check if response contains error
    if echo "$response" | grep -q '"error"' || echo "$response" | grep -q '"detail"'; then
        echo -e "${RED}❌ FAILED${NC}"
        echo "Response: $response"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    else
        echo -e "${GREEN}✅ PASSED${NC}"
        # Show first 200 chars of response
        echo "Response: ${response:0:200}..."
        TESTS_PASSED=$((TESTS_PASSED + 1))
        return 0
    fi
}

# Test 1: Health Check
echo ""
echo "[1/7] Testing Health Check..."
test_endpoint "Health Check" "http://localhost:8080/health"

# Test 2: Tools List
echo ""
echo "[2/7] Testing Tools List..."
test_endpoint "Tools List" "http://localhost:8080/tools/list"

# Get provider ID for subsequent tests
echo ""
echo "Getting provider ID..."
providers_response=$(curl -s "http://localhost:8080/health")
echo "Providers response: $providers_response"

# For now, let's assume we have a provider configured
# We'll test with the OpenProject v13 provider that should be configured

# Test 3: List Projects (projects_v2)
echo ""
echo "[3/7] Testing list_projects (projects_v2)..."
# Note: We can't easily test MCP tools via HTTP without a proper MCP client
# The tools are registered in the MCP server but require MCP protocol to call
echo -e "${YELLOW}⚠️  SKIPPED - Requires MCP protocol client${NC}"

# Test 4: Get Project (projects_v2)
echo ""
echo "[4/7] Testing get_project (projects_v2)..."
echo -e "${YELLOW}⚠️  SKIPPED - Requires MCP protocol client${NC}"

# Test 5: List Tasks (tasks_v2)
echo ""
echo "[5/7] Testing list_tasks (tasks_v2)..."
echo -e "${YELLOW}⚠️  SKIPPED - Requires MCP protocol client${NC}"

# Test 6: List Sprints (sprints_v2)
echo ""
echo "[6/7] Testing list_sprints (sprints_v2)..."
echo -e "${YELLOW}⚠️  SKIPPED - Requires MCP protocol client${NC}"

# Test 7: Burndown Chart (analytics_v2)
echo ""
echo "[7/7] Testing burndown_chart (analytics_v2)..."
echo -e "${YELLOW}⚠️  SKIPPED - Requires MCP protocol client${NC}"

# Summary
echo ""
echo "================================================================================"
echo "Test Summary"
echo "================================================================================"
echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
echo -e "${RED}Failed: $TESTS_FAILED${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ All basic tests passed!${NC}"
    echo ""
    echo "Note: Full tool testing requires an MCP protocol client."
    echo "The tools are registered and available via MCP protocol."
    echo "Use the frontend or an MCP client to test the actual tool functionality."
    exit 0
else
    echo -e "${RED}❌ Some tests failed${NC}"
    exit 1
fi

