#!/bin/bash

# Debug script to help diagnose setup issues

echo "🔧 Bitcoin Reused-R Scanner - Setup Diagnostics"
echo "==============================================="

echo ""
echo "📍 Environment Information:"
echo "Current directory: $(pwd)"
echo "User: $(whoami)"
echo "OS: $OSTYPE"
echo "Shell: $SHELL"

echo ""
echo "📂 Directory Contents:"
echo "$(ls -la)"

echo ""
echo "🔍 Looking for project files..."

# Check in current directory
if [ -f "./setup.sh" ]; then
    echo "✅ setup.sh found in current directory"
else
    echo "❌ setup.sh not found in current directory"
fi

if [ -d "./backend" ]; then
    echo "✅ backend directory found"
    echo "   Contents: $(ls -la backend/)"
else
    echo "❌ backend directory not found"
fi

if [ -d "./frontend" ]; then
    echo "✅ frontend directory found"
    echo "   Key files:"
    [ -f "./frontend/.env" ] && echo "   ✅ .env" || echo "   ❌ .env missing"
    [ -f "./frontend/package.json" ] && echo "   ✅ package.json" || echo "   ❌ package.json missing"
    [ -f "./frontend/src/App.js" ] && echo "   ✅ App.js" || echo "   ❌ App.js missing"
else
    echo "❌ frontend directory not found"
fi

echo ""
echo "🛠️ Prerequisites Check:"

# Node.js
if command -v node >/dev/null 2>&1; then
    echo "✅ Node.js: $(node --version)"
else
    echo "❌ Node.js not found"
fi

# Python
if command -v python3 >/dev/null 2>&1; then
    echo "✅ Python: $(python3 --version)"
else
    echo "❌ Python 3 not found"
fi

# Yarn
if command -v yarn >/dev/null 2>&1; then
    echo "✅ Yarn: $(yarn --version)"
else
    echo "❌ Yarn not found"
fi

# MongoDB
if command -v mongod >/dev/null 2>&1; then
    echo "✅ MongoDB installed"
    if pgrep -x "mongod" >/dev/null; then
        echo "   ✅ MongoDB running"
    else
        echo "   ⚠️  MongoDB not running"
    fi
else
    echo "⚠️  MongoDB not found (Docker alternative available)"
fi

echo ""
echo "🌐 Port Status:"
for port in 3000 8001 27017; do
    if lsof -ti:$port >/dev/null 2>&1; then
        process=$(lsof -ti:$port | xargs ps -p 2>/dev/null | tail -1 | awk '{print $4}')
        echo "✅ Port $port: OCCUPIED ($process)"
    else
        echo "❌ Port $port: FREE"
    fi
done

echo ""
echo "📋 Recommendations:"

if [ ! -d "./backend" ] || [ ! -d "./frontend" ]; then
    echo "❌ Project structure missing - ensure you're in the correct directory"
    echo "   Run: cd /path/to/bitcoin-reused-r-scanner"
fi

if [ ! -f "./backend/.env" ]; then
    echo "❌ Backend .env missing - run verify_setup.sh to create it"
fi

if [ ! -f "./frontend/.env" ]; then
    echo "❌ Frontend .env missing - run verify_setup.sh to create it"
fi

if ! command -v node >/dev/null 2>&1; then
    echo "❌ Install Node.js from https://nodejs.org/"
fi

if ! command -v python3 >/dev/null 2>&1; then
    echo "❌ Install Python 3 from https://python.org/"
fi

echo ""
echo "✅ Run this sequence to fix common issues:"
echo "1. ./verify_setup.sh  (creates missing files)"
echo "2. ./setup.sh         (full setup)"
echo "3. ./test_local.sh    (verify everything works)"