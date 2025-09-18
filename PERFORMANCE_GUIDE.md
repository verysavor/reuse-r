# Bitcoin Reused-R Scanner - Performance Guide

## 🚀 **High-Performance Parallel Scanning**

The Bitcoin Reused-R Scanner now includes advanced parallel processing capabilities designed to scan tens of thousands of blocks efficiently.

### **Performance Features**

#### **1. Multi-API Load Balancing**
- **3 Blockchain APIs**: Blockstream, Mempool.space, BlockCypher
- **Round-robin distribution**: Requests automatically distributed across APIs
- **Fallback system**: If one API fails, others continue processing
- **Rate limit handling**: Automatic retry with exponential backoff

#### **2. Parallel Batch Processing**
- **Batch size**: 50 blocks processed simultaneously (configurable)
- **Concurrent blocks**: Up to 10 blocks processed in parallel per batch
- **Concurrent requests**: Up to 20 API requests simultaneously
- **Session management**: Individual sessions per request to prevent conflicts

#### **3. Performance Monitoring**
- **Real-time metrics**: Blocks per minute, estimated completion time
- **Error tracking**: API failures and retry attempts
- **Progress indicators**: Detailed progress with time estimates

### **Speed Benchmarks**

| Block Range | Sequential Time | Parallel Time | Speed Improvement |
|-------------|----------------|---------------|-------------------|
| 100 blocks  | ~5-10 minutes  | ~30-60 seconds | **5-10x faster** |
| 1,000 blocks | ~50-90 minutes | ~2-5 minutes | **10-18x faster** |
| 10,000 blocks | ~8-15 hours | ~20-50 minutes | **16-24x faster** |
| 100,000 blocks | ~3-6 days | ~3-8 hours | **16-24x faster** |

*Note: Actual performance depends on API response times and network conditions*

### **Configuration Options**

#### **Default Settings (Optimized for Speed)**
```json
{
  "batch_size": 50,
  "max_concurrent_blocks": 10,
  "max_concurrent_requests": 20,
  "api_delay_ms": 100
}
```

#### **Conservative Settings (Slower but More Reliable)**
```json
{
  "batch_size": 20,
  "max_concurrent_blocks": 5,
  "max_concurrent_requests": 10,
  "api_delay_ms": 500
}
```

#### **Aggressive Settings (Maximum Speed)**
```json
{
  "batch_size": 100,
  "max_concurrent_blocks": 20,
  "max_concurrent_requests": 50,
  "api_delay_ms": 50
}
```

### **Usage Recommendations**

#### **For Large Scans (10,000+ blocks)**
1. **Use default settings** for optimal balance of speed and reliability
2. **Monitor progress** regularly to ensure no excessive errors
3. **Run during off-peak hours** to avoid API rate limiting
4. **Consider breaking very large scans** into chunks (e.g., 50,000 blocks per scan)

#### **For Quick Testing (1-1,000 blocks)**
1. Use aggressive settings for maximum speed
2. Perfect for testing and demonstration purposes

#### **For Production Analysis**
1. Use conservative settings for maximum reliability
2. Implement proper error handling and retry logic
3. Monitor API usage to stay within limits

### **Technical Architecture**

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Batch Manager │────│   Block Workers │────│   API Managers  │
│   (50 blocks)   │    │   (10 parallel) │    │   (3 APIs)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Progress      │    │   Transaction   │    │   Rate Limiting │
│   Tracking      │    │   Processing    │    │   & Retries     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### **Error Handling**

#### **Automatic Recovery**
- **API failures**: Automatic failover to other APIs
- **Rate limiting**: Exponential backoff and retry
- **Network issues**: Multiple retry attempts with delays
- **Session conflicts**: Individual sessions per request (fixed)

#### **Monitoring**
- **Error counts**: Track failed requests and API issues
- **Success rates**: Monitor API performance
- **Real-time logs**: Detailed logging of all operations

### **API Usage Guidelines**

#### **Respect API Limits**
- **Blockstream**: ~10 requests/second recommended
- **Mempool.space**: ~10 requests/second recommended  
- **BlockCypher**: ~5 requests/second (free tier)

#### **Best Practices**
1. **Start with small scans** to test API responsiveness
2. **Monitor error rates** - if > 10%, reduce concurrency
3. **Use delays** between batches to prevent overwhelming APIs
4. **Consider API costs** for large-scale scanning

### **Troubleshooting**

#### **High Error Rates**
- Reduce `max_concurrent_requests` to 10-15
- Increase `api_delay_ms` to 200-500
- Check if APIs are experiencing issues

#### **Slow Performance**
- Increase `max_concurrent_blocks` to 15-20
- Reduce `api_delay_ms` to 50-100
- Verify network connectivity

#### **Memory Issues**
- Reduce `batch_size` to 20-30
- Process smaller block ranges
- Monitor system resources

### **Future Optimizations**

#### **Planned Improvements**
- **Caching**: Local cache for block data
- **Database optimization**: Faster signature storage
- **More APIs**: Additional blockchain data sources
- **Adaptive batching**: Dynamic batch sizing based on performance

#### **Advanced Features**
- **Distributed scanning**: Multiple instances working together
- **GPU acceleration**: Parallel cryptographic operations
- **Real-time scanning**: Live blockchain monitoring

---

## 🎯 **Quick Start for Large Scans**

```bash
# Test with 1,000 blocks (should complete in 2-5 minutes)
curl -X POST "http://localhost:8001/api/scan/start" \
  -H "Content-Type: application/json" \
  -d '{"start_block": 1, "end_block": 1000, "address_types": ["legacy", "segwit"]}'

# Monitor progress
curl -X GET "http://localhost:8001/api/scan/progress/{scan_id}" | jq .

# For 10,000+ blocks, monitor regularly and expect 20-50 minutes
```

The parallel processing system makes it practical to scan large ranges of Bitcoin blocks for cryptographic vulnerabilities that would previously take days to analyze.