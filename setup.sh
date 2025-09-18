#!/bin/bash

# Bitcoin Reused-R Scanner - Local Setup Script for Mac
# This script sets up and tests the application locally

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}$1${NC}"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

print_header "🚀 Bitcoin Reused-R Scanner - Local Setup"
print_header "=========================================="

# Check prerequisites
print_status "Checking prerequisites..."

# Check Node.js
if command_exists node; then
    NODE_VERSION=$(node --version)
    print_status "Node.js found: $NODE_VERSION"
else
    print_error "Node.js not found. Please install Node.js 18+ from https://nodejs.org/"
    exit 1
fi

# Check Python
if command_exists python3; then
    PYTHON_VERSION=$(python3 --version)
    print_status "Python found: $PYTHON_VERSION"
else
    print_error "Python 3 not found. Please install Python 3.11+ from https://python.org/"
    exit 1
fi

# Check if we're on Mac
if [[ "$OSTYPE" == "darwin"* ]]; then
    print_status "macOS detected"
    
    # Check Homebrew
    if command_exists brew; then
        print_status "Homebrew found"
    else
        print_warning "Homebrew not found. Install from https://brew.sh/ for easier MongoDB setup"
    fi
else
    print_warning "Not running on macOS. Some commands may need adjustment."
fi

# Check yarn
if command_exists yarn; then
    YARN_VERSION=$(yarn --version)
    print_status "Yarn found: $YARN_VERSION"
else
    print_warning "Yarn not found. Installing via npm..."
    npm install -g yarn
fi

print_header "\n📦 Setting up Backend..."

# Backend setup
cd backend

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    print_status "Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
print_status "Activating virtual environment..."
source venv/bin/activate

# Install Python dependencies
print_status "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

print_header "\n🎨 Setting up Frontend..."

# Frontend setup
cd ../frontend

# Install Node dependencies
print_status "Installing Node.js dependencies..."
yarn install

print_header "\n🗄️ Setting up Database..."

# MongoDB setup
print_status "Checking MongoDB..."

if command_exists mongod; then
    print_status "MongoDB found locally"
    
    # Check if MongoDB is running
    if pgrep -x "mongod" > /dev/null; then
        print_status "MongoDB is already running"
    else
        print_status "Starting MongoDB..."
        if command_exists brew; then
            brew services start mongodb/brew/mongodb-community || {
                print_warning "Failed to start MongoDB with brew. Trying alternative..."
                mongod --dbpath /usr/local/var/mongodb --logpath /usr/local/var/log/mongodb/mongo.log --fork || {
                    print_error "Failed to start MongoDB. Please start it manually."
                }
            }
        else
            mongod --dbpath ./data/db --logpath ./data/log/mongodb.log --fork || {
                print_error "Failed to start MongoDB. Please ensure it's installed and configured."
            }
        fi
    fi
elif command_exists docker; then
    print_status "MongoDB not found locally. Using Docker..."
    
    # Check if MongoDB container is running
    if docker ps | grep -q mongodb-reused-r; then
        print_status "MongoDB Docker container is already running"
    else
        print_status "Starting MongoDB in Docker..."
        docker run -d \
            --name mongodb-reused-r \
            -p 27017:27017 \
            -v mongodb_data:/data/db \
            mongo:5.0
    fi
else
    print_error "Neither MongoDB nor Docker found. Please install one of them:"
    print_error "- MongoDB: https://docs.mongodb.com/manual/installation/"
    print_error "- Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

# Wait for MongoDB to be ready
print_status "Waiting for MongoDB to be ready..."
sleep 3

# Test MongoDB connection
print_status "Testing MongoDB connection..."
if command_exists mongosh; then
    mongosh --eval "db.adminCommand('ping')" --quiet || {
        print_error "Failed to connect to MongoDB"
        exit 1
    }
    print_status "MongoDB connection successful"
elif command_exists mongo; then
    mongo --eval "db.adminCommand('ping')" --quiet || {
        print_error "Failed to connect to MongoDB"
        exit 1
    }
    print_status "MongoDB connection successful"
else
    print_warning "MongoDB shell not found. Assuming MongoDB is running..."
fi

print_header "\n⚙️ Configuration Check..."

# Check environment files
cd ..

# Backend environment
BACKEND_ENV_PATH="backend/.env"
if [ -f "$BACKEND_ENV_PATH" ]; then
    print_status "Backend .env file found at $BACKEND_ENV_PATH"
    
    # Check if MONGO_URL is set to localhost
    if grep -q "MONGO_URL.*localhost" "$BACKEND_ENV_PATH"; then
        print_status "✅ Backend configured for local MongoDB"
    else
        print_warning "Backend .env may not be configured for local development"
    fi
else
    print_error "Backend .env file not found at $BACKEND_ENV_PATH"
    print_status "Creating backend .env file..."
    
    # Create the missing .env file
    cat > "$BACKEND_ENV_PATH" << 'EOF'
MONGO_URL="mongodb://localhost:27017"
DB_NAME="bitcoin_reused_r_scanner"
CORS_ORIGINS="*"
EOF
    
    if [ -f "$BACKEND_ENV_PATH" ]; then
        print_status "✅ Created backend .env file"
    else
        print_error "Failed to create backend .env file"
        exit 1
    fi
fi

# Frontend environment
FRONTEND_ENV_PATH="frontend/.env"
if [ -f "$FRONTEND_ENV_PATH" ]; then
    print_status "Frontend .env file found at $FRONTEND_ENV_PATH"
    
    # Check if REACT_APP_BACKEND_URL points to localhost
    if grep -q "REACT_APP_BACKEND_URL.*localhost" "$FRONTEND_ENV_PATH"; then
        print_status "✅ Frontend configured for local backend"
    else
        print_error "❌ Frontend .env points to remote backend!"
        print_error "This is the bug you mentioned. Fixing now..."
        
        # Fix the configuration
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' 's|REACT_APP_BACKEND_URL=.*|REACT_APP_BACKEND_URL=http://localhost:8001|' "$FRONTEND_ENV_PATH"
        else
            sed -i 's|REACT_APP_BACKEND_URL=.*|REACT_APP_BACKEND_URL=http://localhost:8001|' "$FRONTEND_ENV_PATH"
        fi
        print_status "✅ Fixed: Frontend now points to local backend"
    fi
else
    print_error "Frontend .env file not found at $FRONTEND_ENV_PATH"
    print_status "Creating frontend .env file..."
    
    # Create the missing .env file
    cat > "$FRONTEND_ENV_PATH" << 'EOF'
REACT_APP_BACKEND_URL=http://localhost:8001
WDS_SOCKET_PORT=443
EOF
    
    if [ -f "$FRONTEND_ENV_PATH" ]; then
        print_status "✅ Created frontend .env file"
    else
        print_error "Failed to create frontend .env file"
        exit 1
    fi
fi

print_header "\n🧪 Starting Test Services..."

# Kill any existing processes on our ports
print_status "Cleaning up any existing processes..."
lsof -ti:8001 | xargs kill -9 2>/dev/null || true
lsof -ti:3000 | xargs kill -9 2>/dev/null || true

# Start backend in background
print_status "Starting backend server..."
cd backend
source venv/bin/activate
python -m uvicorn server:app --host 0.0.0.0 --port 8001 --reload > ../backend.log 2>&1 &
BACKEND_PID=$!
cd ..

# Wait for backend to start
print_status "Waiting for backend to start..."
sleep 5

# Test backend
print_status "Testing backend API..."
BACKEND_RESPONSE=$(curl -s http://localhost:8001/api/current-height || echo "FAILED")

if [[ "$BACKEND_RESPONSE" == *"height"* ]]; then
    print_status "✅ Backend API is working!"
    echo "   Response: $BACKEND_RESPONSE"
else
    print_error "❌ Backend API test failed"
    print_error "Backend logs:"
    tail -10 backend.log
    kill $BACKEND_PID 2>/dev/null || true
    exit 1
fi

# Start frontend in background
print_status "Starting frontend server..."
cd frontend
BROWSER=none yarn start > ../frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..

# Wait for frontend to start
print_status "Waiting for frontend to start..."
sleep 10

# Test frontend
print_status "Testing frontend..."
FRONTEND_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000 || echo "000")

if [ "$FRONTEND_RESPONSE" = "200" ]; then
    print_status "✅ Frontend is working!"
else
    print_error "❌ Frontend test failed (HTTP: $FRONTEND_RESPONSE)"
    print_error "Frontend logs:"
    tail -10 frontend.log
fi

print_header "\n🎯 Integration Test..."

# Test the integration by checking if frontend can reach backend
print_status "Testing frontend-backend integration..."
sleep 2

# Check backend logs for frontend requests
if grep -q "127.0.0.1" backend.log; then
    print_status "✅ Frontend is calling local backend (127.0.0.1 found in logs)"
else
    print_warning "⚠️  No localhost requests found in backend logs yet"
fi

print_header "\n✅ Setup Complete!"
print_header "=================="

print_status "🎉 Bitcoin Reused-R Scanner is ready!"
echo ""
print_status "📍 Access Points:"
print_status "   • Frontend: http://localhost:3000"
print_status "   • Backend API: http://localhost:8001"
print_status "   • API Docs: http://localhost:8001/docs"
echo ""
print_status "🔧 Process IDs:"
print_status "   • Backend PID: $BACKEND_PID"
print_status "   • Frontend PID: $FRONTEND_PID"
echo ""
print_status "📋 To stop services:"
print_status "   kill $BACKEND_PID $FRONTEND_PID"
echo ""
print_status "📄 Log files:"
print_status "   • Backend: backend.log"
print_status "   • Frontend: frontend.log"
echo ""

# Test a simple scan
print_header "🧪 Running Quick Integration Test..."
print_status "Testing scan functionality..."

SCAN_RESPONSE=$(curl -s -X POST "http://localhost:8001/api/scan/start" \
  -H "Content-Type: application/json" \
  -d '{"start_block": 1, "end_block": 3, "address_types": ["legacy"]}' || echo "FAILED")

if [[ "$SCAN_RESPONSE" == *"scan_id"* ]]; then
    print_status "✅ Scan API is working!"
    
    # Extract scan ID
    SCAN_ID=$(echo "$SCAN_RESPONSE" | grep -o '"scan_id":"[^"]*"' | cut -d'"' -f4)
    print_status "   Scan ID: $SCAN_ID"
    
    # Wait a moment and check progress
    sleep 3
    PROGRESS_RESPONSE=$(curl -s "http://localhost:8001/api/scan/progress/$SCAN_ID" || echo "FAILED")
    
    if [[ "$PROGRESS_RESPONSE" == *"status"* ]]; then
        print_status "✅ Progress tracking is working!"
    else
        print_warning "⚠️  Progress tracking may have issues"
    fi
else
    print_warning "⚠️  Scan test failed, but basic setup is complete"
fi

print_header "\n🎯 Next Steps:"
print_status "1. Open http://localhost:3000 in your browser"
print_status "2. Try scanning a small block range (e.g., 1-10)"
print_status "3. Monitor the real-time progress and logs"
print_status "4. Check the Results tab for any recovered keys"
print_status "5. Test the balance checking feature"
echo ""
print_warning "⚠️  Remember: This tool is for educational/research purposes only!"
print_warning "    Use responsibly and legally."
echo ""

# Create a stop script
cat > stop_services.sh << 'EOF'
#!/bin/bash
echo "Stopping Bitcoin Reused-R Scanner services..."
kill $(cat backend_pid.txt) 2>/dev/null || true
kill $(cat frontend_pid.txt) 2>/dev/null || true
echo "Services stopped."
rm -f backend_pid.txt frontend_pid.txt
EOF

echo "$BACKEND_PID" > backend_pid.txt
echo "$FRONTEND_PID" > frontend_pid.txt
chmod +x stop_services.sh

print_status "💡 To stop all services later, run: ./stop_services.sh"
echo ""
print_header "🚀 Setup Complete! The application is running and ready for testing."