"""
Game theory prompt builder for Gemini API interactions.
"""
import logging
from typing import List, Dict, Any
from datetime import datetime

from ..interfaces import GameTheoryPromptBuilder as GameTheoryPromptBuilderInterface
from ..models.core import AgentIntention, GameState


logger = logging.getLogger(__name__)


class GameTheoryPromptBuilder(GameTheoryPromptBuilderInterface):
    """
    Builds structured prompts for game theory analysis using Gemini API.
    
    This class formats agent intentions and game states into prompts that
    guide the Gemini API to perform conflict analysis and Nash equilibrium
    calculations using game theory principles.
    """
    
    def __init__(self):
        """Initialize the prompt builder."""
        self.conflict_template = self._load_conflict_template()
        self.equilibrium_template = self._load_equilibrium_template()
    
    def build_conflict_analysis_prompt(self, intentions: List[AgentIntention]) -> str:
        """
        Build a prompt for conflict analysis.
        
        Args:
            intentions: List of agent intentions to analyze for conflicts.
            
        Returns:
            Formatted prompt string for Gemini API.
            
        Raises:
            ValueError: If intentions list is empty or contains invalid data.
        """
        if not intentions:
            raise ValueError("Cannot build conflict analysis prompt with empty intentions list")
        
        # Validate agent intentions
        for intention in intentions:
            self._validate_agent_intention(intention)
        
        # Group intentions by resource type for better analysis
        resource_groups = self._group_intentions_by_resource(intentions)
        
        # Build the prompt using the template
        prompt = self.conflict_template.format(
            scenario_description=self._build_scenario_description(intentions),
            resource_analysis=self._build_resource_analysis(resource_groups),
            agent_profiles=self._build_agent_profiles(intentions),
            game_theory_context=self._build_game_theory_context(intentions),
            output_format=self._get_conflict_output_format()
        )
        
        logger.debug(f"Built conflict analysis prompt for {len(intentions)} intentions")
        return prompt
    
    def build_nash_equilibrium_prompt(self, game_state: GameState) -> str:
        """
        Build a prompt for Nash equilibrium calculation.
        
        Args:
            game_state: Current game state to analyze.
            
        Returns:
            Formatted prompt string for Gemini API.
            
        Raises:
            ValueError: If game_state is invalid or incomplete.
        """
        if not game_state.agents:
            raise ValueError("Cannot build equilibrium prompt with empty agents list")
        
        if not game_state.intentions:
            raise ValueError("Cannot build equilibrium prompt with empty intentions list")
        
        # Validate game state
        self._validate_game_state(game_state)
        
        # Build the prompt using the template
        prompt = self.equilibrium_template.format(
            game_setup=self._build_game_setup(game_state),
            player_strategies=self._build_player_strategies(game_state),
            payoff_matrix=self._build_payoff_matrix_description(game_state),
            equilibrium_context=self._build_equilibrium_context(game_state),
            output_format=self._get_equilibrium_output_format()
        )
        
        logger.debug(f"Built Nash equilibrium prompt for {len(game_state.agents)} agents")
        return prompt
    
    def _validate_agent_intention(self, intention: AgentIntention) -> None:
        """Validate an agent intention structure."""
        if not intention.agent_id:
            raise ValueError("Agent intention must have a valid agent_id")
        
        if not intention.resource_type:
            raise ValueError("Agent intention must have a valid resource_type")
        
        if intention.requested_amount <= 0:
            raise ValueError("Agent intention must have a positive requested_amount")
        
        if intention.priority_level < 0:
            raise ValueError("Agent intention priority_level cannot be negative")
    
    def _validate_game_state(self, game_state: GameState) -> None:
        """Validate a game state structure."""
        if not all(isinstance(agent, str) and agent.strip() for agent in game_state.agents):
            raise ValueError("All agents must be non-empty strings")
        
        if not isinstance(game_state.resources, dict):
            raise ValueError("Game state resources must be a dictionary")
        
        for resource, amount in game_state.resources.items():
            if not isinstance(amount, int) or amount < 0:
                raise ValueError(f"Resource {resource} must have a non-negative integer amount")
    
    def _group_intentions_by_resource(self, intentions: List[AgentIntention]) -> Dict[str, List[AgentIntention]]:
        """Group intentions by resource type."""
        groups = {}
        for intention in intentions:
            resource_type = intention.resource_type
            if resource_type not in groups:
                groups[resource_type] = []
            groups[resource_type].append(intention)
        return groups
    
    def _build_scenario_description(self, intentions: List[AgentIntention]) -> str:
        """Build a description of the current scenario."""
        agent_count = len(set(i.agent_id for i in intentions))
        resource_types = set(i.resource_type for i in intentions)
        
        description = f"""
You are analyzing a multi-agent system with {agent_count} autonomous agents competing for shared resources.
The agents are requesting access to {len(resource_types)} different resource types: {', '.join(sorted(resource_types))}.
Each agent operates independently and makes decisions based on their own objectives and priorities.
        """.strip()
        
        return description
    
    def _build_resource_analysis(self, resource_groups: Dict[str, List[AgentIntention]]) -> str:
        """Build analysis of resource contention."""
        analysis = "Resource Contention Analysis:\n"
        
        for resource_type, intentions in resource_groups.items():
            total_demand = sum(i.requested_amount for i in intentions)
            agent_count = len(intentions)
            avg_priority = sum(i.priority_level for i in intentions) / len(intentions)
            
            analysis += f"""
- {resource_type.upper()}: {agent_count} agents competing
  * Total demand: {total_demand} units
  * Average priority: {avg_priority:.1f}
  * Agents: {', '.join(i.agent_id for i in intentions)}
            """.strip() + "\n"
        
        return analysis
    
    def _build_agent_profiles(self, intentions: List[AgentIntention]) -> str:
        """Build profiles of each agent's behavior."""
        agent_data = {}
        
        # Aggregate data per agent
        for intention in intentions:
            agent_id = intention.agent_id
            if agent_id not in agent_data:
                agent_data[agent_id] = {
                    'resources': [],
                    'total_demand': 0,
                    'avg_priority': 0,
                    'priorities': []
                }
            
            agent_data[agent_id]['resources'].append(f"{intention.resource_type}({intention.requested_amount})")
            agent_data[agent_id]['total_demand'] += intention.requested_amount
            agent_data[agent_id]['priorities'].append(intention.priority_level)
        
        # Build profiles
        profiles = "Agent Behavioral Profiles:\n"
        for agent_id, data in agent_data.items():
            avg_priority = sum(data['priorities']) / len(data['priorities'])
            profiles += f"""
- Agent {agent_id}:
  * Resources requested: {', '.join(data['resources'])}
  * Total demand: {data['total_demand']} units
  * Average priority: {avg_priority:.1f}
  * Aggressiveness: {'High' if avg_priority > 7 else 'Medium' if avg_priority > 4 else 'Low'}
            """.strip() + "\n"
        
        return profiles
    
    def _build_game_theory_context(self, intentions: List[AgentIntention]) -> str:
        """Build game theory context for analysis."""
        context = """
Game Theory Analysis Framework:
- Model this as a non-cooperative game where agents act independently
- Consider resource scarcity and competition dynamics
- Analyze potential Nash equilibria and their stability
- Evaluate the likelihood of coordination failures
- Assess the risk of cascading failures if conflicts escalate
- Consider the impact of agent priorities on strategic behavior
        """.strip()
        
        return context
    
    def _build_game_setup(self, game_state: GameState) -> str:
        """Build game setup description for equilibrium analysis."""
        setup = f"""
Game Setup:
- Players: {len(game_state.agents)} autonomous agents ({', '.join(game_state.agents)})
- Resources: {len(game_state.resources)} shared resource pools
- Time: {game_state.timestamp.strftime('%Y-%m-%d %H:%M:%S')}

Resource Availability:
        """.strip()
        
        for resource, amount in game_state.resources.items():
            setup += f"\n- {resource}: {amount} units available"
        
        return setup
    
    def _build_player_strategies(self, game_state: GameState) -> str:
        """Build description of player strategies."""
        strategies = "Player Strategy Options:\n"
        
        for agent in game_state.agents:
            agent_intentions = [i for i in game_state.intentions if i.agent_id == agent]
            
            if agent_intentions:
                strategies += f"""
- Agent {agent}:
  * COOPERATE: Request resources at normal priority, respect other agents
  * COMPETE: Increase priority to secure resources, potentially blocking others
  * DEFECT: Maximum priority requests, aggressive resource acquisition
                """.strip() + "\n"
            else:
                strategies += f"\n- Agent {agent}: No current resource requests (IDLE strategy)"
        
        return strategies
    
    def _build_payoff_matrix_description(self, game_state: GameState) -> str:
        """Build description of the payoff structure."""
        description = """
Payoff Structure:
- Successful resource acquisition: +1 point per unit obtained
- Resource denial (blocked by others): -0.5 points per unit denied
- Cooperation bonus: +0.2 points when multiple agents cooperate
- Defection penalty: -0.3 points when defecting against cooperators
- System stability bonus: +0.1 points when system remains stable
        """.strip()
        
        return description
    
    def _build_equilibrium_context(self, game_state: GameState) -> str:
        """Build context for equilibrium calculation."""
        context = """
Nash Equilibrium Analysis:
- Find strategy profiles where no agent can unilaterally improve their payoff
- Consider both pure and mixed strategy equilibria
- Evaluate equilibrium stability and likelihood of convergence
- Assess the social optimality of equilibrium outcomes
- Identify potential coordination problems and their solutions
        """.strip()
        
        return context
    
    def _get_conflict_output_format(self) -> str:
        """Get the required output format for conflict analysis."""
        return """
REQUIRED OUTPUT FORMAT:
RISK_SCORE: [decimal between 0.0 and 1.0]
CONFIDENCE: [decimal between 0.0 and 1.0]
AFFECTED_AGENTS: [comma-separated list of agent IDs, or "none"]
FAILURE_MODE: [brief description of predicted failure scenario]
NASH_EQUILIBRIUM: [brief description of predicted equilibrium, or "unstable"]
REASONING: [explanation of the analysis and risk assessment]

Example:
RISK_SCORE: 0.75
CONFIDENCE: 0.85
AFFECTED_AGENTS: agent_1, agent_3
FAILURE_MODE: Resource deadlock leading to system stall
NASH_EQUILIBRIUM: Competitive equilibrium with suboptimal resource allocation
REASONING: High contention for CPU resources with conflicting priorities creates deadlock risk
        """.strip()
    
    def _get_equilibrium_output_format(self) -> str:
        """Get the required output format for equilibrium calculation."""
        return """
REQUIRED OUTPUT FORMAT:
STRATEGY_PROFILE: [agent_id:strategy pairs, comma-separated]
PAYOFFS: [agent_id:payoff pairs, comma-separated]
STABILITY_SCORE: [decimal between 0.0 and 1.0]
EQUILIBRIUM_TYPE: [pure, mixed, or none]
REASONING: [explanation of the equilibrium analysis]

Example:
STRATEGY_PROFILE: agent_1:cooperate, agent_2:compete, agent_3:cooperate
PAYOFFS: agent_1:0.7, agent_2:0.4, agent_3:0.6
STABILITY_SCORE: 0.8
EQUILIBRIUM_TYPE: pure
REASONING: Stable equilibrium where cooperation dominates due to resource abundance
        """.strip()
    
    def _load_conflict_template(self) -> str:
        """Load the conflict analysis prompt template."""
        return """
{scenario_description}

{resource_analysis}

{agent_profiles}

{game_theory_context}

TASK: Analyze this multi-agent scenario for potential conflicts using game theory principles. 
Focus on identifying situations that could lead to cascading failures, resource deadlocks, 
or system instability. Consider the strategic interactions between agents and the likelihood 
of coordination failures.

{output_format}
        """.strip()
    
    def _load_equilibrium_template(self) -> str:
        """Load the Nash equilibrium prompt template."""
        return """
{game_setup}

{player_strategies}

{payoff_matrix}

{equilibrium_context}

TASK: Calculate the Nash equilibrium for this multi-agent resource allocation game. 
Determine the optimal strategy profile where no agent can unilaterally improve their 
outcome. Consider both the stability and efficiency of the equilibrium.

{output_format}
        """.strip()