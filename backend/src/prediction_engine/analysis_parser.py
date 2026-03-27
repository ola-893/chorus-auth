"""
Conflict analysis parser for Gemini API responses.
"""
import logging
import re
from typing import Dict, List, Optional, Any
from datetime import datetime

from .interfaces import ConflictAnalysisParser as ConflictAnalysisParserInterface
from .models.core import ConflictAnalysis, EquilibriumSolution


logger = logging.getLogger(__name__)


class ConflictAnalysisParser(ConflictAnalysisParserInterface):
    """
    Parses Gemini API responses for conflict analysis and Nash equilibrium calculations.
    
    This class handles the structured parsing of Gemini API responses, validates
    the extracted data, and provides error handling for malformed responses.
    """
    
    def __init__(self):
        """Initialize the parser with regex patterns."""
        # Default pattern
        self.risk_score_pattern = re.compile(r"RISK_SCORE:\s*([\d\.eE\-\+]+)", re.IGNORECASE)
        self.confidence_pattern = re.compile(r"CONFIDENCE:\s*([\d\.eE\-\+]+)", re.IGNORECASE)
        self.affected_agents_pattern = re.compile(r'AFFECTED_AGENTS:\s*([^\n]+)', re.IGNORECASE)
        self.failure_mode_pattern = re.compile(r'FAILURE_MODE:\s*([^\n]+)', re.IGNORECASE)
        self.nash_equilibrium_pattern = re.compile(r'NASH_EQUILIBRIUM:\s*([^\n]+)', re.IGNORECASE)
        self.reasoning_pattern = re.compile(r'REASONING:\s*([^\n]+)', re.IGNORECASE)
        
        self.strategy_profile_pattern = re.compile(r'STRATEGY_PROFILE:\s*([^\n]+)', re.IGNORECASE)
        self.payoffs_pattern = re.compile(r'PAYOFFS:\s*([^\n]+)', re.IGNORECASE)
        self.stability_score_pattern = re.compile(r'STABILITY_SCORE:\s*([0-9]*\.?[0-9]+(?:[eE][+-]?[0-9]+)?)', re.IGNORECASE)
        self.equilibrium_type_pattern = re.compile(r'EQUILIBRIUM_TYPE:\s*([^\n]+)', re.IGNORECASE)
    
    def parse_conflict_analysis(self, response: str) -> ConflictAnalysis:
        """
        Parse conflict analysis response from Gemini API.
        
        Args:
            response: Raw response text from Gemini API.
            
        Returns:
            ConflictAnalysis object with parsed data.
            
        Raises:
            ValueError: If the response cannot be parsed or contains invalid data.
        """
        if not response or not response.strip():
            raise ValueError("Cannot parse empty or whitespace-only response")
        
        try:
            # Extract risk score (required)
            risk_score = self._extract_risk_score(response)
            
            # Extract confidence level (required)
            confidence_level = self._extract_confidence(response)
            
            # Extract affected agents (optional)
            affected_agents = self._extract_affected_agents(response)
            
            # Extract failure mode (optional)
            failure_mode = self._extract_failure_mode(response)
            
            # Extract Nash equilibrium info (optional)
            nash_equilibrium = self._extract_nash_equilibrium_info(response)
            
            # Log successful parsing
            logger.debug(f"Successfully parsed conflict analysis: risk={risk_score}, confidence={confidence_level}")
            
            return ConflictAnalysis(
                risk_score=risk_score,
                confidence_level=confidence_level,
                affected_agents=affected_agents,
                predicted_failure_mode=failure_mode,
                nash_equilibrium=nash_equilibrium,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Failed to parse conflict analysis response: {e}")
            logger.debug(f"Response content: {response[:500]}...")  # Log first 500 chars for debugging
            raise ValueError(f"Failed to parse conflict analysis response: {e}")
    
    def parse_nash_equilibrium(self, response: str) -> EquilibriumSolution:
        """
        Parse Nash equilibrium response from Gemini API.
        
        Args:
            response: Raw response text from Gemini API.
            
        Returns:
            EquilibriumSolution object with parsed data.
            
        Raises:
            ValueError: If the response cannot be parsed or contains invalid data.
        """
        if not response or not response.strip():
            raise ValueError("Cannot parse empty or whitespace-only response")
        
        try:
            # Extract strategy profile (required)
            strategy_profile = self._extract_strategy_profile(response)
            
            # Extract payoffs (required)
            payoffs = self._extract_payoffs(response)
            
            # Extract stability score (required)
            stability_score = self._extract_stability_score(response)
            
            # Log successful parsing
            logger.debug(f"Successfully parsed Nash equilibrium: stability={stability_score}, agents={len(strategy_profile)}")
            
            return EquilibriumSolution(
                strategy_profile=strategy_profile,
                payoffs=payoffs,
                stability_score=stability_score,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Failed to parse Nash equilibrium response: {e}")
            logger.debug(f"Response content: {response[:500]}...")  # Log first 500 chars for debugging
            raise ValueError(f"Failed to parse Nash equilibrium response: {e}")
    
    def _extract_risk_score(self, response: str) -> float:
        """Extract and validate risk score from response."""
        match = self.risk_score_pattern.search(response)
        if match:
            try:
                score = float(match.group(1))
                return max(0.0, min(1.0, score))
            except ValueError:
                pass
        
        # Fallback: look for just a float if no label found (less reliable)
        # Or maybe the prompt returns JSON?
        # For now, raise specific error
        raise ValueError("Risk score not found in response")
    
    def _extract_confidence(self, response: str) -> float:
        """Extract and validate confidence level from response."""
        match = self.confidence_pattern.search(response)
        if not match:
            logger.warning("Confidence level not found in response, using default 0.5")
            return 0.5
        
        try:
            confidence = float(match.group(1))
        except ValueError:
            logger.warning(f"Invalid confidence format: {match.group(1)}, using default 0.5")
            return 0.5
        
        # Validate range
        if not (0.0 <= confidence <= 1.0):
            logger.warning(f"Confidence {confidence} outside valid range [0.0, 1.0], clamping")
            confidence = max(0.0, min(1.0, confidence))
        
        return confidence
    
    def _extract_affected_agents(self, response: str) -> List[str]:
        """Extract affected agents list from response."""
        match = self.affected_agents_pattern.search(response)
        if not match:
            logger.debug("Affected agents not found in response")
            return []
        
        agents_str = match.group(1).strip()
        
        # Handle "none" case
        if agents_str.lower() in ['none', 'null', 'empty', '']:
            return []
        
        # Parse comma-separated list
        try:
            agents = [agent.strip() for agent in agents_str.split(',')]
            # Filter out empty strings
            agents = [agent for agent in agents if agent]
            return agents
        except Exception as e:
            logger.warning(f"Failed to parse affected agents '{agents_str}': {e}")
            return []
    
    def _extract_failure_mode(self, response: str) -> str:
        """Extract failure mode description from response."""
        match = self.failure_mode_pattern.search(response)
        if not match:
            logger.debug("Failure mode not found in response")
            return "Unknown failure mode"
        
        failure_mode = match.group(1).strip()
        return failure_mode if failure_mode else "Unknown failure mode"
    
    def _extract_nash_equilibrium_info(self, response: str) -> Optional[Dict[str, Any]]:
        """Extract Nash equilibrium information from response."""
        match = self.nash_equilibrium_pattern.search(response)
        if not match:
            logger.debug("Nash equilibrium info not found in response")
            return None
        
        equilibrium_str = match.group(1).strip()
        
        # Handle "none", "unstable", etc.
        if equilibrium_str.lower() in ['none', 'unstable', 'null', 'unknown']:
            return {"status": equilibrium_str.lower()}
        
        # For now, just store as a description
        # This could be enhanced to parse more structured data
        return {"description": equilibrium_str}
    
    def _extract_strategy_profile(self, response: str) -> Dict[str, str]:
        """Extract strategy profile from response."""
        match = self.strategy_profile_pattern.search(response)
        if not match:
            raise ValueError("Strategy profile not found in response")
        
        profile_str = match.group(1).strip()
        
        try:
            # Parse "agent_id:strategy" pairs
            profile = {}
            pairs = profile_str.split(',')
            
            for pair in pairs:
                pair = pair.strip()
                if ':' not in pair:
                    continue
                
                agent_id, strategy = pair.split(':', 1)
                agent_id = agent_id.strip()
                strategy = strategy.strip()
                
                if agent_id and strategy:
                    profile[agent_id] = strategy
            
            if not profile:
                raise ValueError("No valid agent:strategy pairs found")
            
            return profile
            
        except Exception as e:
            raise ValueError(f"Failed to parse strategy profile '{profile_str}': {e}")
    
    def _extract_payoffs(self, response: str) -> Dict[str, float]:
        """Extract payoffs from response."""
        match = self.payoffs_pattern.search(response)
        if not match:
            raise ValueError("Payoffs not found in response")
        
        payoffs_str = match.group(1).strip()
        
        try:
            # Parse "agent_id:payoff" pairs
            payoffs = {}
            pairs = payoffs_str.split(',')
            
            for pair in pairs:
                pair = pair.strip()
                if ':' not in pair:
                    continue
                
                agent_id, payoff_str = pair.split(':', 1)
                agent_id = agent_id.strip()
                payoff_str = payoff_str.strip()
                
                if agent_id and payoff_str:
                    try:
                        payoff = float(payoff_str)
                        payoffs[agent_id] = payoff
                    except ValueError:
                        logger.warning(f"Invalid payoff value for {agent_id}: {payoff_str}")
                        continue
            
            if not payoffs:
                raise ValueError("No valid agent:payoff pairs found")
            
            return payoffs
            
        except Exception as e:
            raise ValueError(f"Failed to parse payoffs '{payoffs_str}': {e}")
    
    def _extract_stability_score(self, response: str) -> float:
        """Extract and validate stability score from response."""
        match = self.stability_score_pattern.search(response)
        if not match:
            raise ValueError("Stability score not found in response")
        
        try:
            stability_score = float(match.group(1))
        except ValueError:
            raise ValueError(f"Invalid stability score format: {match.group(1)}")
        
        # Validate range
        if not (0.0 <= stability_score <= 1.0):
            logger.warning(f"Stability score {stability_score} outside valid range [0.0, 1.0], clamping")
            stability_score = max(0.0, min(1.0, stability_score))
        
        return stability_score
    
    def validate_response_format(self, response: str, response_type: str = "conflict") -> bool:
        """
        Validate that a response contains the expected format markers.
        
        Args:
            response: Response text to validate.
            response_type: Type of response ("conflict" or "equilibrium").
            
        Returns:
            True if response appears to be in the expected format.
        """
        if not response or not response.strip():
            return False
        
        if response_type == "conflict":
            # Check for required fields
            has_risk_score = bool(self.risk_score_pattern.search(response))
            return has_risk_score
        
        elif response_type == "equilibrium":
            # Check for required fields
            has_strategy = bool(self.strategy_profile_pattern.search(response))
            has_payoffs = bool(self.payoffs_pattern.search(response))
            has_stability = bool(self.stability_score_pattern.search(response))
            return has_strategy and has_payoffs and has_stability
        
        return False