#!/usr/bin/env python3
"""
Validation script for LLMAIStrategy refactoring.

This script demonstrates:
1. New LLMAIStrategy class
2. Backward compatibility with GrokAIStrategy
3. OpenAI analyzer integration
4. Parameter naming (llm_analyzer vs grok_analyzer)
"""

import sys
from loguru import logger

# Configure logger
logger.remove()
logger.add(sys.stderr, level="INFO")

def main():
    """Run validation checks."""
    logger.info("=" * 60)
    logger.info("LLMAIStrategy Refactoring Validation")
    logger.info("=" * 60)
    
    # Test 1: Import validation
    logger.info("\n[1/6] Testing imports...")
    try:
        from yunmin.strategy.grok_ai_strategy import LLMAIStrategy, GrokAIStrategy
        from yunmin.llm.openai_analyzer import OpenAIAnalyzer
        from yunmin.llm.grok_analyzer import GrokAnalyzer
        logger.success("✅ All imports successful")
    except Exception as e:
        logger.error(f"❌ Import failed: {e}")
        return False
    
    # Test 2: Backward compatibility
    logger.info("\n[2/6] Testing backward compatibility...")
    try:
        assert issubclass(GrokAIStrategy, LLMAIStrategy)
        logger.success("✅ GrokAIStrategy is subclass of LLMAIStrategy")
    except AssertionError:
        logger.error("❌ Backward compatibility broken")
        return False
    
    # Test 3: New parameter naming
    logger.info("\n[3/6] Testing new parameter naming (llm_analyzer)...")
    try:
        from unittest.mock import Mock
        mock_analyzer = Mock()
        mock_analyzer.enabled = False
        
        strategy = LLMAIStrategy(llm_analyzer=mock_analyzer)
        assert strategy.llm is mock_analyzer
        assert strategy.grok is mock_analyzer  # Backward compat alias
        logger.success("✅ New parameter naming works correctly")
    except Exception as e:
        logger.error(f"❌ New parameter naming failed: {e}")
        return False
    
    # Test 4: Old parameter naming (backward compat)
    logger.info("\n[4/6] Testing old parameter naming (grok_analyzer)...")
    try:
        strategy = LLMAIStrategy(grok_analyzer=mock_analyzer)
        assert strategy.llm is mock_analyzer
        logger.success("✅ Old parameter naming still works (backward compat)")
    except Exception as e:
        logger.error(f"❌ Old parameter naming failed: {e}")
        return False
    
    # Test 5: OpenAI analyzer integration
    logger.info("\n[5/6] Testing OpenAI analyzer integration...")
    try:
        analyzer = OpenAIAnalyzer()
        logger.info(f"   OpenAI analyzer enabled: {analyzer.enabled}")
        
        strategy = LLMAIStrategy(llm_analyzer=analyzer)
        assert strategy.llm is analyzer
        
        if analyzer.enabled:
            logger.success("✅ OpenAI analyzer integrated and enabled")
        else:
            logger.warning("⚠️  OpenAI analyzer integrated but disabled (no API key)")
            logger.info("   Set OPENAI_API_KEY environment variable to enable")
    except Exception as e:
        logger.error(f"❌ OpenAI integration failed: {e}")
        return False
    
    # Test 6: Groq analyzer integration (legacy)
    logger.info("\n[6/6] Testing Groq analyzer integration (legacy)...")
    try:
        analyzer = GrokAnalyzer()
        logger.info(f"   Groq analyzer enabled: {analyzer.enabled}")
        
        strategy = LLMAIStrategy(llm_analyzer=analyzer)
        assert strategy.llm is analyzer
        
        if analyzer.enabled:
            logger.success("✅ Groq analyzer integrated and enabled")
        else:
            logger.warning("⚠️  Groq analyzer integrated but disabled (no API key)")
            logger.info("   Set GROK_API_KEY environment variable to enable")
    except Exception as e:
        logger.error(f"❌ Groq integration failed: {e}")
        return False
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.success("✅ All validation checks passed!")
    logger.info("=" * 60)
    logger.info("\nRefactoring Summary:")
    logger.info("• LLMAIStrategy: New primary class name")
    logger.info("• GrokAIStrategy: Deprecated alias (backward compatible)")
    logger.info("• llm_analyzer: New parameter name")
    logger.info("• grok_analyzer: Old parameter name (still works)")
    logger.info("• OpenAI: Primary LLM provider")
    logger.info("• Groq: Alternative LLM provider")
    logger.info("\nConfiguration:")
    logger.info("• Set OPENAI_API_KEY for OpenAI (recommended)")
    logger.info("• Set GROK_API_KEY for Groq (alternative)")
    logger.info("• Update config/default.yaml: provider: openai")
    logger.info("=" * 60)
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
