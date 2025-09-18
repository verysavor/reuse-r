#!/bin/bash

# Bitcoin Reused-R Scanner - Local Testing Script
# Quick test script to verify all components are working

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}[TEST]${NC} $1"
}

print_error() {
    echo -e "${RED}[FAIL]${NC} $1"
}

print_header() {
    echo -e "${BLUE}$1${NC}"
}

print_header "🧪 Bitcoin Reused-R Scanner - Local Test Suite"
print_header "=============================================="

# Test 1: Backend Health Check
print_status "Testing backend health..."
BACKEND_HEALTH=$(curl -s http://localhost:8001/api/current-height || echo "FAILED")

if [[ "$BACKEND_HEALTH" == *"height"* ]]; then
    print_status "✅ Backend is healthy"
    echo "   Current blockchain height: $(echo $BACKEND_HEALTH | grep -o '"height":[0-9]*' | cut -d':' -f2)"
else
    print_error "❌ Backend health check failed"
    echo "   Make sure backend is running on port 8001"
    exit 1
fi

# Test 2: Frontend Accessibility
print_status "Testing frontend accessibility..."
FRONTEND_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000 || echo "000")

if [ "$FRONTEND_STATUS" = "200" ]; then
    print_status "✅ Frontend is accessible"
else
    print_error "❌ Frontend not accessible (HTTP: $FRONTEND_STATUS)"
    echo "   Make sure frontend is running on port 3000"
fi

# Test 3: MongoDB Connection
print_status "Testing MongoDB connection..."
if command -v mongosh >/dev/null 2>&1; then
    MONGO_TEST=$(mongosh --eval "db.adminCommand('ping')" --quiet 2>/dev/null || echo "FAILED")
    if [[ "$MONGO_TEST" == *"ok"* ]]; then
        print_status "✅ MongoDB is connected"
    else
        print_error "❌ MongoDB connection failed"
    fi
elif command -v mongo >/dev/null 2>&1; then
    MONGO_TEST=$(mongo --eval "db.adminCommand('ping')" --quiet 2>/dev/null || echo "FAILED")
    if [[ "$MONGO_TEST" == *"ok"* ]]; then
        print_status "✅ MongoDB is connected"
    else
        print_error "❌ MongoDB connection failed"
    fi
else
    print_status "⚠️  MongoDB shell not found, skipping direct test"
fi

# Test 4: Environment Configuration
print_status "Testing environment configuration..."

# Check backend env
if grep -q "localhost" backend/.env; then
    print_status "✅ Backend configured for localhost"
else
    print_error "❌ Backend not configured for localhost"
fi

# Check frontend env
if grep -q "localhost:8001" frontend/.env; then
    print_status "✅ Frontend pointing to local backend"
else
    print_error "❌ Frontend not pointing to local backend"
    echo "   This is the configuration bug!"
    echo "   Run: sed -i '' 's|REACT_APP_BACKEND_URL=.*|REACT_APP_BACKEND_URL=http://localhost:8001|' frontend/.env"
fi

# Test 5: API Endpoints
print_status "Testing API endpoints..."

# Test scan list endpoint
SCAN_LIST=$(curl -s http://localhost:8001/api/scan/list || echo "FAILED")
if [[ "$SCAN_LIST" == *"scans"* ]]; then
    print_status "✅ Scan list endpoint working"
else
    print_error "❌ Scan list endpoint failed"
fi

# Test 6: Quick Scan Test
print_status "Testing scan functionality..."
SCAN_TEST=$(curl -s -X POST "http://localhost:8001/api/scan/start" \
  -H "Content-Type: application/json" \
  -d '{"start_block": 1, "end_block": 2, "address_types": ["legacy"]}' || echo "FAILED")

if [[ "$SCAN_TEST" == *"scan_id"* ]]; then
    print_status "✅ Scan creation working"
    
    # Extract scan ID and test progress
    SCAN_ID=$(echo "$SCAN_TEST" | grep -o '"scan_id":"[^"]*"' | cut -d'"' -f4)
    sleep 2
    
    PROGRESS_TEST=$(curl -s "http://localhost:8001/api/scan/progress/$SCAN_ID" || echo "FAILED")
    if [[ "$PROGRESS_TEST" == *"status"* ]]; then
        print_status "✅ Progress tracking working"
    else
        print_error "❌ Progress tracking failed"
    fi
else
    print_error "❌ Scan creation failed"
fi

# Test 7: Balance Check API
print_status "Testing balance check API..."
BALANCE_TEST=$(curl -s -X POST "http://localhost:8001/api/balance/check" \
  -H "Content-Type: application/json" \
  -d '["1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"]' || echo "FAILED")

if [[ "$BALANCE_TEST" == *"balances"* ]]; then
    print_status "✅ Balance check API working"
else
    print_error "❌ Balance check API failed"
fi

print_header "\n📊 Test Summary"
print_header "==============="

print_status "🎯 All core functionality tested!"
echo ""
print_status "📍 Application URLs:"
print_status "   • Frontend: http://localhost:3000"
print_status "   • Backend: http://localhost:8001"
print_status "   • API Docs: http://localhost:8001/docs"
echo ""
print_status "🔧 Manual Testing Steps:"
print_status "1. Open http://localhost:3000"
print_status "2. Start a scan with blocks 1-10"
print_status "3. Monitor progress in real-time"
print_status "4. Check results and logs tabs"
print_status "5. Test balance checking if any keys found"
echo ""
print_status "✅ Local testing complete!"