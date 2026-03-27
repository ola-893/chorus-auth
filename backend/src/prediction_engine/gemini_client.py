"""
Gemini API client implementation for conflict prediction.
"""
import logging
import hashlib
import json
import time
from typing import List, Optional
import google.genai as genai
from google.genai.errors import APIError, ClientError, ServerError

from .interfaces import GeminiClient as GeminiClientInterface
from .models.core import AgentIntention, ConflictAnalysis, GameState, EquilibriumSolution
from .game_theory.prompt_builder import GameTheoryPromptBuilder
from .analysis_parser import ConflictAnalysisParser
from src.config import settings
from src.logging_config import get_agent_logger
from src.error_handling import (
    handle_gemini_api_errors, 
    retry_with_exponential_backoff,
    gemini_circuit_breaker,
    system_recovery_context
)
from src.integrations.datadog_client import datadog_client
from src.prediction_engine.redis_client import RedisClient


logger = logging.getLogger(__name__)
agent_logger = get_agent_logger(__name__)


class GeminiClient(GeminiClientInterface):
    """
    Google Gemini API client for game theory conflict analysis.
    
    Handles authentication, connection testing, and error handling for
    interactions with the Gemini 3 Pro API.
    """
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize the Gemini client.
        
        Args:
            api_key: Gemini API key. If None, uses GEMINI_API_KEY from config.
            model: Model name. If None, uses gemini-3-pro-preview from config.
        """
        self.api_key = api_key or settings.gemini.api_key
        self.model = model or settings.gemini.model
        self._client = None
        self.prompt_builder = GameTheoryPromptBuilder()
        self.parser = ConflictAnalysisParser()
        self.redis = None
        
        try:
            self.redis = RedisClient()
        except Exception as e:
            logger.warning(f"Redis unavailable for Gemini caching: {e}")
            
        self._initialize_client()
    
    def _initialize_client(self) -> None:
        """Initialize the Gemini client with authentication."""
        try:
            # Try the newer API first
            try:
                self._client = genai.Client(api_key=self.api_key)
                agent_logger.log_agent_action(
                    "INFO",
                    "Gemini client initialized with newer API",
                    action_type="gemini_client_init",
                    context={"api_type": "newer", "model": self.model}
                )
            except AttributeError:
                # Fallback to older API if available
                genai.configure(api_key=self.api_key)
                self._client = genai.GenerativeModel(self.model)
                agent_logger.log_agent_action(
                    "INFO",
                    "Gemini client initialized with fallback API",
                    action_type="gemini_client_init",
                    context={"api_type": "fallback", "model": self.model}
                )
        except Exception as e:
            agent_logger.log_system_error(
                e,
                component="gemini_client",
                operation="initialize_client",
                context={"model": self.model}
            )
            raise
    
    def test_connection(self) -> bool:
        """
        Test the connection to the Gemini API.
        
        Returns:
            True if connection is successful, False otherwise.
        """
        try:
            # Simple test prompt to verify API connectivity
            test_prompt = "Test connection. Respond with 'OK'."
            
            # Handle different client types
            if hasattr(self._client, 'models'):
                # Newer API - test by listing models
                try:
                    models = self._client.models.list()
                    first_model = next(iter(models), None)
                    if first_model:
                        logger.info(f"Gemini API connection test successful (newer API), found model: {first_model.name}")
                        return True
                    else:
                        logger.info("Gemini API connection test successful (newer API, empty model list)")
                        return True
                except Exception as e:
                    logger.warning(f"Gemini models.list() failed: {e}, trying generation...")
                    # Try generation as fallback
                    try:
                        response = self._client.models.generate_content(
                            model="gemini-2.0-flash-exp",
                            contents=test_prompt
                        )
                        if response and hasattr(response, 'text') and response.text:
                            logger.info("Gemini API connection test successful (newer API via generation)")
                            return True
                    except Exception as gen_e:
                        logger.warning(f"Gemini generation fallback failed: {gen_e}")
            elif hasattr(self._client, 'generate_content'):
                response = self._client.generate_content(test_prompt)
                if response and hasattr(response, 'text') and response.text:
                    logger.info("Gemini API connection test successful")
                    return True
            
            logger.warning("Gemini API connection test failed - no valid response")
            return False
                
        except (ClientError, ServerError) as e:
            logger.error(f"Gemini API connection error: {e}")
            return False
        except APIError as e:
            logger.error(f"Gemini API error during connection test: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during connection test: {e}")
            return False
    
    @gemini_circuit_breaker
    @retry_with_exponential_backoff(max_retries=3, exceptions=(genai.errors.ClientError, genai.errors.ServerError))
    @handle_gemini_api_errors
    def analyze_conflict_risk(self, agent_intentions: List[AgentIntention]) -> ConflictAnalysis:
        """
        Analyze conflict risk using game theory.
        
        Args:
            agent_intentions: List of agent intentions to analyze.
            
        Returns:
            ConflictAnalysis with risk score and predictions.
            
        Raises:
            APIError: If the Gemini API returns an error.
            ClientError/ServerError: If there's a connection issue.
            ValueError: If the response cannot be parsed.
        """
        if not agent_intentions:
            raise ValueError("Cannot analyze conflict risk with empty intentions list")
        
        try:
            # Build the prompt using GameTheoryPromptBuilder
            prompt = self.prompt_builder.build_conflict_analysis_prompt(agent_intentions)
            
            # Check cache
            if self.redis:
                try:
                    cache_key = f"gemini:conflict:{hashlib.md5(prompt.encode()).hexdigest()}"
                    cached_response = self.redis.get(cache_key)
                    if cached_response:
                        logger.info("Cache hit for conflict analysis")
                        analysis = self.parser.parse_conflict_analysis(cached_response)
                        # We need to update timestamp for cached result to be current
                        from datetime import datetime
                        analysis.timestamp = datetime.now()
                        return analysis
                except Exception as e:
                    logger.warning(f"Cache lookup failed: {e}")
            
            # Start timer
            start_time = time.time()
            
            # Handle different client types
            if hasattr(self._client, 'models'):
                response = self._client.models.generate_content(
                    model=self.model,
                    contents=prompt
                )
            else:
                response = self._client.generate_content(prompt)
                
            latency_ms = (time.time() - start_time) * 1000
            
            if not response or not response.text:
                raise ValueError("Empty response from Gemini API")
            
            # Extract and track LLM usage metadata
            try:
                prompt_tokens = 0
                completion_tokens = 0
                finish_reason = "unknown"
                
                # Check for usage metadata
                if hasattr(response, 'usage_metadata'):
                    prompt_tokens = getattr(response.usage_metadata, 'prompt_token_count', 0)
                    completion_tokens = getattr(response.usage_metadata, 'candidates_token_count', 0)
                
                # Check for finish reason
                if hasattr(response, 'candidates') and response.candidates:
                     # Accessing the first candidate safely
                     candidate = response.candidates[0]
                     if hasattr(candidate, 'finish_reason'):
                         finish_reason = str(candidate.finish_reason)

                datadog_client.track_llm_usage(
                    model=self.model,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    latency_ms=latency_ms,
                    finish_reason=finish_reason
                )
            except Exception as e:
                logger.warning(f"Failed to extract/send LLM metrics to Datadog: {e}")

            # Parse the response using ConflictAnalysisParser
            analysis = self.parser.parse_conflict_analysis(response.text)
            
            # Cache the raw text response
            if self.redis:
                try:
                    # Cache for 1 hour
                    self.redis.set(cache_key, response.text, ttl=3600)
                except Exception as e:
                    logger.warning(f"Cache write failed: {e}")
            
            # Emit conflict prediction event
            try:
                from src.event_bus import event_bus
                conflict_id = f"conflict_{analysis.timestamp.strftime('%Y%m%d_%H%M%S')}"
                
                event_bus.publish("conflict_prediction", {
                    "type": "conflict_prediction",
                    "conflict_id": conflict_id,
                    "risk_score": analysis.risk_score,
                    "affected_agents": analysis.affected_agents,
                    "agent_count": len(agent_intentions),
                    "timestamp": analysis.timestamp.isoformat()
                })
            except Exception as e:
                # Don't fail conflict analysis if event emission fails
                logger.warning(f"Failed to emit conflict prediction event: {e}")
            
            # Send observability data to Datadog
            try:
                datadog_client.track_conflict_prediction(
                    conflict_id=f"conflict_{analysis.timestamp.strftime('%Y%m%d_%H%M%S')}",
                    risk_score=analysis.risk_score,
                    affected_agents=analysis.affected_agents
                )
                
                # Send metrics for analysis performance
                datadog_client.send_metric(
                    "chorus.gemini.analysis_success",
                    1.0,
                    tags=[f"agent_count:{len(agent_intentions)}"],
                    metric_type="count"
                )
                
            except Exception as e:
                # Don't fail conflict analysis if observability fails
                logger.warning(f"Failed to send conflict prediction metrics to Datadog: {e}")
            
            return analysis
            
        except (ClientError, ServerError, APIError, Exception) as e:
            # Send error metrics to Datadog
            try:
                datadog_client.send_metric(
                    "chorus.gemini.analysis_error",
                    1.0,
                    tags=[f"error_type:exception", f"agent_count:{len(agent_intentions)}"],
                    metric_type="count"
                )
            except Exception:
                pass
            
            logger.error(f"Gemini API failure: {e}. Attempting rule-based fallback.")
            
            # Execute rule-based fallback
            return self._rule_based_conflict_analysis(agent_intentions)

    def _rule_based_conflict_analysis(self, agent_intentions: List[AgentIntention]) -> ConflictAnalysis:
                """
                Fallback method to analyze conflict risk using simple heuristics when API is down.
                """
                from datetime import datetime
                
                # Simple heuristic: if multiple agents want the same resource, risk is high
                resource_counts = {}
                for intention in agent_intentions:
                    res = intention.resource_type
                    resource_counts[res] = resource_counts.get(res, 0) + 1
                    
                max_contention = max(resource_counts.values()) if resource_counts else 0
                
                if max_contention > 2:
                    risk_score = 0.8
                    failure_mode = "High resource contention (Fallback detection)"
                elif max_contention > 1:
                    risk_score = 0.5
                    failure_mode = "Moderate resource contention (Fallback detection)"
                else:
                    risk_score = 0.1
                    failure_mode = "Low risk (Fallback detection)"
                    
                return ConflictAnalysis(
                    risk_score=risk_score,
                    confidence_level=0.5, # Lower confidence for fallback
                    affected_agents=[i.agent_id for i in agent_intentions],
                    predicted_failure_mode=failure_mode,
                    nash_equilibrium=None,
                    timestamp=datetime.now()
                )
        
    def calculate_nash_equilibrium(self, game_state: GameState) -> EquilibriumSolution:
        """
        Calculate Nash equilibrium for the given game state.
        
        Args:
            game_state: Current game state to analyze.
            
        Returns:
            EquilibriumSolution with strategy profile and payoffs.
            
        Raises:
            APIError: If the Gemini API returns an error.
            ClientError/ServerError: If there's a connection issue.
            ValueError: If the response cannot be parsed.
        """
        try:
            # Build the prompt using GameTheoryPromptBuilder
            prompt = self.prompt_builder.build_nash_equilibrium_prompt(game_state)
            
            response = self._client.generate_content(prompt)
            
            if not response or not response.text:
                raise ValueError("Empty response from Gemini API")
            
            # Parse the response using ConflictAnalysisParser
            return self.parser.parse_nash_equilibrium(response.text)
            
        except (ClientError, ServerError) as e:
            logger.error(f"Gemini API connection error during equilibrium calculation: {e}")
            raise
        except APIError as e:
            logger.error(f"Gemini API error during equilibrium calculation: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during equilibrium calculation: {e}")
            raise
    
