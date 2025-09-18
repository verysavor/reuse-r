#!/usr/bin/env python3

import asyncio
import aiohttp
import json

async def test_blockchain_info_api():
    """Test blockchain.info API for block 252474"""
    
    # Get block hash
    block_height = 252474
    url1 = f"https://blockchain.info/block-height/{block_height}?format=json"
    
    print(f"Testing: {url1}")
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url1) as resp:
            print(f"Status: {resp.status}")
            if resp.status == 200:
                result = await resp.json()
                block_hash = result['blocks'][0]['hash']
                print(f"Block hash: {block_hash}")
                
                # Get block transactions
                url2 = f"https://blockchain.info/rawblock/{block_hash}"
                print(f"\nTesting: {url2}")
                
                async with session.get(url2) as resp2:
                    print(f"Status: {resp2.status}")
                    if resp2.status == 200:
                        block_data = await resp2.json()
                        tx_count = len(block_data.get('tx', []))
                        print(f"Transaction count: {tx_count}")
                        
                        if tx_count > 0:
                            # Test first transaction
                            first_tx = block_data['tx'][0]
                            tx_hash = first_tx['hash']
                            print(f"First tx hash: {tx_hash}")
                            
                            # Get transaction details
                            url3 = f"https://blockchain.info/rawtx/{tx_hash}"
                            print(f"\nTesting: {url3}")
                            
                            async with session.get(url3) as resp3:
                                print(f"Status: {resp3.status}")
                                if resp3.status == 200:
                                    tx_data = await resp3.json()
                                    print(f"Transaction inputs: {len(tx_data.get('inputs', []))}")
                                    print(f"Transaction outputs: {len(tx_data.get('out', []))}")
                                    
                                    # Check for signatures in inputs
                                    sig_count = 0
                                    for inp in tx_data.get('inputs', []):
                                        script = inp.get('script', '')
                                        if script and len(script) > 40:  # Likely has signature
                                            sig_count += 1
                                    print(f"Inputs with signatures: {sig_count}")
                                    
                                    return True
                    else:
                        print(f"Error getting block data: {resp2.status}")
            else:
                print(f"Error getting block hash: {resp.status}")
    
    return False

if __name__ == "__main__":
    asyncio.run(test_blockchain_info_api())