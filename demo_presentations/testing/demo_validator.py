#!/usr/bin/env python3
"""
Demo Validator - Chorus Multi-Agent Immune System
Pre-demo validation and reliability testing

This script validates system readiness before live demonstrations
and provides confidence metrics for demo success.
"""

import asyncio
import sys
import os
import time
import json
from datetime import datetime
from typing import Dict, List, Tuple

# Add backend src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend', 'src'))

from prediction_engine.gemini_client import GeminiClient
from prediction_engine.redis_client import RedisClient
from prediction_engine.trust_manager import TrustManager
from prediction_engine.intervention_engine import InterventionEngine
from prediction_engine.simulator import AgentSimulator
from config import Config

class DemoValidator:
    """Comprehensive demo validation and reliability testing."""
    
    def __init__(self):
        self.config = Config()
        self.validation_results = {
            'overall_score': 0,
            'component_scores': {},
            'performance_metrics': {},
            'reliability_assessment': {},
            'recommendations': []
        }
        
        # Validation thresholds
        self.thresholds = {
            'gemini_latency_ms': 100,  # Max acceptable latency
            'redis_latency_ms': 10,    # Max Redis response time
            'trust_update_ms': 50,     # Max trust update time
            'intervention_ms': 1000,   # Max intervention time
            'system_reliability': 95   # Min reliability percentage
        }
    
    async def validate_redis_connection(self) -> Tuple[bool, Dict]:
        """Validate Redis connection and performance."""
        print("📊 Validating Redis connection...")
        
        try:
            redis_client = RedisClient()
            
            # Test connection
            start_time = time.time()
            await redis_client.connect()
            connection_time = (time.time() - start_time) * 1000
            
            # Test basic operations
            start_time = time.time()
            await redis_client.set("demo_test_key", "demo_test_value")
            set_time = (time.time() - start_time) * 1000
            
            start_time = time.time()
            value = await redis_client.get("demo_test_key")
            get_time = (time.time() - start_time) * 1000
            
            # Clean up
            await redis_client.delete("demo_test_key")
            await redis_client.disconnect()
            
            # Get Redis info
            await redis_client.connect()
            redis_info = await redis_client.get_info()
            await redis_client.disconnect()
            
            avg_latency = (set_time + get_time) / 2
            
            result = {
                'connected': True,
                'connection_time_ms': connection_time,
                'avg_operation_latency_ms': avg_latency,
                'redis_version': redis_info.get('redis_version', 'unknown'),
                'memory_usage': redis_info.get('used_memory_human', 'unknown'),
                'performance_score': 100 if avg_latency < self.thresholds['redis_latency_ms'] else 70
            }
            
            print(f"   ✅ Redis connected ({connection_time:.1f}ms)")
            print(f"   ⚡ Avg latency: {avg_latency:.1f}ms")
            print(f"   📊 Version: {result['redis_version']}")
            
            return True, result
            
        except Exception as e:
            print(f"   ❌ Redis validation failed: {e}")
            return False, {'connected': False, 'error': str(e), 'performance_score': 0}
    
    async def validate_gemini_integration(self) -> Tuple[bool, Dict]:
        """Validate Gemini AI integration and performance."""
        print("🧠 Validating Gemini AI integration...")
        
        try:
            gemini_client = GeminiClient()
            
            # Test connection
            connection_test = await gemini_client.test_connection()
            if not connection_test:
                print(f"   ❌ Gemini connection failed")
                return False, {'connected': False, 'performance_score': 0}
            
            # Test prediction performance
            latencies = []
            success_count = 0
            
            for i in range(3):
                try:
                    start_time = time.time()
                    analysis = await gemini_client.analyze_conflict_potential(
                        agent_ids=[f"test_agent_{j}" for j in range(3)],
                        context=f"Test scenario {i+1}: Resource contention validation test"
                    )
                    latency = (time.time() - start_time) * 1000
                    latencies.append(latency)
                    
                    if analysis and hasattr(analysis, 'risk_score'):
                        success_count += 1
                    
                except Exception as e:
                    print(f"   ⚠️  Test {i+1} failed: {e}")
            
            if not latencies:
                print(f"   ❌ All Gemini tests failed")
                return False, {'connected': True, 'performance_score': 0}
            
            avg_latency = sum(latencies) / len(latencies)
            success_rate = (success_count / 3) * 100
            
            performance_score = 100
            if avg_latency > self.thresholds['gemini_latency_ms']:
                performance_score -= 30
            if success_rate < 100:
                performance_score -= (100 - success_rate)
            
            result = {
                'connected': True,
                'avg_latency_ms': avg_latency,
                'success_rate': success_rate,
                'test_count': len(latencies),
                'performance_score': max(0, performance_score)
            }
            
            print(f"   ✅ Gemini connected")
            print(f"   ⚡ Avg latency: {avg_latency:.1f}ms")
            print(f"   📊 Success rate: {success_rate:.1f}%")
            
            return True, result
            
        except Exception as e:
            print(f"   ❌ Gemini validation failed: {e}")
            return False, {'connected': False, 'error': str(e), 'performance_score': 0}
    
    async def validate_trust_management(self) -> Tuple[bool, Dict]:
        """Validate trust management system performance."""
        print("🛡️  Validating trust management system...")
        
        try:
            redis_client = RedisClient()
            await redis_client.connect()
            
            trust_manager = TrustManager(redis_client)
            
            # Test trust score operations
            test_agent_id = "validation_test_agent"
            latencies = []
            
            # Test set operation
            start_time = time.time()
            await trust_manager.set_trust_score(test_agent_id, 100)
            set_latency = (time.time() - start_time) * 1000
            latencies.append(set_latency)
            
            # Test get operation
            start_time = time.time()
            score = await trust_manager.get_trust_score(test_agent_id)
            get_latency = (time.time() - start_time) * 1000
            latencies.append(get_latency)
            
            # Test update operation
            start_time = time.time()
            await trust_manager.update_trust_score(test_agent_id, -10, "Validation test")
            update_latency = (time.time() - start_time) * 1000
            latencies.append(update_latency)
            
            # Verify final score
            final_score = await trust_manager.get_trust_score(test_agent_id)
            
            # Clean up
            await redis_client.delete(f"trust_score:{test_agent_id}")
            await redis_client.disconnect()
            
            avg_latency = sum(latencies) / len(latencies)
            
            # Validate correctness
            score_correct = (score == 100)
            final_score_correct = (final_score == 90)
            
            performance_score = 100
            if avg_latency > self.thresholds['trust_update_ms']:
                performance_score -= 30
            if not (score_correct and final_score_correct):
                performance_score -= 50
            
            result = {
                'avg_latency_ms': avg_latency,
                'operations_tested': len(latencies),
                'score_accuracy': score_correct and final_score_correct,
                'performance_score': max(0, performance_score)
            }
            
            print(f"   ✅ Trust management operational")
            print(f"   ⚡ Avg latency: {avg_latency:.1f}ms")
            print(f"   📊 Score accuracy: {'✅' if result['score_accuracy'] else '❌'}")
            
            return True, result
            
        except Exception as e:
            print(f"   ❌ Trust management validation failed: {e}")
            return False, {'error': str(e), 'performance_score': 0}
    
    async def validate_intervention_system(self) -> Tuple[bool, Dict]:
        """Validate intervention system performance."""
        print("🚫 Validating intervention system...")
        
        try:
            redis_client = RedisClient()
            await redis_client.connect()
            
            trust_manager = TrustManager(redis_client)
            intervention_engine = InterventionEngine(
                trust_manager=trust_manager,
                redis_client=redis_client
            )
            
            # Test intervention operations
            test_agent_id = "validation_intervention_agent"
            
            # Set up test agent
            await trust_manager.set_trust_score(test_agent_id, 100)
            
            # Test quarantine operation
            start_time = time.time()
            quarantine_success = await intervention_engine.quarantine_agent(
                agent_id=test_agent_id,
                reason="Validation test quarantine",
                confidence=0.95
            )
            quarantine_latency = (time.time() - start_time) * 1000
            
            # Test quarantine status check
            quarantined_agents = await intervention_engine.get_quarantined_agents()
            is_quarantined = test_agent_id in quarantined_agents
            
            # Clean up
            await redis_client.delete(f"quarantine:{test_agent_id}")
            await redis_client.delete(f"trust_score:{test_agent_id}")
            await redis_client.disconnect()
            
            performance_score = 100
            if quarantine_latency > self.thresholds['intervention_ms']:
                performance_score -= 30
            if not quarantine_success:
                performance_score -= 40
            if not is_quarantined:
                performance_score -= 30
            
            result = {
                'quarantine_latency_ms': quarantine_latency,
                'quarantine_success': quarantine_success,
                'status_check_accurate': is_quarantined,
                'performance_score': max(0, performance_score)
            }
            
            print(f"   ✅ Intervention system operational")
            print(f"   ⚡ Quarantine latency: {quarantine_latency:.1f}ms")
            print(f"   📊 Operations successful: {'✅' if quarantine_success and is_quarantined else '❌'}")
            
            return True, result
            
        except Exception as e:
            print(f"   ❌ Intervention system validation failed: {e}")
            return False, {'error': str(e), 'performance_score': 0}
    
    async def validate_agent_simulation(self) -> Tuple[bool, Dict]:
        """Validate agent simulation system."""
        print("🤖 Validating agent simulation system...")
        
        try:
            redis_client = RedisClient()
            await redis_client.connect()
            
            trust_manager = TrustManager(redis_client)
            intervention_engine = InterventionEngine(
                trust_manager=trust_manager,
                redis_client=redis_client
            )
            gemini_client = GeminiClient()
            
            simulator = AgentSimulator(
                trust_manager=trust_manager,
                intervention_engine=intervention_engine,
                gemini_client=gemini_client
            )
            
            # Test agent creation
            test_agents = []
            creation_times = []
            
            for i in range(3):
                start_time = time.time()
                agent = await simulator.create_agent(f"validation_sim_agent_{i}")
                creation_time = (time.time() - start_time) * 1000
                creation_times.append(creation_time)
                test_agents.append(agent)
            
            # Test agent retrieval
            all_agents = await simulator.get_all_agents()
            created_agent_ids = {agent.agent_id for agent in test_agents}
            retrieved_agent_ids = {agent.agent_id for agent in all_agents}
            
            agents_found = created_agent_ids.issubset(retrieved_agent_ids)
            
            # Clean up
            for agent in test_agents:
                await redis_client.delete(f"trust_score:{agent.agent_id}")
            
            await redis_client.disconnect()
            
            avg_creation_time = sum(creation_times) / len(creation_times)
            
            performance_score = 100
            if avg_creation_time > 100:  # 100ms threshold
                performance_score -= 20
            if not agents_found:
                performance_score -= 50
            
            result = {
                'agents_created': len(test_agents),
                'avg_creation_time_ms': avg_creation_time,
                'retrieval_accurate': agents_found,
                'performance_score': max(0, performance_score)
            }
            
            print(f"   ✅ Agent simulation operational")
            print(f"   🤖 Agents created: {len(test_agents)}")
            print(f"   ⚡ Avg creation time: {avg_creation_time:.1f}ms")
            print(f"   📊 Retrieval accurate: {'✅' if agents_found else '❌'}")
            
            return True, result
            
        except Exception as e:
            print(f"   ❌ Agent simulation validation failed: {e}")
            return False, {'error': str(e), 'performance_score': 0}
    
    def calculate_overall_score(self) -> int:
        """Calculate overall demo readiness score."""
        component_scores = self.validation_results['component_scores']
        
        if not component_scores:
            return 0
        
        # Weighted scoring
        weights = {
            'redis': 0.2,
            'gemini': 0.3,
            'trust_management': 0.2,
            'intervention': 0.2,
            'simulation': 0.1
        }
        
        weighted_score = 0
        total_weight = 0
        
        for component, weight in weights.items():
            if component in component_scores:
                score = component_scores[component].get('performance_score', 0)
                weighted_score += score * weight
                total_weight += weight
        
        return int(weighted_score / total_weight) if total_weight > 0 else 0
    
    def generate_recommendations(self) -> List[str]:
        """Generate recommendations based on validation results."""
        recommendations = []
        component_scores = self.validation_results['component_scores']
        
        # Redis recommendations
        if 'redis' in component_scores:
            redis_score = component_scores['redis'].get('performance_score', 0)
            if redis_score < 80:
                recommendations.append("🔧 Optimize Redis configuration for better performance")
            if not component_scores['redis'].get('connected', False):
                recommendations.append("🚨 CRITICAL: Fix Redis connection before demo")
        
        # Gemini recommendations
        if 'gemini' in component_scores:
            gemini_score = component_scores['gemini'].get('performance_score', 0)
            if gemini_score < 80:
                recommendations.append("🧠 Check Gemini API key and network connectivity")
            avg_latency = component_scores['gemini'].get('avg_latency_ms', 0)
            if avg_latency > self.thresholds['gemini_latency_ms']:
                recommendations.append(f"⚡ Gemini latency ({avg_latency:.1f}ms) exceeds threshold")
        
        # Trust management recommendations
        if 'trust_management' in component_scores:
            trust_score = component_scores['trust_management'].get('performance_score', 0)
            if trust_score < 80:
                recommendations.append("🛡️  Review trust management system configuration")
        
        # Intervention recommendations
        if 'intervention' in component_scores:
            intervention_score = component_scores['intervention'].get('performance_score', 0)
            if intervention_score < 80:
                recommendations.append("🚫 Test intervention system thoroughly before demo")
        
        # Overall recommendations
        overall_score = self.validation_results['overall_score']
        if overall_score >= 90:
            recommendations.append("✅ System ready for live demonstration")
        elif overall_score >= 70:
            recommendations.append("⚠️  System mostly ready - address minor issues")
        else:
            recommendations.append("🚨 System not ready - use backup demo materials")
        
        return recommendations
    
    async def run_validation(self) -> Dict:
        """Run complete demo validation suite."""
        print("🔍 CHORUS DEMO VALIDATION")
        print("=" * 50)
        print("Validating system readiness for live demonstration...")
        print()
        
        # Run all validation tests
        validations = [
            ('redis', self.validate_redis_connection()),
            ('gemini', self.validate_gemini_integration()),
            ('trust_management', self.validate_trust_management()),
            ('intervention', self.validate_intervention_system()),
            ('simulation', self.validate_agent_simulation())
        ]
        
        for component_name, validation_coro in validations:
            try:
                success, result = await validation_coro
                self.validation_results['component_scores'][component_name] = result
                print()
            except Exception as e:
                print(f"   ❌ {component_name} validation error: {e}")
                self.validation_results['component_scores'][component_name] = {
                    'error': str(e),
                    'performance_score': 0
                }
                print()
        
        # Calculate overall score
        self.validation_results['overall_score'] = self.calculate_overall_score()
        
        # Generate recommendations
        self.validation_results['recommendations'] = self.generate_recommendations()
        
        # Print summary
        self.print_validation_summary()
        
        return self.validation_results
    
    def print_validation_summary(self):
        """Print validation summary and recommendations."""
        print("📊 VALIDATION SUMMARY")
        print("=" * 50)
        
        overall_score = self.validation_results['overall_score']
        
        # Overall score with color coding
        if overall_score >= 90:
            score_icon = "🟢"
            status = "EXCELLENT"
        elif overall_score >= 70:
            score_icon = "🟡"
            status = "GOOD"
        else:
            score_icon = "🔴"
            status = "NEEDS ATTENTION"
        
        print(f"{score_icon} Overall Demo Readiness: {overall_score}% ({status})")
        print()
        
        # Component scores
        print("📋 Component Scores:")
        for component, result in self.validation_results['component_scores'].items():
            score = result.get('performance_score', 0)
            icon = "✅" if score >= 80 else "⚠️" if score >= 60 else "❌"
            print(f"   {icon} {component.replace('_', ' ').title()}: {score}%")
        
        print()
        
        # Recommendations
        print("💡 Recommendations:")
        for recommendation in self.validation_results['recommendations']:
            print(f"   {recommendation}")
        
        print()
        
        # Demo readiness assessment
        if overall_score >= 90:
            print("🎯 DEMO STATUS: Ready for live demonstration")
            print("   All systems operational with excellent performance")
        elif overall_score >= 70:
            print("⚠️  DEMO STATUS: Mostly ready with minor issues")
            print("   Consider addressing recommendations before demo")
        else:
            print("🚨 DEMO STATUS: Not ready for live demonstration")
            print("   Use backup demo materials or postpone until issues resolved")

async def main():
    """Main entry point for demo validation."""
    print("🔍 Chorus Demo Validator")
    print("Pre-demo system validation and reliability testing")
    print()
    
    validator = DemoValidator()
    
    try:
        results = await validator.run_validation()
        
        # Save results to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f"demo_validation_{timestamp}.json"
        
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"📄 Validation results saved to: {results_file}")
        
        # Return appropriate exit code
        overall_score = results['overall_score']
        if overall_score >= 70:
            sys.exit(0)  # Success
        else:
            sys.exit(1)  # Failure
            
    except KeyboardInterrupt:
        print("\n🛑 Validation interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Validation failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())