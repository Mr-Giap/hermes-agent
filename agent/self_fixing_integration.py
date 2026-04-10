"""
Self-Fixing Integration for Hermes Agent
Provides easy integration with existing Hermes agent
"""

import logging
from dataclasses import dataclass
from typing import Dict, Any, Callable, Optional, Tuple

from agent.self_fixing import SelfFixingEngine

logger = logging.getLogger(__name__)


@dataclass
class IntegrationConfig:
    """Configuration for self-fixing integration"""
    max_retries: int = 4
    enable_learning: bool = True
    log_level: str = "INFO"


class SelfFixingToolWrapper:
    """Wraps tool execution with self-fixing capabilities"""
    
    def __init__(self, config: Optional[IntegrationConfig] = None):
        self.config = config or IntegrationConfig()
        self.engine = SelfFixingEngine(
            max_retries=self.config.max_retries,
            enable_learning=self.config.enable_learning
        )
        
        # Setup logging
        logging.basicConfig(level=getattr(logging, self.config.log_level))
    
    def execute_tool(self, tool_name: str, tool_func: Callable, tool_params: Dict[str, Any]) -> Tuple[bool, Any, Optional[Exception]]:
        """Execute tool with self-fixing"""
        logger.info(f"Executing tool: {tool_name}")
        
        success, result, error = self.engine.execute_with_recovery(
            tool_func, tool_params, tool_name
        )
        
        if success:
            logger.info(f"Tool {tool_name} succeeded")
        else:
            logger.error(f"Tool {tool_name} failed after all retries: {error}")
        
        return success, result, error
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get metrics"""
        return self.engine.get_metrics()
    
    def get_health_report(self) -> Dict[str, Any]:
        """Get health report"""
        return {
            'status': self.engine.get_health_status(),
            'health_score': f"{self.engine.get_health_score()}/100",
            'metrics': self.get_metrics()
        }


class HermesAgentIntegration:
    """Integration with Hermes Agent"""
    
    def __init__(self, agent, config: Optional[IntegrationConfig] = None):
        self.agent = agent
        self.wrapper = SelfFixingToolWrapper(config)
        self._original_execute_tool = None
        self._wrap_agent()
    
    def _wrap_agent(self):
        """Wrap agent's execute_tool method"""
        if not hasattr(self.agent, 'execute_tool'):
            logger.warning("Agent does not have execute_tool method, skipping integration")
            return
        
        self._original_execute_tool = self.agent.execute_tool
        
        def wrapped_execute_tool(tool_name: str, params: Dict[str, Any]):
            """Wrapped execute_tool with self-fixing"""
            def tool_func(**kwargs):
                return self._original_execute_tool(tool_name, kwargs)
            
            success, result, error = self.wrapper.execute_tool(
                tool_name, tool_func, params
            )
            
            if not success:
                raise error
            
            return result
        
        self.agent.execute_tool = wrapped_execute_tool
        logger.info("Self-fixing integration enabled for Hermes Agent")
    
    def disable(self):
        """Disable self-fixing integration"""
        if self._original_execute_tool:
            self.agent.execute_tool = self._original_execute_tool
            logger.info("Self-fixing integration disabled")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get metrics"""
        return self.wrapper.get_metrics()
    
    def get_health_report(self) -> Dict[str, Any]:
        """Get health report"""
        return self.wrapper.get_health_report()


def create_self_fixing_agent(agent, config: Optional[IntegrationConfig] = None) -> HermesAgentIntegration:
    """
    Create self-fixing agent with one line
    
    Usage:
        agent = HermesAgent()
        integration = create_self_fixing_agent(agent)
        
        # Use agent normally
        result = agent.execute_tool('terminal', {'command': 'ls'})
        
        # Monitor
        metrics = integration.get_metrics()
        health = integration.get_health_report()
    """
    return HermesAgentIntegration(agent, config)


def wrap_tool(tool_func: Callable, config: Optional[IntegrationConfig] = None) -> Callable:
    """
    Decorator to wrap individual tools with self-fixing
    
    Usage:
        @wrap_tool
        def my_tool(param1, param2):
            # tool implementation
            pass
    """
    wrapper = SelfFixingToolWrapper(config)
    
    def wrapped(**kwargs):
        success, result, error = wrapper.execute_tool(
            tool_func.__name__, tool_func, kwargs
        )
        if not success:
            raise error
        return result
    
    return wrapped
