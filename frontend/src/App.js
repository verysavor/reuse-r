import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Button } from './components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './components/ui/card';
import { Input } from './components/ui/input';
import { Label } from './components/ui/label';
import { Badge } from './components/ui/badge';
import { Progress } from './components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './components/ui/tabs';
import { Alert, AlertDescription } from './components/ui/alert';
import { Textarea } from './components/ui/textarea';
import { Checkbox } from './components/ui/checkbox';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from './components/ui/dialog';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from './components/ui/table';
import { ScrollArea } from './components/ui/scroll-area';
import { Separator } from './components/ui/separator';
import { toast } from 'sonner';
import { Toaster } from './components/ui/sonner';
import { 
  Search, 
  Play, 
  Square, 
  Download, 
  AlertTriangle, 
  CheckCircle, 
  Clock, 
  Bitcoin,
  Shield,
  Activity,
  TrendingUp,
  Eye,
  Key,
  Coins,
  RefreshCw
} from 'lucide-react';
import './App.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

function App() {
  const [currentHeight, setCurrentHeight] = useState(0);
  const [scanConfig, setScanConfig] = useState({
    startBlock: 1,
    endBlock: 100,
    addressTypes: ['legacy', 'segwit']
  });
  const [currentScan, setCurrentScan] = useState(null);
  const [scanProgress, setScanProgress] = useState(null);
  const [scanResults, setScanResults] = useState(null);
  const [scanLogs, setScanLogs] = useState([]);
  const [isScanning, setIsScanning] = useState(false);
  const [selectedKeys, setSelectedKeys] = useState([]);
  const [balances, setBalances] = useState({});
  const [showBalanceDialog, setShowBalanceDialog] = useState(false);
  const [performanceConfig, setPerformanceConfig] = useState({
    batch_size: 50,
    max_concurrent_blocks: 10,
    max_concurrent_requests: 20,
    api_delay_ms: 100
  });

  // Fetch current blockchain height on load
  useEffect(() => {
    fetchCurrentHeight();
  }, []);

  // Poll scan progress when scanning
  useEffect(() => {
    console.log('useEffect triggered - currentScan:', currentScan, 'isScanning:', isScanning);
    let interval;
    if (currentScan && isScanning) {
      interval = setInterval(() => {
        fetchScanProgress();
      }, 2000);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [currentScan, isScanning]);

  const fetchCurrentHeight = async () => {
    try {
      const response = await axios.get(`${API}/current-height`);
      setCurrentHeight(response.data.height);
    } catch (error) {
      console.error('Error fetching current height:', error);
      toast.error('Failed to fetch current blockchain height');
    }
  };

  const startScan = async () => {
    try {
      const scanData = {
        start_block: parseInt(scanConfig.startBlock),
        end_block: parseInt(scanConfig.endBlock),
        address_types: scanConfig.addressTypes
      };
      
      console.log('Starting scan with config:', scanData);
      console.log('Current scanConfig state:', scanConfig);
      
      const response = await axios.post(`${API}/scan/start`, scanData);
      
      const scanId = response.data.scan_id;
      console.log('Setting currentScan to:', scanId);
      setCurrentScan(scanId);
      setIsScanning(true);
      setScanResults(null);
      setScanLogs([]);
      toast.success('Scan started successfully!');
    } catch (error) {
      console.error('Error starting scan:', error);
      toast.error('Failed to start scan: ' + (error.response?.data?.detail || error.message));
    }
  };

  const stopScan = async () => {
    if (!currentScan) return;
    
    try {
      await axios.post(`${API}/scan/stop/${currentScan}`);
      setIsScanning(false);
      toast.success('Scan stopped');
    } catch (error) {
      console.error('Error stopping scan:', error);
      toast.error('Failed to stop scan');
    }
  };

  const fetchScanProgress = async () => {
    if (!currentScan) return;
    
    try {
      const response = await axios.get(`${API}/scan/progress/${currentScan}`);
      const progress = response.data;
      
      console.log('Progress update received:', progress);
      
      setScanProgress(progress);
      
      // Update logs
      if (progress.logs && progress.logs.length > 0) {
        setScanLogs(prevLogs => {
          const newLogs = progress.logs.filter(log => 
            !prevLogs.some(existingLog => 
              existingLog.timestamp === log.timestamp && existingLog.message === log.message
            )
          );
          return [...prevLogs, ...newLogs].slice(-100); // Keep last 100 logs
        });
      }
      
      // Check if scan completed
      if (progress.status === 'completed' || progress.status === 'failed' || progress.status === 'stopped') {
        setIsScanning(false);
        if (progress.status === 'completed') {
          fetchScanResults();
          toast.success('Scan completed successfully!');
        } else if (progress.status === 'failed') {
          toast.error('Scan failed');
        }
      }
    } catch (error) {
      console.error('Error fetching scan progress:', error);
    }
  };

  const fetchScanResults = async (scanId = null) => {
    const targetScanId = scanId || currentScan;
    
    if (!targetScanId) {
      console.log('No scan ID available for fetchScanResults');
      // Try to get the latest scan from the list
      try {
        const listResponse = await axios.get(`${API}/scan/list`);
        const scans = listResponse.data.scans;
        if (scans && scans.length > 0) {
          const latestScan = scans[scans.length - 1];
          console.log('Using latest scan from list:', latestScan.scan_id);
          const response = await axios.get(`${API}/scan/results/${latestScan.scan_id}`);
          setScanResults(response.data);
          setCurrentScan(latestScan.scan_id); // Update the current scan state
          return;
        }
      } catch (listError) {
        console.error('Could not fetch scan list:', listError);
      }
      return;
    }
    
    try {
      console.log('Fetching scan results for:', targetScanId);
      const response = await axios.get(`${API}/scan/results/${targetScanId}`);
      console.log('Scan results received:', response.data);
      setScanResults(response.data);
    } catch (error) {
      console.error('Error fetching scan results:', error);
      toast.error('Failed to fetch scan results');
    }
  };

  const checkBalances = async () => {
    if (!scanResults || !scanResults.recovered_keys) return;
    
    setShowBalanceDialog(true);
    
    try {
      const addresses = [];
      scanResults.recovered_keys.forEach(key => {
        if (key.compressed_address) addresses.push(key.compressed_address);
        if (key.uncompressed_address) addresses.push(key.uncompressed_address);
      });
      
      const response = await axios.post(`${API}/balance/check`, addresses);
      const balanceMap = {};
      response.data.balances.forEach(balance => {
        balanceMap[balance.address] = balance;
      });
      setBalances(balanceMap);
      toast.success('Balance check completed');
    } catch (error) {
      console.error('Error checking balances:', error);
      toast.error('Failed to check balances');
    }
  };

  const exportResults = async () => {
    if (!currentScan) return;
    
    try {
      const response = await axios.get(`${API}/scan/export/${currentScan}`, {
        responseType: 'blob'
      });
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `reused_r_scan_${currentScan}.json`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      
      toast.success('Results exported successfully');
    } catch (error) {
      console.error('Error exporting results:', error);
      toast.error('Failed to export results');
    }
  };

  const handleAddressTypeChange = (type, checked) => {
    setScanConfig(prev => ({
      ...prev,
      addressTypes: checked 
        ? [...prev.addressTypes, type]
        : prev.addressTypes.filter(t => t !== type)
    }));
  };

  const formatPrivateKey = (key) => {
    return `${key.substring(0, 8)}...${key.substring(key.length - 8)}`;
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'running': return 'bg-blue-500';
      case 'completed': return 'bg-green-500';
      case 'failed': return 'bg-red-500';
      case 'stopped': return 'bg-yellow-500';
      default: return 'bg-gray-500';
    }
  };

  const getLogIcon = (level) => {
    switch (level) {
      case 'success': return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'warning': return <AlertTriangle className="h-4 w-4 text-yellow-500" />;
      case 'error': return <AlertTriangle className="h-4 w-4 text-red-500" />;
      default: return <Clock className="h-4 w-4 text-blue-500" />;
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      <div className="container mx-auto p-6 space-y-6">
        {/* Header */}
        <div className="text-center space-y-4">
          <div className="flex items-center justify-center space-x-3">
            <div className="p-3 bg-orange-500/20 rounded-full">
              <Bitcoin className="h-8 w-8 text-orange-400" />
            </div>
            <h1 className="text-4xl font-bold text-white">Bitcoin Reused-R Scanner</h1>
            <div className="p-3 bg-red-500/20 rounded-full">
              <Shield className="h-8 w-8 text-red-400" />
            </div>
          </div>
          <p className="text-slate-400 max-w-2xl mx-auto">
            Advanced cryptographic analysis tool for detecting ECDSA nonce reuse vulnerabilities 
            in Bitcoin transactions. Scan blockchain data to identify and recover private keys 
            from weak signatures.
          </p>
          <div className="flex items-center justify-center space-x-4 text-sm text-slate-500">
            <div className="flex items-center space-x-1">
              <Activity className="h-4 w-4" />
              <span>Current Height: {currentHeight.toLocaleString()}</span>
            </div>
            <Separator orientation="vertical" className="h-4" />
            <div className="flex items-center space-x-1">
              <TrendingUp className="h-4 w-4" />
              <span>Live Blockchain Data</span>
            </div>
          </div>
        </div>

        <Tabs defaultValue="scanner" className="space-y-6">
          <TabsList className="grid w-full grid-cols-4 bg-slate-800/50">
            <TabsTrigger value="scanner" className="data-[state=active]:bg-slate-700">
              <Search className="h-4 w-4 mr-2" />
              Scanner
            </TabsTrigger>
            <TabsTrigger value="results" className="data-[state=active]:bg-slate-700">
              <Key className="h-4 w-4 mr-2" />
              Results
            </TabsTrigger>
            <TabsTrigger value="logs" className="data-[state=active]:bg-slate-700">
              <Activity className="h-4 w-4 mr-2" />
              Logs
            </TabsTrigger>
            <TabsTrigger value="performance" className="data-[state=active]:bg-slate-700">
              <TrendingUp className="h-4 w-4 mr-2" />
              Performance
            </TabsTrigger>
          </TabsList>

          {/* Scanner Tab */}
          <TabsContent value="scanner" className="space-y-6">
            <Card className="bg-slate-800/50 border-slate-700">
              <CardHeader>
                <CardTitle className="text-white flex items-center space-x-2">
                  <Search className="h-5 w-5" />
                  <span>Scan Configuration</span>
                </CardTitle>
                <CardDescription className="text-slate-400">
                  Configure your reused-R vulnerability scan parameters
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* Block Range */}
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="startBlock" className="text-slate-300">Start Block</Label>
                    <Input
                      id="startBlock"
                      type="number"
                      value={scanConfig.startBlock}
                      onChange={(e) => {
                        console.log('Start block changed to:', e.target.value);
                        setScanConfig(prev => ({...prev, startBlock: e.target.value}));
                      }}
                      className="bg-slate-700 border-slate-600 text-white"
                      disabled={isScanning}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="endBlock" className="text-slate-300">End Block</Label>
                    <Input
                      id="endBlock"
                      type="number"
                      value={scanConfig.endBlock}
                      onChange={(e) => {
                        console.log('End block changed to:', e.target.value);
                        setScanConfig(prev => ({...prev, endBlock: e.target.value}));
                      }}
                      className="bg-slate-700 border-slate-600 text-white"
                      disabled={isScanning}
                    />
                  </div>
                </div>

                {/* Address Types */}
                <div className="space-y-3">
                  <Label className="text-slate-300">Address Types to Scan</Label>
                  <div className="flex flex-wrap gap-4">
                    <div className="flex items-center space-x-2">
                      <Checkbox
                        id="legacy"
                        checked={scanConfig.addressTypes.includes('legacy')}
                        onCheckedChange={(checked) => handleAddressTypeChange('legacy', checked)}
                        disabled={isScanning}
                      />
                      <Label htmlFor="legacy" className="text-slate-300">Legacy (P2PKH)</Label>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Checkbox
                        id="segwit"
                        checked={scanConfig.addressTypes.includes('segwit')}
                        onCheckedChange={(checked) => handleAddressTypeChange('segwit', checked)}
                        disabled={isScanning}
                      />
                      <Label htmlFor="segwit" className="text-slate-300">SegWit (P2WPKH)</Label>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Checkbox
                        id="taproot"
                        checked={scanConfig.addressTypes.includes('taproot')}
                        onCheckedChange={(checked) => handleAddressTypeChange('taproot', checked)}
                        disabled={isScanning}
                      />
                      <Label htmlFor="taproot" className="text-slate-300">Taproot (P2TR)</Label>
                    </div>
                  </div>
                </div>

                {/* Scan Controls */}
                <div className="flex space-x-4">
                  <Button
                    onClick={startScan}
                    disabled={isScanning || scanConfig.addressTypes.length === 0}
                    className="bg-blue-600 hover:bg-blue-700"
                  >
                    <Play className="h-4 w-4 mr-2" />
                    Start Scan
                  </Button>
                  
                  {isScanning && (
                    <Button
                      onClick={stopScan}
                      variant="destructive"
                    >
                      <Square className="h-4 w-4 mr-2" />
                      Stop Scan
                    </Button>
                  )}
                </div>

                {/* Scan Status */}
                {scanProgress && (
                  <div className="space-y-4 p-4 bg-slate-700/30 rounded-lg">
                    <div className="flex items-center justify-between">
                      <h3 className="text-lg font-semibold text-white">Scan Progress</h3>
                      <Badge className={getStatusColor(scanProgress.status)}>
                        {scanProgress.status}
                      </Badge>
                    </div>
                    
                    <Progress 
                      value={scanProgress.progress_percentage} 
                      className="w-full"
                    />
                    
                    <div className="grid grid-cols-2 md:grid-cols-5 gap-4 text-sm">
                      <div className="text-center">
                        <div className="text-2xl font-bold text-blue-400">
                          {scanProgress.blocks_scanned}
                        </div>
                        <div className="text-slate-400">Blocks Scanned</div>
                      </div>
                      <div className="text-center">
                        <div className="text-2xl font-bold text-green-400">
                          {scanProgress.signatures_found}
                        </div>
                        <div className="text-slate-400">Signatures Found</div>
                      </div>
                      <div className="text-center">
                        <div className="text-2xl font-bold text-yellow-400">
                          {scanProgress.r_reuse_pairs}
                        </div>
                        <div className="text-slate-400">R Reuse Pairs</div>
                      </div>
                      <div className="text-center">
                        <div className="text-2xl font-bold text-red-400">
                          {scanProgress.keys_recovered}
                        </div>
                        <div className="text-slate-400">Keys Recovered</div>
                      </div>
                      <div className="text-center">
                        <div className="text-2xl font-bold text-purple-400">
                          {scanProgress.blocks_per_minute?.toFixed(1) || '0.0'}
                        </div>
                        <div className="text-slate-400">Blocks/Min</div>
                      </div>
                    </div>
                    
                    {scanProgress.estimated_time_remaining && scanProgress.estimated_time_remaining !== 'unknown' && (
                      <div className="text-center text-slate-300">
                        <span className="text-sm">Estimated time remaining: </span>
                        <span className="font-semibold text-cyan-400">{scanProgress.estimated_time_remaining}</span>
                      </div>
                    )}
                    
                    <div className="grid grid-cols-2 gap-4 text-xs text-slate-500">
                      <div>API Calls: {scanProgress.api_calls_made || 0}</div>
                      <div>Errors: {scanProgress.errors_encountered || 0}</div>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Results Tab */}
          <TabsContent value="results" className="space-y-6">
            <Card className="bg-slate-800/50 border-slate-700">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="text-white flex items-center space-x-2">
                      <Key className="h-5 w-5" />
                      <span>Recovered Private Keys</span>
                    </CardTitle>
                    <CardDescription className="text-slate-400">
                      Private keys recovered from reused R value vulnerabilities
                    </CardDescription>
                  </div>
                  <div className="flex space-x-2">
                    <Button
                      onClick={() => fetchScanResults()}
                      variant="outline"
                      size="sm"
                      className="border-slate-600 text-slate-300 hover:bg-slate-700"
                    >
                      <RefreshCw className="h-4 w-4 mr-2" />
                      Refresh Results
                    </Button>
                    <Button
                      onClick={checkBalances}
                      variant="outline"
                      size="sm"
                      disabled={!scanResults || scanResults.total_keys === 0}
                      className="border-slate-600 text-slate-300 hover:bg-slate-700"
                    >
                      <Coins className="h-4 w-4 mr-2" />
                      Check Balances
                    </Button>
                    <Button
                      onClick={exportResults}
                      variant="outline"
                      size="sm"
                      disabled={!scanResults || scanResults.total_keys === 0}
                      className="border-slate-600 text-slate-300 hover:bg-slate-700"
                    >
                      <Download className="h-4 w-4 mr-2" />
                      Export
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                {scanResults && scanResults.recovered_keys && scanResults.recovered_keys.length > 0 ? (
                  <div className="space-y-4">
                    <div className="text-sm text-slate-400">
                      Found {scanResults.total_keys} vulnerable private keys from {scanResults.r_reuse_pairs} reused R values
                    </div>
                    
                    <ScrollArea className="h-96">
                      <div className="space-y-3">
                        {scanResults.recovered_keys.map((key, index) => (
                          <Card key={index} className="bg-slate-700/30 border-slate-600">
                            <CardContent className="p-4">
                              <div className="grid gap-3">
                                <div className="flex items-center justify-between">
                                  <Badge variant="outline" className="text-xs">
                                    Key #{index + 1}
                                  </Badge>
                                  <Badge 
                                    className={
                                      key.validation_status === 'valid' ? 'bg-green-500' :
                                      key.validation_status === 'invalid' ? 'bg-red-500' : 'bg-yellow-500'
                                    }
                                  >
                                    {key.validation_status}
                                  </Badge>
                                </div>
                                
                                <div className="space-y-2 text-sm">
                                  <div>
                                    <span className="text-slate-400">Private Key:</span>
                                    <code className="ml-2 text-orange-400 font-mono">
                                      {formatPrivateKey(key.private_key)}
                                    </code>
                                  </div>
                                  
                                  {key.compressed_address && (
                                    <div>
                                      <span className="text-slate-400">Compressed Address:</span>
                                      <code className="ml-2 text-green-400 font-mono">
                                        {key.compressed_address}
                                      </code>
                                    </div>
                                  )}
                                  
                                  <div className="grid grid-cols-2 gap-4 text-xs text-slate-500">
                                    <div>
                                      <span>TX1:</span> {key.tx1_hash.substring(0, 8)}...
                                    </div>
                                    <div>
                                      <span>TX2:</span> {key.tx2_hash.substring(0, 8)}...
                                    </div>
                                  </div>
                                </div>
                              </div>
                            </CardContent>
                          </Card>
                        ))}
                      </div>
                    </ScrollArea>
                  </div>
                ) : scanResults?.status === 'completed' ? (
                  <Alert className="bg-slate-700/30 border-slate-600">
                    <CheckCircle className="h-4 w-4" />
                    <AlertDescription className="text-slate-300">
                      Scan completed successfully, but no reused R values were found in the specified block range.
                      Try scanning a different range or expanding the search parameters.
                    </AlertDescription>
                  </Alert>
                ) : (
                  <Alert className="bg-slate-700/30 border-slate-600">
                    <Eye className="h-4 w-4" />
                    <AlertDescription className="text-slate-300">
                      No scan results available. Start a scan to see recovered private keys here.
                    </AlertDescription>
                  </Alert>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Logs Tab */}
          <TabsContent value="logs" className="space-y-6">
            <Card className="bg-slate-800/50 border-slate-700">
              <CardHeader>
                <CardTitle className="text-white flex items-center space-x-2">
                  <Activity className="h-5 w-5" />
                  <span>Scan Logs</span>
                </CardTitle>
                <CardDescription className="text-slate-400">
                  Real-time scanning progress and detailed logs
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ScrollArea className="h-96">
                  {scanLogs.length > 0 ? (
                    <div className="space-y-2">
                      {scanLogs.map((log, index) => (
                        <div key={index} className="flex items-start space-x-3 text-sm p-2 rounded bg-slate-700/20">
                          {getLogIcon(log.level)}
                          <div className="flex-1">
                            <div className="flex items-center space-x-2">
                              <span className="text-slate-400 text-xs">
                                {new Date(log.timestamp).toLocaleTimeString()}
                              </span>
                              <Badge variant="outline" className="text-xs">
                                {log.level}
                              </Badge>
                            </div>
                            <div className="text-slate-200 mt-1">{log.message}</div>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <Alert className="bg-slate-700/30 border-slate-600">
                      <Activity className="h-4 w-4" />
                      <AlertDescription className="text-slate-300">
                        No logs available. Start a scan to see real-time progress logs here.
                      </AlertDescription>
                    </Alert>
                  )}
                </ScrollArea>
              </CardContent>
            </Card>
          </TabsContent>
          {/* Performance Tab */}
          <TabsContent value="performance" className="space-y-6">
            <Card className="bg-slate-800/50 border-slate-700">
              <CardHeader>
                <CardTitle className="text-white flex items-center space-x-2">
                  <TrendingUp className="h-5 w-5" />
                  <span>Performance Configuration</span>
                </CardTitle>
                <CardDescription className="text-slate-400">
                  Optimize scanning speed with parallel processing settings
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <Alert className="bg-blue-900/30 border-blue-700">
                  <AlertTriangle className="h-4 w-4" />
                  <AlertDescription className="text-slate-300">
                    <strong>High-Speed Scanning:</strong> This scanner uses advanced parallel processing with 2 reliable blockchain APIs 
                    (Blockstream & Mempool.space) to scan thousands of blocks efficiently and detect reused R values.
                  </AlertDescription>
                </Alert>
                
                <div className="grid grid-cols-2 gap-6">
                  <div className="space-y-4">
                    <h3 className="text-lg font-semibold text-white">Current Performance</h3>
                    
                    {scanProgress && (
                      <div className="space-y-3">
                        <div className="flex justify-between">
                          <span className="text-slate-400">Speed:</span>
                          <span className="text-green-400 font-mono">
                            {scanProgress.blocks_per_minute?.toFixed(1) || '0.0'} blocks/min
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-400">Time Remaining:</span>
                          <span className="text-cyan-400">
                            {scanProgress.estimated_time_remaining || 'Unknown'}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-400">API Calls:</span>
                          <span className="text-yellow-400">{scanProgress.api_calls_made || 0}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-400">Errors:</span>
                          <span className="text-red-400">{scanProgress.errors_encountered || 0}</span>
                        </div>
                      </div>
                    )}
                    
                    {!scanProgress && (
                      <div className="text-slate-500 text-sm">
                        Performance metrics available during active scans
                      </div>
                    )}
                  </div>
                  
                  <div className="space-y-4">
                    <h3 className="text-lg font-semibold text-white">Speed Estimates</h3>
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span className="text-slate-400">1,000 blocks:</span>
                        <span className="text-green-400">~2-5 minutes</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">10,000 blocks:</span>
                        <span className="text-yellow-400">~20-50 minutes</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">100,000 blocks:</span>
                        <span className="text-orange-400">~3-8 hours</span>
                      </div>
                    </div>
                    
                    <Alert className="bg-green-900/30 border-green-700">
                      <CheckCircle className="h-4 w-4" />
                      <AlertDescription className="text-xs text-slate-300">
                        <strong>Parallel Processing:</strong> Uses 2 reliable blockchain APIs (Blockstream & Mempool.space) 
                        with parallel batch processing for optimal speed and accuracy.
                      </AlertDescription>
                    </Alert>
                  </div>
                </div>
                
                <div className="grid grid-cols-3 gap-4">
                  <Card className="bg-slate-700/30 border-slate-600 p-4">
                    <div className="text-center">
                      <div className="text-2xl font-bold text-blue-400">3</div>
                      <div className="text-xs text-slate-400">Blockchain APIs</div>
                    </div>
                  </Card>
                  <Card className="bg-slate-700/30 border-slate-600 p-4">
                    <div className="text-center">
                      <div className="text-2xl font-bold text-green-400">50</div>
                      <div className="text-xs text-slate-400">Blocks per Batch</div>
                    </div>
                  </Card>
                  <Card className="bg-slate-700/30 border-slate-600 p-4">
                    <div className="text-center">
                      <div className="text-2xl font-bold text-purple-400">50</div>
                      <div className="text-xs text-slate-400">Concurrent Requests</div>
                    </div>
                  </Card>
                </div>
                
                <Alert className="bg-yellow-900/30 border-yellow-700">
                  <AlertTriangle className="h-4 w-4" />
                  <AlertDescription className="text-slate-300">
                    <strong>For Large Scans (10,000+ blocks):</strong> The scanner automatically handles rate limiting 
                    and API rotation to maintain optimal speed without overwhelming blockchain APIs.
                  </AlertDescription>
                </Alert>
              </CardContent>
            </Card>
          </TabsContent>

        </Tabs>

        {/* Balance Check Dialog */}
        <Dialog open={showBalanceDialog} onOpenChange={setShowBalanceDialog}>
          <DialogContent className="max-w-4xl bg-slate-800 border-slate-700">
            <DialogHeader>
              <DialogTitle className="text-white">Address Balance Check</DialogTitle>
              <DialogDescription className="text-slate-400">
                Live balance information for recovered addresses
              </DialogDescription>
            </DialogHeader>
            <ScrollArea className="h-96">
              <Table>
                <TableHeader>
                  <TableRow className="border-slate-700">
                    <TableHead className="text-slate-300">Address</TableHead>
                    <TableHead className="text-slate-300">Balance (BTC)</TableHead>
                    <TableHead className="text-slate-300">Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {Object.entries(balances).map(([address, balance]) => (
                    <TableRow key={address} className="border-slate-700">
                      <TableCell className="font-mono text-sm text-slate-200">
                        {address}
                      </TableCell>
                      <TableCell className="text-slate-200">
                        {balance.balance.toFixed(8)}
                      </TableCell>
                      <TableCell>
                        <Badge className={balance.balance > 0 ? 'bg-green-500' : 'bg-gray-500'}>
                          {balance.balance > 0 ? 'Has Balance' : 'Empty'}
                        </Badge>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              </ScrollArea>
            </DialogContent>
          </Dialog>

        {/* Footer */}
        <div className="text-center text-sm text-slate-500 space-y-2">
          <div className="flex items-center justify-center space-x-4">
            <div className="flex items-center space-x-1">
              <Shield className="h-4 w-4 text-red-400" />
              <span>Security Research Tool</span>
            </div>
            <Separator orientation="vertical" className="h-4" />
            <span>Use Responsibly & Legally</span>
          </div>
          <p>
            This tool demonstrates ECDSA nonce reuse vulnerabilities in Bitcoin transactions.
            Only use on data you own or have explicit permission to analyze.
          </p>
        </div>
      </div>
      <Toaster />
    </div>
  );
}

export default App;