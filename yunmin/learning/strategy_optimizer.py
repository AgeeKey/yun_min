"""
Strategy Optimizer - Optimizes Trading Strategy Parameters

Uses grid search, random search, or Bayesian optimization
to find optimal strategy parameters.
"""

from typing import Dict, Any, List, Optional, Callable
import numpy as np
from loguru import logger


class StrategyOptimizer:
    """
    Optimizes trading strategy parameters.
    
    Methods:
    - Grid search: Exhaustive search over parameter grid
    - Random search: Random sampling of parameter space
    - Bayesian optimization: Smart search using past results
    """
    
    def __init__(self, method: str = 'random'):
        """
        Initialize strategy optimizer.
        
        Args:
            method: Optimization method ('grid', 'random', 'bayesian')
        """
        self.method = method
        self.optimization_history: List[Dict[str, Any]] = []
        
        logger.info(f"🎯 Strategy Optimizer initialized (method={method})")
    
    def optimize(
        self,
        param_space: Dict[str, Any],
        objective_function: Callable,
        n_iterations: int = 50,
        n_trials: int = None,  # Backwards compatibility
        maximize: bool = True
    ) -> Dict[str, Any]:
        """
        Optimize strategy parameters.
        
        Args:
            param_space: Parameter space to search
            objective_function: Function to optimize (returns score)
            n_iterations: Number of iterations
            n_trials: Alias for n_iterations (backwards compatibility)
            maximize: Whether to maximize (True) or minimize (False)
            
        Returns:
            Best parameters and score
        """
        # Backwards compatibility
        if n_trials is not None:
            n_iterations = n_trials
        
        logger.info(f"Starting {self.method} optimization with {n_iterations} iterations")
        
        if self.method == 'grid':
            result = self._grid_search(objective_function, param_space, maximize)
        elif self.method == 'random':
            result = self._random_search(objective_function, param_space, n_iterations, maximize)
        elif self.method == 'bayesian':
            result = self._bayesian_optimization(objective_function, param_space, n_iterations, maximize)
        else:
            logger.warning(f"Unknown method {self.method}, using random search")
            result = self._random_search(objective_function, param_space, n_iterations, maximize)
        
        logger.info(f"✅ Optimization complete: best score = {result['best_score']:.4f}")
        return result
    
    def _grid_search(
        self,
        objective_function: Callable,
        param_space: Dict[str, Any],
        maximize: bool
    ) -> Dict[str, Any]:
        """
        Grid search optimization.
        
        Warning: Can be very slow for large parameter spaces!
        """
        # Generate all combinations
        param_combinations = self._generate_grid(param_space)
        
        best_score = float('-inf') if maximize else float('inf')
        best_params = None
        
        for params in param_combinations:
            score = objective_function(**params)
            
            self.optimization_history.append({
                'params': params,
                'score': score
            })
            
            if (maximize and score > best_score) or (not maximize and score < best_score):
                best_score = score
                best_params = params
        
        return {
            'best_params': best_params,
            'best_score': best_score,
            'n_evaluations': len(param_combinations),
            'method': 'grid'
        }
    
    def _random_search(
        self,
        objective_function: Callable,
        param_space: Dict[str, Any],
        n_iterations: int,
        maximize: bool
    ) -> Dict[str, Any]:
        """Random search optimization."""
        best_score = float('-inf') if maximize else float('inf')
        best_params = None
        
        for i in range(n_iterations):
            # Sample random parameters
            params = self._sample_params(param_space)
            
            # Evaluate
            score = objective_function(**params)
            
            self.optimization_history.append({
                'params': params,
                'score': score
            })
            
            # Update best
            if (maximize and score > best_score) or (not maximize and score < best_score):
                best_score = score
                best_params = params
                logger.debug(f"Iteration {i+1}/{n_iterations}: New best score = {best_score:.4f}")
        
        return {
            'best_params': best_params,
            'best_score': best_score,
            'n_evaluations': n_iterations,
            'method': 'random'
        }
    
    def _bayesian_optimization(
        self,
        objective_function: Callable,
        param_space: Dict[str, Any],
        n_iterations: int,
        maximize: bool
    ) -> Dict[str, Any]:
        """
        Bayesian optimization (simplified).
        
        In production, would use a library like scikit-optimize or Optuna.
        """
        logger.warning("Bayesian optimization not fully implemented, using random search")
        return self._random_search(objective_function, param_space, n_iterations, maximize)
    
    def _generate_grid(self, param_space: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate all combinations for grid search."""
        # Simplified grid generation
        param_names = list(param_space.keys())
        param_values = [self._get_param_values(v) for v in param_space.values()]
        
        combinations = []
        
        def generate_recursive(current_params, depth):
            if depth == len(param_names):
                combinations.append(current_params.copy())
                return
            
            param_name = param_names[depth]
            for value in param_values[depth]:
                current_params[param_name] = value
                generate_recursive(current_params, depth + 1)
        
        generate_recursive({}, 0)
        return combinations
    
    def _get_param_values(self, param_spec: Any) -> List[Any]:
        """Get list of values for a parameter."""
        if isinstance(param_spec, list):
            return param_spec
        elif isinstance(param_spec, dict):
            # Range specification
            if 'range' in param_spec:
                start, end, step = param_spec['range']
                return list(np.arange(start, end, step))
        
        return [param_spec]
    
    def _sample_params(self, param_space: Dict[str, Any]) -> Dict[str, Any]:
        """Sample random parameters from space."""
        params = {}
        
        for name, spec in param_space.items():
            if isinstance(spec, tuple) and len(spec) == 2:
                # Tuple format (min, max) - added support
                start, end = spec
                if isinstance(start, int) and isinstance(end, int):
                    params[name] = int(np.random.randint(start, end + 1))
                else:
                    params[name] = float(np.random.uniform(start, end))
            elif isinstance(spec, list):
                # Choose from list
                params[name] = np.random.choice(spec)
            elif isinstance(spec, dict):
                if 'range' in spec:
                    # Uniform sample from range
                    start, end, _ = spec['range']
                    if isinstance(start, int) and isinstance(end, int):
                        params[name] = int(np.random.randint(start, end))
                    else:
                        params[name] = float(np.random.uniform(start, end))
                elif 'type' in spec:
                    # Sample based on type
                    if spec['type'] == 'int':
                        params[name] = int(np.random.randint(spec['min'], spec['max']))
                    elif spec['type'] == 'float':
                        params[name] = float(np.random.uniform(spec['min'], spec['max']))
            else:
                # Use as-is
                params[name] = spec
        
        return params
    
    def get_optimization_summary(self) -> Dict[str, Any]:
        """Get summary of optimization process."""
        if not self.optimization_history:
            return {
                'n_evaluations': 0,
                'best_score': None,
                'mean_score': None,
                'std_score': None
            }
        
        scores = [h['score'] for h in self.optimization_history]
        
        return {
            'n_evaluations': len(self.optimization_history),
            'best_score': max(scores),
            'worst_score': min(scores),
            'mean_score': np.mean(scores),
            'std_score': np.std(scores),
            'improvement': (max(scores) - scores[0]) / abs(scores[0]) if scores[0] != 0 else 0
        }
    
    def plot_optimization_history(self):
        """
        Plot optimization history.
        
        Note: Requires matplotlib, returns data for plotting instead.
        """
        if not self.optimization_history:
            return None
        
        iterations = list(range(len(self.optimization_history)))
        scores = [h['score'] for h in self.optimization_history]
        
        # Running best
        running_best = []
        current_best = float('-inf')
        for score in scores:
            current_best = max(current_best, score)
            running_best.append(current_best)
        
        return {
            'iterations': iterations,
            'scores': scores,
            'running_best': running_best
        }
