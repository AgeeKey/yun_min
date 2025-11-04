#!/usr/bin/env python3
"""Quick test runner for market scenarios."""

import sys
import subprocess

def main():
    """Run market scenario tests and report."""
    print("=" * 60)
    print("Testing Market Scenarios (Task 6)")
    print("=" * 60)
    
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", 
             "tests/test_market_scenarios.py", 
             "-v", "--tb=short", "-x",
             "-k", "not slow"],  # Skip slow tests initially
            capture_output=True,
            text=True,
            timeout=120
        )
        
        print(result.stdout)
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        
        print("\n" + "=" * 60)
        if result.returncode == 0:
            print("✅ ALL MARKET SCENARIO TESTS PASSED!")
        else:
            print(f"❌ Tests failed with code {result.returncode}")
        print("=" * 60)
        
        return result.returncode
        
    except subprocess.TimeoutExpired:
        print("❌ Tests timed out (>120s)")
        return 1
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
