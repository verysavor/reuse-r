#!/bin/bash

# Quick verification script to check if all files are in place

echo "🔍 Bitcoin Reused-R Scanner - Setup Verification"
echo "================================================"

echo ""
echo "📂 Directory Structure:"
echo "$(pwd)"
if [ -d "backend" ]; then
    echo "✅ backend/ directory exists"
else
    echo "❌ backend/ directory missing"
fi

if [ -d "frontend" ]; then
    echo "✅ frontend/ directory exists"
else
    echo "❌ frontend/ directory missing"
fi

echo ""
echo "📄 Configuration Files:"

# Backend files
if [ -f "backend/.env" ]; then
    echo "✅ backend/.env exists"
    echo "   Contents:"
    cat backend/.env | sed 's/^/   /'
else
    echo "❌ backend/.env missing"
    echo "   Creating now..."
    cat > backend/.env << 'EOF'
MONGO_URL="mongodb://localhost:27017"
DB_NAME="bitcoin_reused_r_scanner"
CORS_ORIGINS="*"
EOF
    echo "✅ Created backend/.env"
fi

if [ -f "backend/server.py" ]; then
    echo "✅ backend/server.py exists"
else
    echo "❌ backend/server.py missing"
fi

if [ -f "backend/requirements.txt" ]; then
    echo "✅ backend/requirements.txt exists"
else
    echo "❌ backend/requirements.txt missing"
fi

# Frontend files
if [ -f "frontend/.env" ]; then
    echo "✅ frontend/.env exists"
    echo "   Contents:"
    cat frontend/.env | sed 's/^/   /'
    
    # Check for the bug
    BACKEND_URL=$(grep REACT_APP_BACKEND_URL frontend/.env | cut -d'=' -f2)
    if [[ "$BACKEND_URL" == *"localhost"* ]]; then
        echo "   ✅ Correctly points to localhost"
    else
        echo "   ❌ BUG: Points to remote backend!"
        echo "   Fixing..."
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' 's|REACT_APP_BACKEND_URL=.*|REACT_APP_BACKEND_URL=http://localhost:8001|' frontend/.env
        else
            sed -i 's|REACT_APP_BACKEND_URL=.*|REACT_APP_BACKEND_URL=http://localhost:8001|' frontend/.env
        fi
        echo "   ✅ Fixed: Now points to localhost"
    fi
else
    echo "❌ frontend/.env missing"
    echo "   Creating now..."
    cat > frontend/.env << 'EOF'
REACT_APP_BACKEND_URL=http://localhost:8001
WDS_SOCKET_PORT=443
EOF
    echo "✅ Created frontend/.env"
fi

if [ -f "frontend/package.json" ]; then
    echo "✅ frontend/package.json exists"
else
    echo "❌ frontend/package.json missing"
fi

if [ -f "frontend/src/App.js" ]; then
    echo "✅ frontend/src/App.js exists"
else
    echo "❌ frontend/src/App.js missing"
fi

echo ""
echo "🧪 Quick Tests:"

# Test MongoDB (if available)
if command -v mongosh >/dev/null 2>&1; then
    if mongosh --eval "db.adminCommand('ping')" --quiet 2>/dev/null; then
        echo "✅ MongoDB connection working"
    else
        echo "⚠️  MongoDB not responding (may need to start it)"
    fi
elif command -v mongo >/dev/null 2>&1; then
    if mongo --eval "db.adminCommand('ping')" --quiet 2>/dev/null; then
        echo "✅ MongoDB connection working"
    else
        echo "⚠️  MongoDB not responding (may need to start it)"
    fi
else
    echo "⚠️  MongoDB shell not found"
fi

# Test if services are running
if lsof -ti:8001 >/dev/null 2>&1; then
    echo "✅ Backend service running on port 8001"
    if curl -s http://localhost:8001/api/current-height >/dev/null 2>&1; then
        echo "✅ Backend API responding"
    else
        echo "⚠️  Backend not responding to API calls"
    fi
else
    echo "⚠️  Backend not running on port 8001"
fi

if lsof -ti:3000 >/dev/null 2>&1; then
    echo "✅ Frontend service running on port 3000"
else
    echo "⚠️  Frontend not running on port 3000"
fi

echo ""
echo "📊 Summary:"
if [ -f "backend/.env" ] && [ -f "frontend/.env" ] && [ -f "backend/server.py" ] && [ -f "frontend/package.json" ]; then
    echo "✅ All essential files are present"
    echo "✅ Ready to run setup.sh"
else
    echo "❌ Some files are missing - check the output above"
fi

echo ""
echo "💡 Next steps:"
echo "1. Run: ./setup.sh (for full setup)"
echo "2. Or manually start services:"
echo "   Backend: cd backend && python -m uvicorn server:app --host 0.0.0.0 --port 8001 --reload"
echo "   Frontend: cd frontend && yarn start"