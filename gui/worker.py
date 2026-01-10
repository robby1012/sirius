"""Worker thread for running performance tests without blocking the UI"""

import asyncio
import json
import ssl
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse

import aiohttp
from PyQt6.QtCore import QThread, pyqtSignal


class TestWorker(QThread):
    """Worker thread to run performance test without blocking UI"""
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    progress = pyqtSignal(int)
    log = pyqtSignal(str)

    def __init__(self, url: str, method: str, body: Optional[bytes], headers: Dict[str, str],
                 total: int, concurrency: int, timeout: float, formdata: Optional[dict] = None):
        super().__init__()
        self.url = url
        self.method = method
        self.body = body
        self.headers = headers
        self.total = total
        self.concurrency = concurrency
        self.timeout = timeout
        self.formdata = formdata

    def run(self):
        """Run the performance test"""
        try:
            # Calculate and add Content-Length if body is present
            if self.body and 'Content-Length' not in self.headers:
                content_length = len(self.body)
                self.headers['Content-Length'] = str(content_length)
            
            # Add common browser headers if not present
            parsed_url = urlparse(self.url)
            if 'Host' not in self.headers:
                self.headers['Host'] = parsed_url.netloc
            if 'Connection' not in self.headers:
                self.headers['Connection'] = 'keep-alive'
            if 'Accept-Encoding' not in self.headers:
                self.headers['Accept-Encoding'] = 'gzip, deflate, br'
            if 'Accept-Language' not in self.headers:
                self.headers['Accept-Language'] = 'en-US,en;q=0.9'
            
            self.log.emit(f"=== Starting Performance Test ===")
            self.log.emit(f"URL: {self.url}")
            self.log.emit(f"Method: {self.method}")
            self.log.emit(f"Total Requests: {self.total}")
            self.log.emit(f"Concurrency: {self.concurrency}")
            self.log.emit(f"Timeout: {self.timeout}s")
            if self.body:
                self.log.emit(f"Body Size: {len(self.body)} bytes")
            if self.headers:
                self.log.emit(f"Headers: {json.dumps(self.headers, indent=2)}")
            if self.formdata:
                self.log.emit(f"Form Data: {len(self.formdata)} fields")
            self.log.emit("SSL verification: disabled")
            self.log.emit("")
            
            # Create new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                self.log.emit("Starting async test execution...")
                result = loop.run_until_complete(
                    self.run_test_with_formdata() if self.formdata else
                    self.run_test_with_logging()
                )
                self.log.emit(f"Test completed. Total time: {result['total_time']:.2f}s")
                self.log.emit(f"Total requests: {len(result['results'])}")
                successes = sum(1 for r in result['results'] if r.get('ok'))
                self.log.emit(f"Successful: {successes}, Failed: {len(result['results']) - successes}")
                # Log any errors found in results
                errors = [r for r in result['results'] if not r.get('ok')]
                if errors:
                    self.log.emit("")
                    self.log.emit("First few errors:")
                    for err in errors[:5]:  # Show first 5 errors
                        if err.get('error'):
                            self.log.emit(f"  Request {err.get('index')}: {err.get('error')}")
                        elif err.get('status'):
                            self.log.emit(f"  Request {err.get('index')}: HTTP {err.get('status')}")
                self.finished.emit(result)
            finally:
                loop.close()
        except Exception as e:
            self.log.emit(f"ERROR: {str(e)}")
            self.error.emit(str(e))
    
    async def run_test_with_logging(self) -> Dict[str, Any]:
        """Run test with error logging for non-formdata requests"""
        import time
        
        # Create SSL context that doesn't verify certificates
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        results: List[Dict[str, Any]] = []
        sem = asyncio.Semaphore(self.concurrency)
        timeout_cfg = aiohttp.ClientTimeout(total=self.timeout)
        connector = aiohttp.TCPConnector(limit=0, ssl=ssl_context)

        async with aiohttp.ClientSession(timeout=timeout_cfg, connector=connector) as session:
            start_all = time.perf_counter()

            async def do_request(i: int) -> None:
                nonlocal results
                async with sem:
                    req_start_perf = time.perf_counter()
                    req_start_epoch = time.time()
                    try:
                        async with session.request(self.method, self.url, data=self.body, headers=self.headers) as resp:
                            payload = await resp.read()
                            elapsed = time.perf_counter() - req_start_perf
                            is_ok = 200 <= resp.status < 400
                            results.append({
                                'index': i,
                                'status': resp.status,
                                'time': elapsed,
                                'ok': is_ok,
                                'bytes': len(payload),
                                'start_epoch': req_start_epoch,
                                'start_rel_s': req_start_perf - start_all,
                            })
                            # Log error responses
                            if not is_ok:
                                try:
                                    error_body = payload.decode('utf-8')[:200]  # First 200 chars
                                    self.log.emit(f"Request {i} failed: {self.method} {self.url} -> HTTP {resp.status}")
                                    self.log.emit(f"  Server response: {error_body}")
                                except:
                                    self.log.emit(f"Request {i} failed: {self.method} {self.url} -> HTTP {resp.status}")
                    except Exception as e:
                        elapsed = time.perf_counter() - req_start_perf
                        error_msg = str(e)
                        self.log.emit(f"Request {i} error: {self.method} {self.url}")
                        self.log.emit(f"  Exception: {error_msg}")
                        results.append({
                            'index': i, 'status': None, 'time': None, 'ok': False, 
                            'error': error_msg, 'start_epoch': req_start_epoch, 
                            'start_rel_s': req_start_perf - start_all
                        })

            tasks = [asyncio.create_task(do_request(i)) for i in range(self.total)]
            await asyncio.gather(*tasks)
            total_time = time.perf_counter() - start_all

        return {
            'results': results,
            'total_time': total_time,
        }
    
    async def run_test_with_formdata(self) -> Dict[str, Any]:
        """Run test with multipart form data"""
        import time
        
        self.log.emit("Using multipart/form-data encoding...")
        
        # Create SSL context that doesn't verify certificates
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        results: List[Dict[str, Any]] = []
        sem = asyncio.Semaphore(self.concurrency)
        timeout_cfg = aiohttp.ClientTimeout(total=self.timeout)
        connector = aiohttp.TCPConnector(limit=0, ssl=ssl_context)

        async with aiohttp.ClientSession(timeout=timeout_cfg, connector=connector) as session:
            start_all = time.perf_counter()

            async def do_request(i: int) -> None:
                nonlocal results
                async with sem:
                    req_start_perf = time.perf_counter()
                    req_start_epoch = time.time()
                    try:
                        # Build FormData
                        data = aiohttp.FormData()
                        for key, value in self.formdata.items():
                            if isinstance(value, dict) and 'file' in value:
                                # File upload
                                data.add_field(key, value['file'], filename=value.get('filename', 'file'))
                            else:
                                data.add_field(key, value)
                        
                        async with session.request(self.method, self.url, data=data, headers=self.headers) as resp:
                            payload = await resp.read()
                            elapsed = time.perf_counter() - req_start_perf
                            is_ok = 200 <= resp.status < 400
                            results.append({
                                'index': i,
                                'status': resp.status,
                                'time': elapsed,
                                'ok': is_ok,
                                'bytes': len(payload),
                                'start_epoch': req_start_epoch,
                                'start_rel_s': req_start_perf - start_all,
                            })
                            # Log error responses
                            if not is_ok:
                                try:
                                    error_body = payload.decode('utf-8')[:200]  # First 200 chars
                                    self.log.emit(f"Request {i} failed: {self.method} {self.url} -> HTTP {resp.status}")
                                    self.log.emit(f"  Server response: {error_body}")
                                except:
                                    self.log.emit(f"Request {i} failed: {self.method} {self.url} -> HTTP {resp.status}")
                    except Exception as e:
                        elapsed = time.perf_counter() - req_start_perf
                        error_msg = str(e)
                        self.log.emit(f"Request {i} error (formdata): {self.method} {self.url}")
                        self.log.emit(f"  Exception: {error_msg}")
                        results.append({
                            'index': i, 'status': None, 'time': None, 'ok': False, 
                            'error': error_msg, 'start_epoch': req_start_epoch, 
                            'start_rel_s': req_start_perf - start_all
                        })

            tasks = [asyncio.create_task(do_request(i)) for i in range(self.total)]
            await asyncio.gather(*tasks)
            total_time = time.perf_counter() - start_all

        return {
            'results': results,
            'total_time': total_time,
        }
