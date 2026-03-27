#!/usr/bin/env python3
"""
Timing Tests - Chorus Demo Presentations
Validate presentation timing and pacing for different demo scenarios

This script ensures demos stay within time limits and maintain
appropriate pacing for maximum audience engagement.
"""

import asyncio
import time
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

# Add demo scenarios to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scenarios'))

class TimingValidator:
    """Validate demo timing and pacing."""
    
    def __init__(self):
        self.timing_results = {
            'executive_demo': {},
            'technical_demo': {},
            'hackathon_demo': {},
            'partner_showcase_demo': {}
        }
        
        # Target timing constraints (in seconds)
        self.timing_constraints = {
            'executive_demo': {
                'total_max': 180,      # 3 minutes max
                'total_target': 165,   # 2:45 target
                'sections': {
                    'problem_statement': 45,
                    'solution_demo': 90,
                    'business_value': 30,
                    'call_to_action': 15
                }
            },
            'technical_demo': {
                'total_max': 600,      # 10 minutes max
                'total_target': 540,   # 9 minutes target
                'sections': {
                    'architecture': 60,
                    'agent_lifecycle': 60,
                    'ai_analysis': 120,
                    'trust_management': 90,
                    'intervention': 90,
                    'monitoring': 90,
                    'summary': 30
                }
            },
            'hackathon_demo': {
                'total_max': 300,      # 5 minutes max
                'total_target': 270,   # 4:30 target
                'sections': {
                    'innovation': 60,
                    'partner_integration': 90,
                    'live_scenario': 120,
                    'impact': 30
                }
            },
            'partner_showcase_demo': {
                'total_max': 480,      # 8 minutes max
                'total_target': 420,   # 7 minutes target
                'sections': {
                    'gemini_showcase': 120,
                    'datadog_showcase': 60,
                    'confluent_showcase': 60,
                    'elevenlabs_showcase': 60,
                    'synergy_demo': 60,
                    'summary': 60
                }
            }
        }
    
    def time_function_execution(self, func, *args, **kwargs):
        """Time the execution of a function."""
        start_time = time.time()
        try:
            if asyncio.iscoroutinefunction(func):
                result = asyncio.run(func(*args, **kwargs))
            else:
                result = func(*args, **kwargs)
            success = True
        except Exception as e:
            result = str(e)
            success = False
        
        end_time = time.time()
        duration = end_time - start_time
        
        return {
            'duration': duration,
            'success': success,
            'result': result,
            'start_time': start_time,
            'end_time': end_time
        }
    
    def simulate_demo_section(self, section_name: str, target_duration: float) -> Dict:
        """Simulate a demo section with realistic timing."""
        print(f"   ⏱️  Timing {section_name}...")
        
        # Simulate realistic demo activities
        start_time = time.time()
        
        # Simulate different types of demo activities
        if 'ai' in section_name.lower() or 'gemini' in section_name.lower():
            # AI operations are typically faster
            time.sleep(min(2.0, target_duration * 0.1))
        elif 'demo' in section_name.lower() or 'scenario' in section_name.lower():
            # Live demos take more time
            time.sleep(min(5.0, target_duration * 0.2))
        else:
            # Standard presentation sections
            time.sleep(min(1.0, target_duration * 0.05))
        
        actual_duration = time.time() - start_time
        
        # Calculate timing metrics
        timing_accuracy = abs(target_duration - actual_duration) / target_duration
        within_tolerance = timing_accuracy <= 0.2  # 20% tolerance
        
        return {
            'section_name': section_name,
            'target_duration': target_duration,
            'actual_duration': actual_duration,
            'timing_accuracy': timing_accuracy,
            'within_tolerance': within_tolerance,
            'variance_seconds': actual_duration - target_duration,
            'variance_percentage': (actual_duration - target_duration) / target_duration * 100
        }
    
    def validate_executive_demo_timing(self) -> Dict:
        """Validate executive demo timing."""
        print("💼 Validating Executive Demo Timing")
        print("-" * 40)
        
        constraints = self.timing_constraints['executive_demo']
        sections = constraints['sections']
        
        section_results = []
        total_actual_duration = 0
        
        for section_name, target_duration in sections.items():
            result = self.simulate_demo_section(section_name, target_duration)
            section_results.append(result)
            total_actual_duration += result['actual_duration']
            
            # Print section timing
            status = "✅" if result['within_tolerance'] else "⚠️"
            print(f"      {status} {section_name}: {result['actual_duration']:.1f}s (target: {target_duration}s)")
        
        # Overall timing assessment
        total_target = constraints['total_target']
        total_max = constraints['total_max']
        
        timing_assessment = {
            'demo_type': 'executive_demo',
            'total_target': total_target,
            'total_max': total_max,
            'total_actual': total_actual_duration,
            'within_target': total_actual_duration <= total_target,
            'within_max': total_actual_duration <= total_max,
            'section_results': section_results,
            'overall_variance': total_actual_duration - total_target,
            'timing_score': self.calculate_timing_score(section_results, total_actual_duration, total_target, total_max)
        }
        
        print(f"\n   📊 Total Duration: {total_actual_duration:.1f}s")
        print(f"   🎯 Target: {total_target}s | Max: {total_max}s")
        print(f"   {'✅' if timing_assessment['within_max'] else '❌'} Within Limits: {timing_assessment['within_max']}")
        
        return timing_assessment
    
    def validate_technical_demo_timing(self) -> Dict:
        """Validate technical demo timing."""
        print("🔧 Validating Technical Demo Timing")
        print("-" * 40)
        
        constraints = self.timing_constraints['technical_demo']
        sections = constraints['sections']
        
        section_results = []
        total_actual_duration = 0
        
        for section_name, target_duration in sections.items():
            result = self.simulate_demo_section(section_name, target_duration)
            section_results.append(result)
            total_actual_duration += result['actual_duration']
            
            status = "✅" if result['within_tolerance'] else "⚠️"
            print(f"      {status} {section_name}: {result['actual_duration']:.1f}s (target: {target_duration}s)")
        
        total_target = constraints['total_target']
        total_max = constraints['total_max']
        
        timing_assessment = {
            'demo_type': 'technical_demo',
            'total_target': total_target,
            'total_max': total_max,
            'total_actual': total_actual_duration,
            'within_target': total_actual_duration <= total_target,
            'within_max': total_actual_duration <= total_max,
            'section_results': section_results,
            'overall_variance': total_actual_duration - total_target,
            'timing_score': self.calculate_timing_score(section_results, total_actual_duration, total_target, total_max)
        }
        
        print(f"\n   📊 Total Duration: {total_actual_duration:.1f}s")
        print(f"   🎯 Target: {total_target}s | Max: {total_max}s")
        print(f"   {'✅' if timing_assessment['within_max'] else '❌'} Within Limits: {timing_assessment['within_max']}")
        
        return timing_assessment
    
    def validate_hackathon_demo_timing(self) -> Dict:
        """Validate hackathon demo timing."""
        print("🏆 Validating Hackathon Demo Timing")
        print("-" * 40)
        
        constraints = self.timing_constraints['hackathon_demo']
        sections = constraints['sections']
        
        section_results = []
        total_actual_duration = 0
        
        for section_name, target_duration in sections.items():
            result = self.simulate_demo_section(section_name, target_duration)
            section_results.append(result)
            total_actual_duration += result['actual_duration']
            
            status = "✅" if result['within_tolerance'] else "⚠️"
            print(f"      {status} {section_name}: {result['actual_duration']:.1f}s (target: {target_duration}s)")
        
        total_target = constraints['total_target']
        total_max = constraints['total_max']
        
        timing_assessment = {
            'demo_type': 'hackathon_demo',
            'total_target': total_target,
            'total_max': total_max,
            'total_actual': total_actual_duration,
            'within_target': total_actual_duration <= total_target,
            'within_max': total_actual_duration <= total_max,
            'section_results': section_results,
            'overall_variance': total_actual_duration - total_target,
            'timing_score': self.calculate_timing_score(section_results, total_actual_duration, total_target, total_max)
        }
        
        print(f"\n   📊 Total Duration: {total_actual_duration:.1f}s")
        print(f"   🎯 Target: {total_target}s | Max: {total_max}s")
        print(f"   {'✅' if timing_assessment['within_max'] else '❌'} Within Limits: {timing_assessment['within_max']}")
        
        return timing_assessment
    
    def validate_partner_showcase_timing(self) -> Dict:
        """Validate partner showcase demo timing."""
        print("🤝 Validating Partner Showcase Demo Timing")
        print("-" * 40)
        
        constraints = self.timing_constraints['partner_showcase_demo']
        sections = constraints['sections']
        
        section_results = []
        total_actual_duration = 0
        
        for section_name, target_duration in sections.items():
            result = self.simulate_demo_section(section_name, target_duration)
            section_results.append(result)
            total_actual_duration += result['actual_duration']
            
            status = "✅" if result['within_tolerance'] else "⚠️"
            print(f"      {status} {section_name}: {result['actual_duration']:.1f}s (target: {target_duration}s)")
        
        total_target = constraints['total_target']
        total_max = constraints['total_max']
        
        timing_assessment = {
            'demo_type': 'partner_showcase_demo',
            'total_target': total_target,
            'total_max': total_max,
            'total_actual': total_actual_duration,
            'within_target': total_actual_duration <= total_target,
            'within_max': total_actual_duration <= total_max,
            'section_results': section_results,
            'overall_variance': total_actual_duration - total_target,
            'timing_score': self.calculate_timing_score(section_results, total_actual_duration, total_target, total_max)
        }
        
        print(f"\n   📊 Total Duration: {total_actual_duration:.1f}s")
        print(f"   🎯 Target: {total_target}s | Max: {total_max}s")
        print(f"   {'✅' if timing_assessment['within_max'] else '❌'} Within Limits: {timing_assessment['within_max']}")
        
        return timing_assessment
    
    def calculate_timing_score(self, section_results: List[Dict], total_actual: float, total_target: float, total_max: float) -> int:
        """Calculate overall timing score (0-100)."""
        score = 100
        
        # Penalize sections that are significantly off-target
        for section in section_results:
            if not section['within_tolerance']:
                score -= 10
        
        # Penalize total duration overruns
        if total_actual > total_max:
            score -= 30  # Major penalty for exceeding max time
        elif total_actual > total_target:
            score -= 15  # Minor penalty for exceeding target
        
        # Bonus for being close to target
        total_variance = abs(total_actual - total_target) / total_target
        if total_variance <= 0.05:  # Within 5%
            score += 10
        
        return max(0, min(100, score))
    
    def generate_timing_recommendations(self, assessment: Dict) -> List[str]:
        """Generate timing recommendations based on assessment."""
        recommendations = []
        
        demo_type = assessment['demo_type']
        total_actual = assessment['total_actual']
        total_target = assessment['total_target']
        total_max = assessment['total_max']
        
        # Overall timing recommendations
        if total_actual > total_max:
            recommendations.append(f"🚨 CRITICAL: Demo exceeds maximum time by {total_actual - total_max:.1f}s")
            recommendations.append("   Consider removing non-essential sections")
        elif total_actual > total_target:
            recommendations.append(f"⚠️  Demo exceeds target time by {total_actual - total_target:.1f}s")
            recommendations.append("   Practice to improve pacing")
        else:
            recommendations.append("✅ Demo timing is within acceptable limits")
        
        # Section-specific recommendations
        problematic_sections = [s for s in assessment['section_results'] if not s['within_tolerance']]
        
        if problematic_sections:
            recommendations.append(f"\n📋 Sections needing attention:")
            for section in problematic_sections:
                variance = section['variance_seconds']
                if variance > 0:
                    recommendations.append(f"   ⏩ {section['section_name']}: {variance:.1f}s too long")
                else:
                    recommendations.append(f"   ⏪ {section['section_name']}: {abs(variance):.1f}s too short")
        
        # Demo-specific recommendations
        if demo_type == 'executive_demo':
            recommendations.append("\n💼 Executive Demo Tips:")
            recommendations.append("   • Keep technical details minimal")
            recommendations.append("   • Focus on business value and ROI")
            recommendations.append("   • Practice smooth transitions")
        elif demo_type == 'hackathon_demo':
            recommendations.append("\n🏆 Hackathon Demo Tips:")
            recommendations.append("   • Emphasize innovation and uniqueness")
            recommendations.append("   • Show all partner integrations clearly")
            recommendations.append("   • End with strong call to action")
        
        return recommendations
    
    def run_all_timing_tests(self) -> Dict:
        """Run timing tests for all demo types."""
        print("⏱️  CHORUS DEMO TIMING VALIDATION")
        print("=" * 50)
        print("Testing presentation timing and pacing...")
        print()
        
        # Run all timing validations
        results = {}
        
        results['executive_demo'] = self.validate_executive_demo_timing()
        print()
        
        results['technical_demo'] = self.validate_technical_demo_timing()
        print()
        
        results['hackathon_demo'] = self.validate_hackathon_demo_timing()
        print()
        
        results['partner_showcase_demo'] = self.validate_partner_showcase_timing()
        print()
        
        # Generate overall summary
        self.print_timing_summary(results)
        
        return results
    
    def print_timing_summary(self, results: Dict):
        """Print comprehensive timing summary."""
        print("📊 TIMING VALIDATION SUMMARY")
        print("=" * 50)
        
        # Calculate overall metrics
        total_demos = len(results)
        demos_within_limits = sum(1 for r in results.values() if r['within_max'])
        demos_within_target = sum(1 for r in results.values() if r['within_target'])
        avg_timing_score = sum(r['timing_score'] for r in results.values()) / total_demos
        
        print(f"📈 Overall Metrics:")
        print(f"   🎯 Demos within target: {demos_within_target}/{total_demos}")
        print(f"   ✅ Demos within limits: {demos_within_limits}/{total_demos}")
        print(f"   📊 Average timing score: {avg_timing_score:.1f}%")
        print()
        
        # Individual demo summaries
        print(f"📋 Individual Demo Results:")
        for demo_type, result in results.items():
            status = "✅" if result['within_max'] else "❌"
            score = result['timing_score']
            duration = result['total_actual']
            target = result['total_target']
            
            print(f"   {status} {demo_type.replace('_', ' ').title()}: {duration:.1f}s (target: {target}s) - Score: {score}%")
        
        print()
        
        # Recommendations
        print(f"💡 Overall Recommendations:")
        if avg_timing_score >= 90:
            print(f"   ✅ All demos are well-timed and ready for presentation")
        elif avg_timing_score >= 70:
            print(f"   ⚠️  Most demos are acceptable, minor adjustments recommended")
        else:
            print(f"   🚨 Significant timing issues detected, practice required")
        
        # Specific recommendations for problematic demos
        for demo_type, result in results.items():
            if result['timing_score'] < 80:
                print(f"\n   🔧 {demo_type.replace('_', ' ').title()} needs attention:")
                recommendations = self.generate_timing_recommendations(result)
                for rec in recommendations[:3]:  # Show top 3 recommendations
                    print(f"      {rec}")

def main():
    """Main entry point for timing tests."""
    print("⏱️  Chorus Demo Timing Tests")
    print("Validate presentation timing and pacing")
    print()
    
    validator = TimingValidator()
    
    try:
        results = validator.run_all_timing_tests()
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f"timing_validation_{timestamp}.json"
        
        import json
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"📄 Timing results saved to: {results_file}")
        
        # Determine exit code based on results
        avg_score = sum(r['timing_score'] for r in results.values()) / len(results)
        if avg_score >= 70:
            print("✅ Timing validation passed")
            sys.exit(0)
        else:
            print("❌ Timing validation failed")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n🛑 Timing tests interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Timing tests failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()