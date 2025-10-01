"""
Comprehensive Test Suite for RAG Agent Workflow API
Tests all endpoints and functionality including streaming
"""

import requests
import json
import time
from typing import Dict, Any
from urllib.parse import urlencode

# Configuration
BASE_URL = "http://localhost:8000"
TEST_QUERIES = [
    "What information do you have?",
    "Tell me about the documents in your knowledge base",
    "Can you help me with something?",
]

# ANSI color codes for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header(text: str):
    """Print formatted header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text.center(60)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}\n")

def print_test(test_name: str):
    """Print test name"""
    print(f"{Colors.BOLD}Testing: {test_name}{Colors.END}")

def print_success(message: str):
    """Print success message"""
    print(f"{Colors.GREEN}✓ {message}{Colors.END}")

def print_error(message: str):
    """Print error message"""
    print(f"{Colors.RED}✗ {message}{Colors.END}")

def print_warning(message: str):
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠ {message}{Colors.END}")

def print_info(message: str):
    """Print info message"""
    print(f"  {message}")

def print_json(data: Dict[Any, Any], indent: int = 2):
    """Print JSON data in a formatted way"""
    print(f"{Colors.YELLOW}{json.dumps(data, indent=indent)}{Colors.END}")

# Test Functions

def test_root_endpoint():
    """Test the root endpoint"""
    print_test("Root Endpoint (GET /)")
    
    try:
        response = requests.get(f"{BASE_URL}/")
        
        if response.status_code == 200:
            data = response.json()
            print_success(f"Status Code: {response.status_code}")
            print_info(f"Service: {data.get('service')}")
            print_info(f"Version: {data.get('version')}")
            print_info(f"Agent Ready: {data.get('agent_ready')}")
            
            if data.get('agent_ready'):
                print_success("Agent is ready to accept requests")
            else:
                print_error("Agent is not ready - check configuration")
            
            return True
        else:
            print_error(f"Unexpected status code: {response.status_code}")
            return False
            
    except Exception as e:
        print_error(f"Request failed: {e}")
        return False

def test_health_endpoint():
    """Test the health check endpoint"""
    print_test("Health Check Endpoint (GET /health)")
    
    try:
        response = requests.get(f"{BASE_URL}/health")
        
        if response.status_code == 200:
            data = response.json()
            print_success(f"Status Code: {response.status_code}")
            print_info(f"Status: {data.get('status')}")
            print_info(f"Timestamp: {data.get('timestamp')}")
            print_info(f"ChromaDB Path: {data.get('chroma_db_path')}")
            print_info(f"Collection: {data.get('collection_name')}")
            print_info(f"Model: {data.get('model')}")
            return True
        else:
            print_error(f"Health check failed with status: {response.status_code}")
            if response.status_code == 503:
                print_error("Service unavailable - check if RAG Agent is initialized")
            return False
            
    except Exception as e:
        print_error(f"Request failed: {e}")
        return False

def test_query_endpoint(query: str, user_id: str = "test_user"):
    """Test the query endpoint"""
    print_test(f"Query Endpoint (POST /query)")
    print_info(f"Query: '{query}'")
    
    try:
        payload = {
            "query": query,
            "user_id": user_id
        }
        
        start_time = time.time()
        response = requests.post(
            f"{BASE_URL}/query",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        elapsed_time = (time.time() - start_time) * 1000
        
        if response.status_code == 200:
            data = response.json()
            print_success(f"Status Code: {response.status_code}")
            print_success(f"Request completed in {elapsed_time:.2f}ms")
            
            # Display response details
            print_info(f"\nSuccess: {data.get('success')}")
            
            if data.get('success'):
                print_info(f"Answer: {data.get('answer', 'No answer')[:200]}...")
                
                sources = data.get('sources', [])
                print_info(f"\nSources Found: {len(sources)}")
                
                for i, source in enumerate(sources[:3], 1):  # Show first 3 sources
                    print_info(f"\n  Source {i}:")
                    print_info(f"    Similarity: {source.get('similarity_score', 0):.3f}")
                    print_info(f"    Metadata: {source.get('metadata', {})}")
                    preview = source.get('preview', '')[:100]
                    print_info(f"    Preview: {preview}...")
                
                metadata = data.get('metadata', {})
                print_info(f"\nMetadata:")
                print_info(f"  Processing Time: {metadata.get('processing_time_ms')}ms")
                print_info(f"  Documents Found: {metadata.get('documents_found')}")
                
                return True
            else:
                print_error(f"Query failed: {data.get('error', 'Unknown error')}")
                return False
        else:
            print_error(f"Unexpected status code: {response.status_code}")
            print_error(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print_error(f"Request failed: {e}")
        return False

def test_empty_query():
    """Test the query endpoint with empty query"""
    print_test("Empty Query Test")
    
    try:
        payload = {
            "query": "",
            "user_id": "test_user"
        }
        
        response = requests.post(
            f"{BASE_URL}/query",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        data = response.json()
        
        if not data.get('success'):
            print_success("Empty query correctly rejected")
            print_info(f"Error: {data.get('error')}")
            return True
        else:
            print_error("Empty query should have been rejected")
            return False
            
    except Exception as e:
        print_error(f"Request failed: {e}")
        return False

def test_twilio_webhook_json():
    """Test the Twilio JSON webhook endpoint"""
    print_test("Twilio JSON Webhook (POST /webhook/twilio/json)")
    
    try:
        # Simulate Twilio form data
        form_data = {
            "Body": "What information do you have?",
            "From": "+1234567890",
            "MessageSid": "SM" + "x" * 32
        }
        
        response = requests.post(
            f"{BASE_URL}/webhook/twilio/json",
            data=form_data
        )
        
        if response.status_code == 200:
            data = response.json()
            print_success(f"Status Code: {response.status_code}")
            print_success("Webhook processed successfully")
            print_info(f"Answer: {data.get('answer', 'No answer')[:200]}...")
            return True
        else:
            print_error(f"Unexpected status code: {response.status_code}")
            return False
            
    except Exception as e:
        print_error(f"Request failed: {e}")
        return False

def test_twilio_webhook_twiml():
    """Test the Twilio TwiML webhook endpoint"""
    print_test("Twilio TwiML Webhook (POST /webhook/twilio)")
    
    try:
        # Simulate Twilio form data
        form_data = {
            "Body": "Hello, can you help me?",
            "From": "+1234567890",
            "MessageSid": "SM" + "y" * 32
        }
        
        response = requests.post(
            f"{BASE_URL}/webhook/twilio",
            data=form_data
        )
        
        if response.status_code == 200:
            print_success(f"Status Code: {response.status_code}")
            print_success("TwiML response received")
            
            # Check if response is XML
            if "<?xml" in response.text and "<Response>" in response.text:
                print_success("Valid TwiML format")
                print_info(f"\nTwiML Response:")
                print_info(response.text[:300])
                return True
            else:
                print_error("Response is not valid TwiML")
                return False
        else:
            print_error(f"Unexpected status code: {response.status_code}")
            return False
            
    except Exception as e:
        print_error(f"Request failed: {e}")
        return False

def test_performance():
    """Test response time performance"""
    print_test("Performance Test")
    
    print_info("Running 5 queries to measure average response time...")
    
    times = []
    successes = 0
    
    for i in range(5):
        try:
            payload = {
                "query": f"Test query number {i+1}",
                "user_id": "performance_test"
            }
            
            start = time.time()
            response = requests.post(
                f"{BASE_URL}/query",
                json=payload,
                timeout=30
            )
            elapsed = (time.time() - start) * 1000
            
            if response.status_code == 200:
                times.append(elapsed)
                successes += 1
                print_info(f"  Query {i+1}: {elapsed:.2f}ms")
            
        except Exception as e:
            print_warning(f"  Query {i+1} failed: {e}")
    
    if times:
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)
        
        print_info(f"\nResults:")
        print_info(f"  Success Rate: {successes}/5 ({successes*20}%)")
        print_info(f"  Average Time: {avg_time:.2f}ms")
        print_info(f"  Min Time: {min_time:.2f}ms")
        print_info(f"  Max Time: {max_time:.2f}ms")
        
        if avg_time < 3000:
            print_success("Performance is good (< 3 seconds)")
        elif avg_time < 5000:
            print_warning("Performance is acceptable (< 5 seconds)")
        else:
            print_error("Performance is slow (> 5 seconds)")
        
        return successes == 5
    else:
        print_error("All queries failed")
        return False

def test_edge_cases():
    """Test various edge cases"""
    print_test("Edge Cases Test")
    
    test_cases = [
        ("Very long query: " + "x" * 1000, "Long query"),
        ("Special chars: !@#$%^&*()", "Special characters"),
        ("Multi\nline\nquery", "Multiline query"),
        ("   Whitespace   ", "Whitespace trimming"),
    ]
    
    passed = 0
    
    for query, description in test_cases:
        try:
            print_info(f"\n  Testing: {description}")
            
            payload = {"query": query, "user_id": "edge_case_test"}
            response = requests.post(
                f"{BASE_URL}/query",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success') or data.get('error'):
                    print_success(f"    Handled correctly")
                    passed += 1
                else:
                    print_error(f"    Unexpected response")
            else:
                print_warning(f"    Status: {response.status_code}")
                
        except Exception as e:
            print_error(f"    Error: {e}")
    
    print_info(f"\nPassed: {passed}/{len(test_cases)}")
    return passed == len(test_cases)

def test_streaming_endpoint():
    """Test the streaming query endpoint"""
    print_test("Streaming Query Endpoint (POST /query/stream)")
    
    try:
        payload = {
            "query": "What information do you have in your knowledge base?",
            "user_id": "stream_test"
        }
        
        print_info("Starting streaming request...")
        start_time = time.time()
        
        # Make streaming request
        response = requests.post(
            f"{BASE_URL}/query/stream",
            json=payload,
            stream=True,
            timeout=30
        )
        
        if response.status_code != 200:
            print_error(f"Unexpected status code: {response.status_code}")
            return False
        
        print_success(f"Status Code: {response.status_code}")
        print_info("Receiving streamed chunks...")
        
        chunks_received = 0
        content_chunks = []
        sources_received = False
        end_received = False
        first_chunk_time = None
        
        # Process the stream
        for line in response.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
                
                # Parse SSE format
                if decoded_line.startswith('event:'):
                    event_type = decoded_line.split('event:')[1].strip()
                elif decoded_line.startswith('data:'):
                    try:
                        data_str = decoded_line.split('data:')[1].strip()
                        data = json.loads(data_str)
                        
                        chunks_received += 1
                        
                        if first_chunk_time is None and data.get('type') == 'content':
                            first_chunk_time = time.time()
                            ttfb = (first_chunk_time - start_time) * 1000
                            print_info(f"Time to first byte: {ttfb:.2f}ms")
                        
                        if data.get('type') == 'start':
                            print_info(f"  ▶ Stream started")
                        elif data.get('type') == 'content':
                            content = data.get('content', '')
                            content_chunks.append(content)
                            print(f"{Colors.GREEN}.{Colors.END}", end='', flush=True)
                        elif data.get('type') == 'sources':
                            sources_received = True
                            sources = data.get('sources', [])
                            print()  # New line after dots
                            print_info(f"  📚 Received {len(sources)} sources")
                        elif data.get('type') == 'end':
                            end_received = True
                            metadata = data.get('metadata', {})
                            print()  # New line
                            print_info(f"  ✓ Stream ended")
                            print_info(f"  Total time: {metadata.get('processing_time_ms')}ms")
                        elif data.get('type') == 'error':
                            print()  # New line
                            print_error(f"  Error in stream: {data.get('error')}")
                            
                    except json.JSONDecodeError:
                        continue
        
        total_time = (time.time() - start_time) * 1000
        full_answer = ''.join(content_chunks)
        
        print()  # New line
        print_success(f"Streaming completed in {total_time:.2f}ms")
        print_info(f"Chunks received: {chunks_received}")
        print_info(f"Content length: {len(full_answer)} characters")
        print_info(f"Answer preview: {full_answer[:150]}...")
        
        if sources_received and end_received:
            print_success("All expected events received")
            return True
        else:
            print_warning("Some expected events missing")
            return False
            
    except Exception as e:
        print_error(f"Request failed: {e}")
        return False

def test_streaming_vs_regular():
    """Compare streaming vs regular response times"""
    print_test("Streaming vs Regular Performance Comparison")
    
    query = "What do you know about the documents in your database?"
    
    try:
        # Test regular endpoint
        print_info("Testing regular endpoint...")
        start = time.time()
        response = requests.post(
            f"{BASE_URL}/query",
            json={"query": query, "user_id": "perf_test"},
            timeout=30
        )
        regular_time = (time.time() - start) * 1000
        
        if response.status_code == 200:
            print_success(f"Regular response: {regular_time:.2f}ms")
        else:
            print_error("Regular endpoint failed")
            return False
        
        # Test streaming endpoint
        print_info("Testing streaming endpoint...")
        start = time.time()
        first_chunk_time = None
        
        response = requests.post(
            f"{BASE_URL}/query/stream",
            json={"query": query, "user_id": "perf_test"},
            stream=True,
            timeout=30
        )
        
        for line in response.iter_lines():
            if line and first_chunk_time is None:
                decoded_line = line.decode('utf-8')
                if 'data:' in decoded_line and '"type":"content"' in decoded_line:
                    first_chunk_time = time.time()
                    break
        
        if first_chunk_time:
            ttfb = (first_chunk_time - start) * 1000
            print_success(f"Streaming TTFB: {ttfb:.2f}ms")
            
            improvement = ((regular_time - ttfb) / regular_time) * 100
            print_info(f"\n  Performance Comparison:")
            print_info(f"  Regular: {regular_time:.2f}ms (complete response)")
            print_info(f"  Streaming: {ttfb:.2f}ms (first content)")
            print_info(f"  Improvement: {improvement:.1f}% faster to first byte")
            
            if ttfb < regular_time:
                print_success("Streaming provides better perceived performance!")
                return True
            else:
                print_warning("Streaming didn't improve TTFB")
                return False
        else:
            print_error("Didn't receive streaming content")
            return False
            
    except Exception as e:
        print_error(f"Comparison failed: {e}")
        return False

def run_all_tests():
    """Run all tests"""
    print_header("RAG AGENT WORKFLOW API - TEST SUITE")
    
    print_info(f"Testing API at: {BASE_URL}")
    print_info(f"Start time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    results = {}
    
    # Run tests
    tests = [
        ("Root Endpoint", test_root_endpoint),
        ("Health Check", test_health_endpoint),
        ("Query Endpoint 1", lambda: test_query_endpoint(TEST_QUERIES[0])),
        ("Query Endpoint 2", lambda: test_query_endpoint(TEST_QUERIES[1])),
        ("Empty Query", test_empty_query),
        ("Streaming Endpoint", test_streaming_endpoint),
        ("Streaming vs Regular", test_streaming_vs_regular),
        ("Twilio JSON Webhook", test_twilio_webhook_json),
        ("Twilio TwiML Webhook", test_twilio_webhook_twiml),
        ("Performance", test_performance),
        ("Edge Cases", test_edge_cases),
    ]: test_query_endpoint(TEST_QUERIES[1])),
        ("Empty Query", test_empty_query),
        ("Twilio JSON Webhook", test_twilio_webhook_json),
        ("Twilio TwiML Webhook", test_twilio_webhook_twiml),
        ("Performance", test_performance),
        ("Edge Cases", test_edge_cases),
    ]
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results[test_name] = result
        except Exception as e:
            print_error(f"Test crashed: {e}")
            results[test_name] = False
        
        print()  # Add spacing between tests
        time.sleep(0.5)  # Small delay between tests
    
    # Print summary
    print_header("TEST SUMMARY")
    
    passed = sum(1 for r in results.values() if r)
    total = len(results)
    
    for test_name, result in results.items():
        status = f"{Colors.GREEN}PASS{Colors.END}" if result else f"{Colors.RED}FAIL{Colors.END}"
        print(f"  {test_name}: {status}")
    
    print(f"\n{Colors.BOLD}Total: {passed}/{total} tests passed{Colors.END}")
    
    if passed == total:
        print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 ALL TESTS PASSED! 🎉{Colors.END}")
    else:
        print(f"\n{Colors.YELLOW}{Colors.BOLD}⚠ Some tests failed. Check the output above.{Colors.END}")
    
    return passed == total

def interactive_test():
    """Run an interactive test session"""
    print_header("INTERACTIVE TEST MODE")
    
    print("Enter your queries (type 'exit' to quit):\n")
    
    while True:
        try:
            query = input(f"{Colors.BLUE}Query > {Colors.END}").strip()
            
            if query.lower() in ['exit', 'quit', 'q']:
                print("\nExiting interactive mode...")
                break
            
            if not query:
                continue
            
            print()
            test_query_endpoint(query, "interactive_user")
            print()
            
        except KeyboardInterrupt:
            print("\n\nExiting interactive mode...")
            break
        except Exception as e:
            print_error(f"Error: {e}")

if __name__ == "__main__":
    import sys
    
    print(f"""
{Colors.BOLD}RAG Agent API Test Suite{Colors.END}
{Colors.BLUE}{'='*60}{Colors.END}

Usage:
  python test_api.py              # Run all automated tests
  python test_api.py interactive  # Run interactive test mode
  python test_api.py quick        # Run quick basic tests only

Make sure the API is running at {BASE_URL}
Start it with: python app.py
{Colors.BLUE}{'='*60}{Colors.END}
    """)
    
    # Check if API is accessible
    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        if response.status_code != 200:
            print_error(f"API returned status {response.status_code}")
            print_error("Make sure the API is running!")
            sys.exit(1)
    except Exception as e:
        print_error(f"Cannot connect to API at {BASE_URL}")
        print_error(f"Error: {e}")
        print_error("\nMake sure to start the API first with: python app.py")
        sys.exit(1)
    
    # Determine which tests to run
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
        
        if mode == "interactive":
            interactive_test()
        elif mode == "quick":
            print_header("QUICK TEST MODE")
            test_root_endpoint()
            print()
            test_health_endpoint()
            print()
            test_query_endpoint(TEST_QUERIES[0])
        else:
            print_error(f"Unknown mode: {mode}")
            sys.exit(1)
    else:
        # Run all tests
        success = run_all_tests()
        sys.exit(0 if success else 1)
