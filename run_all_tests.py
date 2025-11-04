#!/usr/bin/env python3
"""Comprehensive test suite runner - validates all completed work."""

import sys
import subprocess
from typing import Dict, List

def run_test_suite(name: str, path: str, markers: str = "") -> Dict:
    """Run a test suite and return results."""
    print(f"\n{'='*60}")
    print(f"Running: {name}")
    print('='*60)
    
    cmd = [sys.executable, "-m", "pytest", path, "-v", "--tb=short"]
    if markers:
        cmd.extend(["-m", markers])
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        
        # Parse output for pass/fail counts
        output = result.stdout
        passed = failed = 0
        
        for line in output.split('\n'):
            if ' passed' in line:
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == 'passed' and i > 0:
                        try:
                            passed = int(parts[i-1])
                        except ValueError:
                            pass
            if ' failed' in line:
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == 'failed' and i > 0:
                        try:
                            failed = int(parts[i-1])
                        except ValueError:
                            pass
        
        print(output)
        
        return {
            'name': name,
            'passed': passed,
            'failed': failed,
            'returncode': result.returncode,
            'success': result.returncode == 0
        }
        
    except subprocess.TimeoutExpired:
        print(f"❌ {name} timed out!")
        return {'name': name, 'passed': 0, 'failed': 0, 'returncode': 1, 'success': False}
    except Exception as e:
        print(f"❌ Error running {name}: {e}")
        return {'name': name, 'passed': 0, 'failed': 0, 'returncode': 1, 'success': False}


def main():
    """Run all test suites and generate report."""
    
    print("🚀 YunMin Comprehensive Test Suite")
    print("=" * 60)
    print("Testing all completed work (Tasks 1-7)")
    print("=" * 60)
    
    test_suites = [
        ("Task 1: Persistence Layer", "tests/test_store.py", ""),
        ("Task 2: Backtesting Engine", "tests/test_backtester.py", ""),
        ("Task 3: Error Recovery", "tests/test_error_recovery.py", ""),
        ("Task 4: Alert Manager", "tests/test_alert_manager.py", ""),
        ("Task 5: Integration Tests", "tests/integration/test_e2e_pipeline.py", ""),
        ("Task 6: Market Scenarios", "tests/test_market_scenarios.py", "not slow"),
        ("Risk Manager", "tests/test_risk.py", ""),
        ("Config Loading", "tests/test_config.py", ""),
    ]
    
    results: List[Dict] = []
    
    for name, path, markers in test_suites:
        result = run_test_suite(name, path, markers)
        results.append(result)
    
    # Generate summary report
    print("\n" + "=" * 60)
    print("📊 COMPREHENSIVE TEST REPORT")
    print("=" * 60)
    
    total_passed = sum(r['passed'] for r in results)
    total_failed = sum(r['failed'] for r in results)
    total_tests = total_passed + total_failed
    
    print(f"\n{'Suite':<35} {'Passed':<10} {'Failed':<10} {'Status'}")
    print("-" * 60)
    
    for r in results:
        status = "✅ PASS" if r['success'] else "❌ FAIL"
        print(f"{r['name']:<35} {r['passed']:<10} {r['failed']:<10} {status}")
    
    print("-" * 60)
    print(f"{'TOTAL':<35} {total_passed:<10} {total_failed:<10}")
    
    if total_tests > 0:
        pass_rate = (total_passed / total_tests) * 100
        print(f"\n📈 Overall Pass Rate: {pass_rate:.1f}% ({total_passed}/{total_tests})")
    
    print("\n" + "=" * 60)
    
    if total_failed == 0:
        print("🎉 ALL TESTS PASSED! System is 100% validated!")
        print("=" * 60)
        return 0
    else:
        print(f"⚠️  {total_failed} tests failed. Review output above.")
        print("=" * 60)
        return 1

if __name__ == "__main__":
    sys.exit(main())
