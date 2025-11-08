"""
Ensemble Decision Maker - Multi-Agent Consensus

Combines decisions from multiple agents/models for robust decisions.
"""

from typing import Dict, Any, List
from loguru import logger


class EnsembleDecisionMaker:
    """
    Ensemble decision making from multiple agents.
    
    Methods:
    - Voting: Each agent votes, majority wins
    - Weighted: Each agent has weight based on past performance
    - Confidence-based: Higher confidence agents have more influence
    """
    
    def __init__(self, method: str = 'weighted'):
        """
        Initialize ensemble decision maker.
        
        Args:
            method: Ensemble method ('voting', 'weighted', 'confidence')
        """
        self.method = method
        self.agent_weights: Dict[str, float] = {}
        
        logger.info(f"🤝 Ensemble Decision Maker initialized (method={method})")
    
    def decide(
        self,
        agent_decisions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Make ensemble decision from multiple agent outputs.
        
        Args:
            agent_decisions: List of decisions from different agents
            
        Returns:
            Final ensemble decision
        """
        if not agent_decisions:
            return {
                'decision': 'HOLD',
                'confidence': 0.5,
                'method': 'no_agents',
                'agents_count': 0
            }
        
        logger.debug(f"Making ensemble decision from {len(agent_decisions)} agents")
        
        if self.method == 'voting':
            result = self._voting_ensemble(agent_decisions)
        elif self.method == 'weighted':
            result = self._weighted_ensemble(agent_decisions)
        elif self.method == 'confidence':
            result = self._confidence_ensemble(agent_decisions)
        else:
            result = self._voting_ensemble(agent_decisions)
        
        logger.info(f"✅ Ensemble decision: {result['decision']} (confidence: {result['confidence']:.2f})")
        return result
    
    def _voting_ensemble(self, decisions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Simple majority voting."""
        votes = {}
        
        for decision in decisions:
            action = decision.get('decision', 'HOLD')
            votes[action] = votes.get(action, 0) + 1
        
        # Get winner
        winner = max(votes.items(), key=lambda x: x[1])
        winning_action = winner[0]
        vote_count = winner[1]
        
        # Calculate confidence based on consensus
        confidence = vote_count / len(decisions)
        
        return {
            'decision': winning_action,
            'confidence': confidence,
            'method': 'voting',
            'votes': votes,
            'agents_count': len(decisions)
        }
    
    def _weighted_ensemble(self, decisions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Weighted voting based on agent performance."""
        weighted_votes = {}
        
        for decision in decisions:
            action = decision.get('decision', 'HOLD')
            agent_name = decision.get('agent', 'unknown')
            
            # Get weight for this agent (default 1.0)
            weight = self.agent_weights.get(agent_name, 1.0)
            
            weighted_votes[action] = weighted_votes.get(action, 0.0) + weight
        
        # Get winner
        if not weighted_votes:
            return {
                'decision': 'HOLD',
                'confidence': 0.5,
                'method': 'weighted',
                'agents_count': 0
            }
        
        winner = max(weighted_votes.items(), key=lambda x: x[1])
        winning_action = winner[0]
        total_weight = sum(weighted_votes.values())
        
        # Confidence based on weight share
        confidence = winner[1] / total_weight if total_weight > 0 else 0.5
        
        return {
            'decision': winning_action,
            'confidence': confidence,
            'method': 'weighted',
            'weighted_votes': weighted_votes,
            'agents_count': len(decisions)
        }
    
    def _confidence_ensemble(self, decisions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Confidence-weighted ensemble."""
        action_scores = {}
        
        for decision in decisions:
            action = decision.get('decision', 'HOLD')
            confidence = decision.get('confidence', 0.5)
            
            action_scores[action] = action_scores.get(action, 0.0) + confidence
        
        # Get winner
        if not action_scores:
            return {
                'decision': 'HOLD',
                'confidence': 0.5,
                'method': 'confidence',
                'agents_count': 0
            }
        
        winner = max(action_scores.items(), key=lambda x: x[1])
        winning_action = winner[0]
        total_score = sum(action_scores.values())
        
        # Normalize confidence
        confidence = winner[1] / total_score if total_score > 0 else 0.5
        
        return {
            'decision': winning_action,
            'confidence': min(confidence, 0.95),  # Cap at 0.95
            'method': 'confidence',
            'action_scores': action_scores,
            'agents_count': len(decisions)
        }
    
    def update_agent_weight(self, agent_name: str, performance: float):
        """
        Update agent weight based on performance.
        
        Args:
            agent_name: Name of agent
            performance: Performance metric (0-1, higher is better)
        """
        # Weight is 0.5 to 1.5 based on performance
        self.agent_weights[agent_name] = 0.5 + performance
        
        logger.debug(f"Updated weight for {agent_name}: {self.agent_weights[agent_name]:.2f}")
    
    def get_consensus_level(self, decisions: List[Dict[str, Any]]) -> float:
        """
        Calculate consensus level among agents (0-1).
        
        1.0 = all agents agree
        0.0 = complete disagreement
        """
        if len(decisions) <= 1:
            return 1.0
        
        actions = [d.get('decision', 'HOLD') for d in decisions]
        
        # Count most common action
        most_common_count = max([actions.count(a) for a in set(actions)])
        
        consensus = most_common_count / len(decisions)
        
        return consensus
