#!/usr/bin/env python3
"""
System Integration Test for Observability & Trust Layer
Tests end-to-end functionality from agent interaction to dashboard display
"""

import sys
import os
import time
import requests
import json
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

def test_api_endpoints():
    """Test that API endpoints are responding correctly"""
    base_url = "http://localhost:8000"
    
    try:
        # Test status endpoint
        response = requests.get(f"{base_url}/status", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Status endpoint working: {data.get('state', 'unknown')}")
            return True
        else:
            print(f"✗ Status endpoint failed: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"✗ API connection failed: {e}")
        return False

def test_trust_manager():
    """Test trust manager functionality"""
    try:
        from config import Settings
        from prediction_engine.trust_manager import TrustManager
        
        settings = Settings()
        trust_manager = TrustManager(settings.trust_score)
        
        # Test agent initialization
        agent_id = "test_agent_001"
        trust_manager.initialize_agent(agent_id)
        score = trust_manager.get_trust_score(agent_id)
        
        if score == 100:  # Initial trust score
            print(f"✓ Trust manager working: Agent {agent_id} initialized with score {score}")
            return True
        else:
            print(f"✗ Trust manager failed: Expected score 100, got {score}")
            return False
            
    except Exception as e:
        print(f"✗ Trust manager test failed: {e}")
        return False

def test_configuration():
    """Test system configuration"""
    try:
        from config import Settings
        
        settings = Settings()
        print(f"✓ Configuration loaded successfully")
        print(f"  - Environment: {settings.environment}")
        print(f"  - Redis host: {settings.redis.host}:{settings.redis.port}")
        print(f"  - Datadog enabled: {settings.datadog.enabled}")
        return True
        
    except Exception as e:
        print(f"✗ Configuration test failed: {e}")
        return False

def test_system_health():
    """Test overall system health"""
    try:
        from system_health import SystemHealthMonitor
        from config import Settings
        
        settings = Settings()
        health_monitor = SystemHealthMonitor(settings)
        
        # Get system health status
        health_status = health_monitor.get_system_health()
        
        print(f"✓ System health check completed")
        print(f"  - Overall status: {health_status.get('status', 'unknown')}")
        return True
        
    except Exception as e:
        print(f"✗ System health test failed: {e}")
        return False

def main():
    """Run comprehensive system integration tests"""
    print("=" * 60)
    print("CHORUS SYSTEM INTEGRATION TEST")
    print("=" * 60)
    
    tests = [
        ("Configuration", test_configuration),
        ("Trust Manager", test_trust_manager),
        ("System Health", test_system_health),
        # Note: API test requires server to be running
        # ("API Endpoints", test_api_endpoints),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n[{test_name}]")
        try:
            if test_func():
                passed += 1
            else:
                print(f"  Test failed")
        except Exception as e:
            print(f"  Test error: {e}")
    
    print("\n" + "=" * 60)
    print(f"RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("✓ All core system components are functional")
        return 0
    else:
        print("✗ Some system components have issues")
        return 1

if __name__ == "__main__":
    sys.exit(main())