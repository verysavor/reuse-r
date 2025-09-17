# Bitcoin Reused-R Scanner

<div align="center">
  <img src="https://img.shields.io/badge/Security-Research-red" alt="Security Research">
  <img src="https://img.shields.io/badge/React-19.0.0-blue" alt="React">
  <img src="https://img.shields.io/badge/FastAPI-0.110.1-green" alt="FastAPI">
  <img src="https://img.shields.io/badge/MongoDB-5.0-green" alt="MongoDB">
  <img src="https://img.shields.io/badge/License-MIT-yellow" alt="License">
</div>

A sophisticated web application that detects **ECDSA nonce reuse vulnerabilities** in Bitcoin transactions. When the same R value (nonce) is used twice in ECDSA signatures with the same private key, the private key can be mathematically recovered - demonstrating a critical cryptographic vulnerability.

## 🚨 **SECURITY NOTICE**

**FOR EDUCATIONAL AND RESEARCH PURPOSES ONLY**

This tool demonstrates real cryptographic vulnerabilities in Bitcoin transactions. Use responsibly and only on data you own or have explicit permission to analyze.

## ✨ **Features**

### 🔐 **Core Cryptographic Analysis**
- **ECDSA Signature Extraction**: Parses Bitcoin transaction signatures from multiple address types
- **R Value Reuse Detection**: Identifies signatures that reuse the same R value (nonce)
- **Private Key Recovery**: Mathematically recovers private keys from vulnerable signatures
- **Address Generation**: Generates Bitcoin addresses from recovered private keys
- **Multi-Address Support**: Handles Legacy (P2PKH), SegWit (P2WPKH), and Taproot (P2TR) addresses

### 🌐 **Live Blockchain Integration**
- **Public API Integration**: Uses Blockstream API and mempool.space for real-time Bitcoin data
- **No Bitcoin Node Required**: Completely cloud-based using public APIs
- **Current Block Height**: Displays live blockchain height
- **Balance Verification**: Real-time Bitcoin address balance checking

### 💻 **Advanced Frontend**
- **Modern React UI**: Beautiful dark gradient design with Bitcoin branding
- **Real-time Progress**: Live progress bars, statistics, and scan logs
- **Tabbed Interface**: Scanner, Results, and Logs tabs for organized workflow
- **Responsive Design**: Works on desktop, tablet, and mobile
- **Export Functionality**: JSON export of scan results
- **Balance Integration**: One-click balance checking for recovered addresses

### ⚡ **Robust Backend**
- **FastAPI**: Async processing with background tasks
- **RESTful API**: 9 comprehensive endpoints
- **Real-time Updates**: Progress tracking and live log streaming
- **Error Handling**: Proper HTTP status codes and validation
- **Rate Limiting**: Built-in delays to respect public API limits

## 🏗️ **Architecture**

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   React Frontend│────│   FastAPI       │────│   MongoDB       │
│   (Port 3000)  │    │   Backend       │    │   Database      │
│                 │    │   (Port 8001)   │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Blockchain    │    │   Cryptographic │    │   Scan Results  │
│   APIs          │    │   Functions     │    │   Storage       │
│   (External)    │    │   (ECDSA)       │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🛠️ **Tech Stack**

- **Frontend**: React 19, TypeScript, Tailwind CSS, shadcn/ui
- **Backend**: FastAPI, Python 3.11, AsyncIO
- **Database**: MongoDB
- **APIs**: Blockstream API, mempool.space
- **Cryptography**: Custom ECDSA implementation
- **UI Components**: shadcn/ui, Lucide React icons

## 🚀 **Quick Start**

### Prerequisites

- **Node.js** (v18 or higher)
- **Python** (3.11 or higher)
- **MongoDB** (5.0 or higher)
- **Git**

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd bitcoin-reused-r-scanner
```

### 2. Run Setup Script (Mac/Linux)

```bash
chmod +x setup.sh
./setup.sh
```

### 3. Manual Setup (Alternative)

#### Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

#### Frontend Setup
```bash
cd frontend
yarn install
```

#### Database Setup
```bash
# Start MongoDB (Mac with Homebrew)
brew services start mongodb/brew/mongodb-community

# Or using Docker
docker run -d -p 27017:27017 --name mongodb mongo:5.0
```

### 4. Start the Application

#### Backend
```bash
cd backend
python -m uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

#### Frontend
```bash
cd frontend
yarn start
```

### 5. Access the Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8001
- **API Documentation**: http://localhost:8001/docs

## 📖 **Usage Guide**

### **Starting a Scan**

1. **Configure Scan Parameters**:
   - Set start and end block numbers
   - Select address types (Legacy, SegWit, Taproot)

2. **Start the Scan**:
   - Click "Start Scan" button
   - Monitor real-time progress

3. **View Results**:
   - Switch to "Results" tab
   - View recovered private keys
   - Check address balances

### **Understanding Results**

Each recovered key shows:
- **Private Key**: 64-character hexadecimal string
- **Bitcoin Addresses**: Both compressed and uncompressed formats
- **Transaction Details**: Source transactions where vulnerability was found
- **Validation Status**: Whether the key recovery was successful

### **Export Options**

- **JSON Export**: Download complete scan results
- **Balance Check**: Verify if recovered addresses contain Bitcoin
- **Scan History**: View all previous scans

## 🔧 **API Reference**

### **Endpoints**

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/current-height` | Get current blockchain height |
| `POST` | `/api/scan/start` | Start a new vulnerability scan |
| `GET` | `/api/scan/progress/{scan_id}` | Get scan progress |
| `GET` | `/api/scan/results/{scan_id}` | Get scan results |
| `POST` | `/api/scan/stop/{scan_id}` | Stop a running scan |
| `POST` | `/api/balance/check` | Check address balances |
| `GET` | `/api/scan/export/{scan_id}` | Export scan results |
| `GET` | `/api/scan/list` | List all scans |

### **Example Request**

```bash
# Start a new scan
curl -X POST "http://localhost:8001/api/scan/start" \
  -H "Content-Type: application/json" \
  -d '{
    "start_block": 1,
    "end_block": 100,
    "address_types": ["legacy", "segwit"]
  }'
```

## 🧪 **Testing**

### **Run Tests**
```bash
# Backend tests
cd backend
python -m pytest

# Frontend tests
cd frontend
yarn test
```

### **Manual Testing**
```bash
# Test blockchain height API
curl http://localhost:8001/api/current-height

# Test balance checking
curl -X POST "http://localhost:8001/api/balance/check" \
  -H "Content-Type: application/json" \
  -d '["1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"]'
```

## 📁 **Project Structure**

```
bitcoin-reused-r-scanner/
├── backend/                 # FastAPI backend
│   ├── server.py           # Main application
│   ├── requirements.txt    # Python dependencies
│   └── .env               # Environment variables
├── frontend/               # React frontend
│   ├── src/
│   │   ├── components/    # React components
│   │   ├── App.js        # Main application
│   │   └── App.css       # Styles
│   ├── package.json      # Node dependencies
│   └── .env             # Environment variables
├── setup.sh             # Setup script
├── ENVIRONMENT_SETUP.md # Configuration guide
└── README.md           # This file
```

## 🔒 **Security & Ethics**

### **Educational Purpose**
This tool is designed for:
- ✅ Educational demonstration of cryptographic vulnerabilities
- ✅ Security research and analysis
- ✅ Understanding ECDSA implementation weaknesses
- ✅ Blockchain security auditing (with permission)

### **Prohibited Uses**
- ❌ Unauthorized access to private keys
- ❌ Theft or misuse of cryptocurrency
- ❌ Scanning without explicit permission
- ❌ Any illegal activities

### **Responsible Disclosure**
If you discover significant vulnerabilities:
1. Report to relevant Bitcoin development teams
2. Follow responsible disclosure practices
3. Do not exploit for personal gain

## 🐛 **Troubleshooting**

### **Common Issues**

#### Frontend Won't Start
```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
yarn install
```

#### Backend API Errors
```bash
# Check if MongoDB is running
mongosh --eval "db.adminCommand('ismaster')"

# Verify Python dependencies
pip install -r requirements.txt
```

#### CORS Errors
Ensure backend `.env` has:
```
CORS_ORIGINS="*"
```

#### Configuration Issues
Check that frontend `.env` points to local backend:
```
REACT_APP_BACKEND_URL=http://localhost:8001
```

## 📊 **Performance**

### **Scanning Performance**
- **Small Range** (1-100 blocks): ~30 seconds
- **Medium Range** (1-1000 blocks): ~5 minutes
- **Large Range** (1-10000 blocks): ~30+ minutes

### **API Rate Limits**
- Blockstream API: 10 requests/second
- Mempool.space API: 10 requests/second
- Built-in delays prevent rate limiting

## 🤝 **Contributing**

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### **Development Guidelines**
- Follow PEP 8 for Python code
- Use ESLint/Prettier for JavaScript
- Add tests for new features
- Update documentation

## 📜 **License**

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 **Acknowledgments**

- **Bitcoin Core Team** - For the reference implementation
- **Blockstream** - For providing public APIs
- **mempool.space** - For blockchain data access
- **FastAPI Team** - For the excellent web framework
- **React Team** - For the frontend framework

## 📞 **Support**

- **Issues**: [GitHub Issues](https://github.com/your-repo/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-repo/discussions)
- **Email**: support@your-domain.com

## 🚨 **Disclaimer**

This software is provided "as is" without warranty of any kind. The authors are not responsible for any misuse or damage caused by this software. Always comply with applicable laws and regulations.

---

<div align="center">
  <strong>⚡ Built with modern web technologies for Bitcoin security research ⚡</strong>
</div>