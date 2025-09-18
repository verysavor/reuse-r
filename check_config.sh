#!/bin/bash

# Configuration Checker - Debug the frontend/backend URL bug

echo "🔍 Bitcoin Reused-R Scanner - Configuration Check"
echo "================================================"

echo ""
echo "📂 Current Directory: $(pwd)"
echo ""

echo "🔧 Backend Configuration:"
echo "------------------------"
if [ -f "backend/.env" ]; then
    echo "✅ backend/.env exists"
    echo "   Contents:"
    cat backend/.env | sed 's/^/   /'
else
    echo "❌ backend/.env not found"
fi

echo ""
echo "🎨 Frontend Configuration:"
echo "-------------------------"
if [ -f "frontend/.env" ]; then
    echo "✅ frontend/.env exists"
    echo "   Contents:"
    cat frontend/.env | sed 's/^/   /'
    
    echo ""
    echo "🔍 Backend URL Analysis:"
    BACKEND_URL=$(grep REACT_APP_BACKEND_URL frontend/.env | cut -d'=' -f2)
    if [[ "$BACKEND_URL" == *"localhost"* ]]; then
        echo "   ✅ CORRECT: Points to localhost ($BACKEND_URL)"
    elif [[ "$BACKEND_URL" == *"preview.emergentagent.com"* ]]; then
        echo "   ❌ BUG DETECTED: Points to remote preview backend!"
        echo "   🔧 Fix command: sed -i '' 's|REACT_APP_BACKEND_URL=.*|REACT_APP_BACKEND_URL=http://localhost:8001|' frontend/.env"
    else
        echo "   ⚠️  UNKNOWN: Points to $BACKEND_URL"
    fi
else
    echo "❌ frontend/.env not found"
fi

echo ""
echo "🌐 Port Check:"
echo "-------------"
if lsof -ti:8001 > /dev/null 2>&1; then
    echo "✅ Port 8001 (backend): OCCUPIED"
    echo "   Process: $(lsof -ti:8001 | xargs ps -p | tail -1)"
else
    echo "❌ Port 8001 (backend): FREE"
fi

if lsof -ti:3000 > /dev/null 2>&1; then
    echo "✅ Port 3000 (frontend): OCCUPIED"
    echo "   Process: $(lsof -ti:3000 | xargs ps -p | tail -1)"
else
    echo "❌ Port 3000 (frontend): FREE"
fi

echo ""
echo "🧪 Quick API Test:"
echo "-----------------"
if curl -s http://localhost:8001/api/current-height > /dev/null 2>&1; then
    RESPONSE=$(curl -s http://localhost:8001/api/current-height)
    echo "✅ Backend API: WORKING"
    echo "   Response: $RESPONSE"
else
    echo "❌ Backend API: NOT RESPONDING"
fi

if curl -s http://localhost:3000 > /dev/null 2>&1; then
    echo "✅ Frontend: ACCESSIBLE"
else
    echo "❌ Frontend: NOT ACCESSIBLE"
fi

echo ""
echo "📊 Summary:"
echo "----------"
if [ -f "frontend/.env" ]; then
    BACKEND_URL=$(grep REACT_APP_BACKEND_URL frontend/.env | cut -d'=' -f2)
    if [[ "$BACKEND_URL" == *"localhost"* ]]; then
        echo "✅ Configuration looks correct"
    else
        echo "❌ Configuration bug detected - frontend points to remote backend"
        echo "   Run this to fix: sed -i '' 's|REACT_APP_BACKEND_URL=.*|REACT_APP_BACKEND_URL=http://localhost:8001|' frontend/.env"
    fi
else
    echo "❌ Missing configuration files"
fi