# Environment Configuration Guide

## 🚨 IMPORTANT: Frontend Backend URL Configuration

### ✅ Correct Setup (LOCAL DEVELOPMENT)
```bash
# /app/frontend/.env
REACT_APP_BACKEND_URL=http://localhost:8001
WDS_SOCKET_PORT=443
```

### ❌ WRONG Setup (Bug that was fixed)
```bash
# This would cause local frontend to hit remote backend - DO NOT USE
REACT_APP_BACKEND_URL=https://ecdsa-vulncheck.preview.emergentagent.com
```

## Development Environment Setup

### Backend Configuration
- Backend runs on: `http://localhost:8001`
- MongoDB runs on: `mongodb://localhost:27017`
- Database name: `test_database`

### Frontend Configuration  
- Frontend runs on: `http://localhost:3000`
- Backend API calls go to: `http://localhost:8001/api/*`

## Verification Steps

1. **Check Frontend .env file**:
   ```bash
   cat /app/frontend/.env
   # Should show: REACT_APP_BACKEND_URL=http://localhost:8001
   ```

2. **Test Backend Locally**:
   ```bash
   curl http://localhost:8001/api/current-height
   # Should return: {"height": [current_block_number]}
   ```

3. **Verify Frontend Calls Local Backend**:
   - Check backend logs: `tail -f /var/log/supervisor/backend.out.log`
   - Access frontend: `http://localhost:3000`
   - Should see `127.0.0.1` requests in backend logs

## Common Issues

### Issue: Frontend calls remote backend instead of local
**Symptom**: No logs in local backend when using frontend
**Fix**: Update `REACT_APP_BACKEND_URL` in `/app/frontend/.env` to `http://localhost:8001`

### Issue: CORS errors
**Symptom**: Browser console shows CORS errors
**Fix**: Ensure backend CORS_ORIGINS includes `*` or frontend URL

## Production Deployment
For production deployment, update frontend .env to point to production backend URL:
```bash
REACT_APP_BACKEND_URL=https://your-production-backend.com
```