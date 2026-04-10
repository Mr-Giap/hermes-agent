"""
Quick test suite for self-fixing agent
Run: python examples/quick_tests.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.self_fixing_integration import SelfFixingToolWrapper, IntegrationConfig


def test_basic_retry():
    """Test basic retry mechanism"""
    print("\n1. Testing Basic Retry...")
    wrapper = SelfFixingToolWrapper()
    
    attempt = [0]
    def failing_tool():
        attempt[0] += 1
        if attempt[0] < 2:
            raise ConnectionError("Network error")
        return "Success"
    
    success, result, error = wrapper.execute_tool('test_retry', failing_tool, {})
    
    assert success, "Should succeed after retry"
    assert attempt[0] == 2, f"Should retry once, got {attempt[0]} attempts"
    assert result == "Success"
    print("  ✅ PASS - Basic Retry")


def test_parameter_adjustment():
    """Test parameter adjustment strategy"""
    print("\n2. Testing Parameter Adjustment...")
    wrapper = SelfFixingToolWrapper()
    
    def size_tool(size=100, limit=50):
        if size > limit:
            raise ValueError(f"Size {size} > limit {limit}")
        return f"OK: {size}"
    
    success, result, error = wrapper.execute_tool(
        'size_tool', size_tool, {'size': 100, 'limit': 50}
    )
    
    assert success, f"Should auto-adjust and succeed, got error: {error}"
    print("  ✅ PASS - Parameter Adjustment")


def test_metrics():
    """Test metrics collection"""
    print("\n3. Testing Metrics Collection...")
    wrapper = SelfFixingToolWrapper()
    
    def success_tool():
        return "OK"
    
    wrapper.execute_tool('test', success_tool, {})
    metrics = wrapper.get_metrics()
    
    assert metrics['total_calls'] == 1
    assert metrics['successful_calls'] == 1
    print("  ✅ PASS - Metrics Collection")


def test_health_score():
    """Test health score calculation"""
    print("\n4. Testing Health Score...")
    wrapper = SelfFixingToolWrapper()
    
    def success_tool():
        return "OK"
    
    for _ in range(10):
        wrapper.execute_tool('test', success_tool, {})
    
    health = wrapper.get_health_report()
    assert health['status'] == 'healthy'
    assert '100' in health['health_score']
    print("  ✅ PASS - Health Score")


def test_pattern_learning():
    """Test pattern learning"""
    print("\n5. Testing Pattern Learning...")
    config = IntegrationConfig(enable_learning=True)
    wrapper = SelfFixingToolWrapper(config)
    
    attempt = [0]
    def failing_tool():
        attempt[0] += 1
        if attempt[0] % 2 == 1:
            raise ConnectionError("Network error")
        return "Success"
    
    # Generate 6 ConnectionError patterns
    for i in range(6):
        attempt[0] = 0
        wrapper.execute_tool('test', failing_tool, {})
    
    patterns = wrapper.engine.tracker.get_recurring_patterns(min_count=5)
    assert len(patterns) > 0, "Should learn patterns"
    assert 'ConnectionError' in patterns
    print("  ✅ PASS - Pattern Learning")


def test_critical_error():
    """Test critical error handling"""
    print("\n6. Testing Critical Error...")
    wrapper = SelfFixingToolWrapper()
    
    def critical_tool():
        raise MemoryError("Out of memory")
    
    success, result, error = wrapper.execute_tool('test', critical_tool, {})
    
    assert not success, "Should fail on critical error"
    assert isinstance(error, MemoryError)
    print("  ✅ PASS - Critical Error")


def test_multiple_tools():
    """Test multiple tools"""
    print("\n7. Testing Multiple Tools...")
    wrapper = SelfFixingToolWrapper()
    
    def tool1():
        return "Tool1"
    
    def tool2():
        return "Tool2"
    
    success1, result1, _ = wrapper.execute_tool('tool1', tool1, {})
    success2, result2, _ = wrapper.execute_tool('tool2', tool2, {})
    
    assert success1 and success2
    assert result1 == "Tool1" and result2 == "Tool2"
    
    metrics = wrapper.get_metrics()
    assert metrics['total_calls'] == 2
    print("  ✅ PASS - Multiple Tools")


def run_all_tests():
    """Run all tests"""
    print("=" * 70)
    print("  SELF-FIXING AGENT - QUICK TEST SUITE")
    print("=" * 70)
    
    tests = [
        test_basic_retry,
        test_parameter_adjustment,
        test_metrics,
        test_health_score,
        test_pattern_learning,
        test_critical_error,
        test_multiple_tools,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"  ❌ FAIL - {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"  ❌ ERROR - {test.__name__}: {e}")
            failed += 1
    
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"  Total: {passed + failed} tests")
    print(f"  Passed: {passed}")
    print(f"  Failed: {failed}")
    print("-" * 70)
    
    if failed == 0:
        print("  🎉 ALL TESTS PASSED!")
    else:
        print(f"  ⚠️  {failed} test(s) failed")
    
    print("=" * 70)
    
    return failed == 0


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
