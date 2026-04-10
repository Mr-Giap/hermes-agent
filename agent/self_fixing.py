"""
Self-Fixing Engine for Hermes Agent
Auto-detects errors, applies recovery strategies, learns from patterns
"""

import time
import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Tuple, List
from collections import defaultdict

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels"""
    RECOVERABLE = "recoverable"
    DEGRADED = "degraded"
    CRITICAL = "critical"


class FixStrategy(Enum):
    """Available fix strategies"""
    RETRY_BACKOFF = "retry_backoff"
    ADJUST_PARAMETERS = "adjust_parameters"
    SIMPLIFY_APPROACH = "simplify_approach"
    CACHE_RESULT = "cache_result"
    CHANGE_TOOL = "change_tool"
    DECOMPOSE_TASK = "decompose_task"
    ESCALATE_TO_USER = "escalate_to_user"


@dataclass
class ErrorDiagnosis:
    """Error diagnosis result"""
    error_type: str
    severity: ErrorSeverity
    message: str
    context: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class ErrorPattern:
    """Recurring error pattern"""
    error_type: str
    count: int = 0
    last_seen: float = field(default_factory=time.time)
    best_strategy: Optional[FixStrategy] = None
    strategy_success_rate: Dict[str, float] = field(default_factory=dict)


class ErrorPatternTracker:
    """Tracks and learns from error patterns"""
    
    def __init__(self, max_errors: int = 100):
        self.max_errors = max_errors
        self.errors: List[ErrorDiagnosis] = []
        self.patterns: Dict[str, ErrorPattern] = {}
        self.strategy_attempts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.strategy_success: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    
    def add_error(self, diagnosis: ErrorDiagnosis) -> None:
        """Track error"""
        self.errors.append(diagnosis)
        if len(self.errors) > self.max_errors:
            self.errors.pop(0)
        
        # Update pattern
        if diagnosis.error_type not in self.patterns:
            self.patterns[diagnosis.error_type] = ErrorPattern(error_type=diagnosis.error_type)
        
        self.patterns[diagnosis.error_type].count += 1
        self.patterns[diagnosis.error_type].last_seen = time.time()
    
    def record_strategy_attempt(self, error_type: str, strategy: FixStrategy, success: bool) -> None:
        """Record strategy attempt"""
        self.strategy_attempts[error_type][strategy.value] += 1
        if success:
            self.strategy_success[error_type][strategy.value] += 1
            self._update_best_strategy(error_type)
    
    def _update_best_strategy(self, error_type: str) -> None:
        """Update best strategy for error type"""
        if error_type not in self.patterns:
            return
        
        best_strategy = None
        best_rate = 0.0
        
        for strategy, attempts in self.strategy_attempts[error_type].items():
            if attempts == 0:
                continue
            success = self.strategy_success[error_type].get(strategy, 0)
            rate = success / attempts
            if rate > best_rate:
                best_rate = rate
                best_strategy = FixStrategy(strategy)
        
        if best_strategy:
            self.patterns[error_type].best_strategy = best_strategy
            self.patterns[error_type].strategy_success_rate = {
                strategy: self.strategy_success[error_type].get(strategy, 0) / 
                         self.strategy_attempts[error_type].get(strategy, 1)
                for strategy in self.strategy_attempts[error_type]
            }
    
    def get_best_strategy(self, error_type: str) -> Optional[FixStrategy]:
        """Get best learned strategy for error type"""
        if error_type not in self.patterns:
            return None
        return self.patterns[error_type].best_strategy
    
    def get_recurring_patterns(self, min_count: int = 5) -> Dict[str, ErrorPattern]:
        """Get patterns that occurred min_count+ times"""
        return {
            error_type: pattern
            for error_type, pattern in self.patterns.items()
            if pattern.count >= min_count
        }


class SelfFixingEngine:
    """Core self-fixing engine"""
    
    def __init__(self, max_retries: int = 4, enable_learning: bool = True):
        self.max_retries = max_retries
        self.enable_learning = enable_learning
        self.tracker = ErrorPatternTracker()
        
        # Metrics
        self.total_calls = 0
        self.successful_calls = 0
        self.auto_fixed_calls = 0
        self.failed_calls = 0
        self.total_fix_time = 0.0
    
    def diagnose_error(self, error: Exception, context: Dict[str, Any] = None) -> ErrorDiagnosis:
        """Diagnose error and determine severity"""
        error_type = type(error).__name__
        message = str(error)
        
        # Determine severity
        if error_type in ['ConnectionError', 'TimeoutError', 'RuntimeError', 'ValueError']:
            severity = ErrorSeverity.RECOVERABLE
        elif error_type in ['TypeError']:
            severity = ErrorSeverity.DEGRADED
        else:
            severity = ErrorSeverity.CRITICAL
        
        diagnosis = ErrorDiagnosis(
            error_type=error_type,
            severity=severity,
            message=message,
            context=context or {}
        )
        
        if self.enable_learning:
            self.tracker.add_error(diagnosis)
        
        return diagnosis
    
    def get_fix_strategy(self, diagnosis: ErrorDiagnosis) -> FixStrategy:
        """Determine best fix strategy"""
        # Check if we learned a strategy for this error
        if self.enable_learning:
            learned_strategy = self.tracker.get_best_strategy(diagnosis.error_type)
            if learned_strategy:
                return learned_strategy
        
        # Default strategies by error type
        strategy_map = {
            'ConnectionError': FixStrategy.RETRY_BACKOFF,
            'TimeoutError': FixStrategy.ADJUST_PARAMETERS,
            'ValueError': FixStrategy.ADJUST_PARAMETERS,
            'RuntimeError': FixStrategy.RETRY_BACKOFF,
        }
        
        return strategy_map.get(diagnosis.error_type, FixStrategy.RETRY_BACKOFF)
    
    def execute_with_recovery(self, tool_func, tool_params: Dict[str, Any], tool_name: str) -> Tuple[bool, Any, Optional[Exception]]:
        """Execute tool with automatic recovery"""
        self.total_calls += 1
        start_time = time.time()
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                result = tool_func(**tool_params)
                self.successful_calls += 1
                if attempt > 0:
                    self.auto_fixed_calls += 1
                
                fix_time = time.time() - start_time
                self.total_fix_time += fix_time
                
                return True, result, None
            
            except Exception as e:
                last_error = e
                diagnosis = self.diagnose_error(e, {'tool': tool_name, 'attempt': attempt})
                
                logger.error(f"Tool {tool_name} failed: {diagnosis.message}")
                
                if diagnosis.severity == ErrorSeverity.CRITICAL:
                    self.failed_calls += 1
                    return False, None, e
                
                strategy = self.get_fix_strategy(diagnosis)
                
                # Apply strategy
                if strategy == FixStrategy.RETRY_BACKOFF:
                    wait_time = 2 ** attempt
                    logger.info(f"Retrying {tool_name} after {wait_time}s (attempt {attempt + 1}/{self.max_retries})")
                    time.sleep(wait_time)
                
                elif strategy == FixStrategy.ADJUST_PARAMETERS:
                    logger.info(f"Adjusting parameters for {tool_name}")
                    if 'timeout' in tool_params:
                        tool_params['timeout'] = tool_params.get('timeout', 30) * 2
                    # For size/limit scenarios, reduce size but keep limit
                    if 'size' in tool_params and 'limit' in tool_params:
                        tool_params['size'] = max(1, tool_params.get('size', 100) // 2)
                    elif 'limit' in tool_params:
                        tool_params['limit'] = max(1, tool_params.get('limit', 10) // 2)
                    elif 'size' in tool_params:
                        tool_params['size'] = max(1, tool_params.get('size', 100) // 2)
                
                elif strategy == FixStrategy.SIMPLIFY_APPROACH:
                    logger.info(f"Simplifying approach for {tool_name}")
                    # Remove optional parameters
                    for param in ['retry', 'cache', 'verbose', 'debug']:
                        tool_params.pop(param, None)
                
                # Record attempt
                if self.enable_learning:
                    self.tracker.record_strategy_attempt(diagnosis.error_type, strategy, False)
        
        self.failed_calls += 1
        return False, None, last_error
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics"""
        success_rate = (self.successful_calls / self.total_calls * 100) if self.total_calls > 0 else 0
        auto_fix_rate = (self.auto_fixed_calls / self.total_calls * 100) if self.total_calls > 0 else 0
        avg_fix_time = (self.total_fix_time / self.successful_calls) if self.successful_calls > 0 else 0
        
        return {
            'total_calls': self.total_calls,
            'successful_calls': self.successful_calls,
            'auto_fixed_calls': self.auto_fixed_calls,
            'failed_calls': self.failed_calls,
            'success_rate': f"{success_rate:.1f}%",
            'auto_fix_rate': f"{auto_fix_rate:.1f}%",
            'avg_fix_time': f"{avg_fix_time:.2f}s",
            'patterns_learned': len(self.tracker.get_recurring_patterns())
        }
    
    def get_health_score(self) -> int:
        """Calculate health score (0-100)"""
        if self.total_calls == 0:
            return 100
        
        success_rate = self.successful_calls / self.total_calls
        auto_fix_rate = self.auto_fixed_calls / self.total_calls
        
        # 80% weight on success, 20% on auto-fix
        score = int(success_rate * 80 + auto_fix_rate * 20)
        return min(100, max(0, score))
    
    def get_health_status(self) -> str:
        """Get health status"""
        score = self.get_health_score()
        if score >= 80:
            return "healthy"
        elif score >= 50:
            return "degraded"
        else:
            return "critical"
