#!/usr/bin/env python3
"""
Optimized Demo Launcher - Chorus Multi-Agent Immune System
Comprehensive demo launcher with reliability testing and audience optimization

This script provides a unified interface for launching optimized demo presentations
with pre-validation, timing checks, and audience-specific customization.
"""

import asyncio
import sys
import os
import time
import json
import argparse
from datetime import datetime
from typing import Dict, List, Optional

# Add paths for demo components
current_dir = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(current_dir, 'scenarios'))
sys.path.insert(0, os.path.join(current_dir, 'testing'))
sys.path.insert(0, os.path.join(current_dir, 'backup_materials'))

class OptimizedDemoLauncher:
    """Comprehensive demo launcher with optimization and reliability features."""
    
    def __init__(self):
        self.demo_types = {
            'executive': {
                'name': 'Executive Demo',
                'duration': '3 minutes',
                'audience': 'Business leaders, decision makers',
                'focus': 'Business value, ROI, competitive advantage',
                'script': 'scenarios/executive_demo.py'
            },
            'technical': {
                'name': 'Technical Demo',
                'duration': '10 minutes',
                'audience': 'Engineers, architects, technical teams',
                'focus': 'Architecture, implementation, innovation',
                'script': 'scenarios/technical_demo.py'
            },
            'hackathon': {
                'name': 'Hackathon Demo',
                'duration': '5 minutes',
                'audience': 'Hackathon judges, evaluators',
                'focus': 'Innovation, partner integration, achievement',
                'script': 'scenarios/hackathon_demo.py'
            },
            'partner': {
                'name': 'Partner Showcase Demo',
                'duration': '8 minutes',
                'audience': 'Partner representatives, integration teams',
                'focus': 'Partner technology utilization, integration depth',
                'script': 'scenarios/partner_showcase_demo.py'
            }
        }
        
        self.validation_results = {}
        self.timing_results = {}
        self.demo_readiness_score = 0
    
    def print_launcher_header(self):
        """Print optimized demo launcher header."""
        print("\n" + "🚀" * 25)
        print("🎯 CHORUS OPTIMIZED DEMO LAUNCHER")
        print("   Maximum Impact • Reliable Delivery • Audience Optimized")
        print("🚀" * 25)
        print("⚡ Pre-validated • Timing Optimized • Backup Ready")
        print("=" * 80)
    
    def show_demo_menu(self):
        """Display available demo options."""
        print("\n📋 AVAILABLE DEMO PRESENTATIONS")
        print("-" * 50)
        
        for key, demo in self.demo_types.items():
            print(f"\n🎯 {key.upper()}: {demo['name']}")
            print(f"   ⏱️  Duration: {demo['duration']}")
            print(f"   👥 Audience: {demo['audience']}")
            print(f"   🎯 Focus: {demo['focus']}")
        
        print(f"\n🔧 UTILITY OPTIONS:")
        print(f"   validate: Run system validation")
        print(f"   timing: Test presentation timing")
        print(f"   offline: Backup offline demo")
        print(f"   help: Show detailed help")
    
    async def run_system_validation(self) -> bool:
        """Run comprehensive system validation."""
        print("\n🔍 RUNNING SYSTEM VALIDATION")
        print("=" * 50)
        
        try:
            # Import and run demo validator
            from demo_validator import DemoValidator
            
            validator = DemoValidator()
            self.validation_results = await validator.run_validation()
            
            self.demo_readiness_score = self.validation_results.get('overall_score', 0)
            
            print(f"\n📊 System Readiness Score: {self.demo_readiness_score}%")
            
            if self.demo_readiness_score >= 90:
                print("✅ System ready for live demonstration")
                return True
            elif self.demo_readiness_score >= 70:
                print("⚠️  System mostly ready - minor issues detected")
                return True
            else:
                print("🚨 System not ready - use backup demo")
                return False
                
        except Exception as e:
            print(f"❌ Validation failed: {e}")
            print("🔄 Proceeding with backup demo option")
            return False
    
    def run_timing_validation(self) -> bool:
        """Run presentation timing validation."""
        print("\n⏱️  RUNNING TIMING VALIDATION")
        print("=" * 50)
        
        try:
            # Import and run timing tests
            from timing_tests import TimingValidator
            
            validator = TimingValidator()
            self.timing_results = validator.run_all_timing_tests()
            
            # Calculate average timing score
            avg_score = sum(r['timing_score'] for r in self.timing_results.values()) / len(self.timing_results)
            
            print(f"\n📊 Average Timing Score: {avg_score:.1f}%")
            
            if avg_score >= 80:
                print("✅ Timing validation passed")
                return True
            else:
                print("⚠️  Timing issues detected - practice recommended")
                return False
                
        except Exception as e:
            print(f"❌ Timing validation failed: {e}")
            return False
    
    async def launch_demo(self, demo_type: str, validate: bool = True, check_timing: bool = True) -> bool:
        """Launch specified demo with optional validation."""
        if demo_type not in self.demo_types:
            print(f"❌ Unknown demo type: {demo_type}")
            return False
        
        demo_info = self.demo_types[demo_type]
        
        print(f"\n🎬 LAUNCHING {demo_info['name'].upper()}")
        print("=" * 60)
        print(f"⏱️  Duration: {demo_info['duration']}")
        print(f"👥 Audience: {demo_info['audience']}")
        print(f"🎯 Focus: {demo_info['focus']}")
        print()
        
        # Pre-demo validation
        system_ready = True
        timing_ready = True
        
        if validate:
            print("🔍 Pre-demo validation...")
            system_ready = await self.run_system_validation()
            print()
        
        if check_timing:
            print("⏱️  Timing validation...")
            timing_ready = self.run_timing_validation()
            print()
        
        # Determine demo approach
        if system_ready and timing_ready:
            print("✅ All validations passed - launching live demo")
            return await self.run_live_demo(demo_type)
        elif system_ready:
            print("⚠️  System ready but timing needs attention - launching with caution")
            return await self.run_live_demo(demo_type)
        else:
            print("🔄 System issues detected - launching backup demo")
            return await self.run_backup_demo(demo_type)
    
    async def run_live_demo(self, demo_type: str) -> bool:
        """Run live demo with full system integration."""
        demo_info = self.demo_types[demo_type]
        
        print(f"\n🎯 Starting live {demo_info['name']}...")
        print("🔴 LIVE DEMO - Real system integration active")
        print()
        
        try:
            # Import and run the appropriate demo
            if demo_type == 'executive':
                from executive_demo import ExecutiveDemo
                demo = ExecutiveDemo()
                await demo.initialize_system()
                await demo.run_demo()
            
            elif demo_type == 'technical':
                from technical_demo import TechnicalDemo
                demo = TechnicalDemo()
                await demo.initialize_system()
                await demo.run_demo()
            
            elif demo_type == 'hackathon':
                from hackathon_demo import HackathonDemo
                demo = HackathonDemo()
                await demo.initialize_system()
                await demo.run_demo()
            
            elif demo_type == 'partner':
                from partner_showcase_demo import PartnerShowcaseDemo
                demo = PartnerShowcaseDemo()
                await demo.initialize_system()
                await demo.run_demo()
            
            print("\n✅ Live demo completed successfully")
            return True
            
        except Exception as e:
            print(f"\n❌ Live demo failed: {e}")
            print("🔄 Switching to backup demo...")
            return await self.run_backup_demo(demo_type)
    
    async def run_backup_demo(self, demo_type: str) -> bool:
        """Run backup demo with pre-recorded data."""
        demo_info = self.demo_types[demo_type]
        
        print(f"\n🔄 Starting backup {demo_info['name']}...")
        print("📊 BACKUP DEMO - Using pre-recorded data")
        print()
        
        try:
            # Import and run offline demo
            from offline_demo import OfflineDemo
            
            demo = OfflineDemo(demo_type=demo_type)
            demo.run_demo()
            
            print("\n✅ Backup demo completed successfully")
            return True
            
        except Exception as e:
            print(f"\n❌ Backup demo failed: {e}")
            return False
    
    def show_demo_recommendations(self):
        """Show audience-specific demo recommendations."""
        print("\n💡 DEMO RECOMMENDATIONS BY AUDIENCE")
        print("=" * 50)
        
        recommendations = {
            'C-Suite Executives': {
                'demo': 'executive',
                'tips': [
                    'Focus on ROI and competitive advantage',
                    'Use business scenarios (CDN, trading, IoT)',
                    'Emphasize cost savings and risk mitigation',
                    'Keep technical details minimal'
                ]
            },
            'Technical Teams': {
                'demo': 'technical',
                'tips': [
                    'Show architecture and implementation details',
                    'Demonstrate API integrations and performance',
                    'Highlight testing and reliability features',
                    'Allow time for technical Q&A'
                ]
            },
            'Hackathon Judges': {
                'demo': 'hackathon',
                'tips': [
                    'Emphasize innovation and uniqueness',
                    'Show all partner integrations clearly',
                    'Highlight technical achievements',
                    'End with strong impact statement'
                ]
            },
            'Partner Representatives': {
                'demo': 'partner',
                'tips': [
                    'Deep dive into each partner technology',
                    'Show measurable integration value',
                    'Demonstrate real API usage',
                    'Highlight synergistic benefits'
                ]
            }
        }
        
        for audience, info in recommendations.items():
            print(f"\n🎯 {audience}:")
            print(f"   Recommended Demo: {info['demo']}")
            print(f"   Key Tips:")
            for tip in info['tips']:
                print(f"      • {tip}")
    
    def show_troubleshooting_guide(self):
        """Show troubleshooting guide for common issues."""
        print("\n🔧 TROUBLESHOOTING GUIDE")
        print("=" * 50)
        
        issues = {
            'Redis Connection Failed': [
                'Start Redis server: redis-server',
                'Check Redis port: redis-cli ping',
                'Verify network connectivity',
                'Use backup demo if persistent'
            ],
            'Gemini API Issues': [
                'Verify API key in .env file',
                'Check internet connectivity',
                'Test API key at Google AI Studio',
                'Use offline demo with simulated results'
            ],
            'Demo Timing Issues': [
                'Practice presentation flow',
                'Remove non-essential sections',
                'Use timing checkpoints',
                'Prepare shorter backup version'
            ],
            'System Performance Slow': [
                'Close unnecessary applications',
                'Check system resources',
                'Use performance mode',
                'Switch to backup demo'
            ]
        }
        
        for issue, solutions in issues.items():
            print(f"\n❓ {issue}:")
            for solution in solutions:
                print(f"   • {solution}")
    
    def interactive_demo_selection(self):
        """Interactive demo selection with guidance."""
        print("\n🎯 INTERACTIVE DEMO SELECTION")
        print("-" * 40)
        
        # Audience identification
        print("👥 Who is your audience?")
        print("   1. Business executives and decision makers")
        print("   2. Engineers and technical teams")
        print("   3. Hackathon judges and evaluators")
        print("   4. Partner representatives")
        print("   5. Mixed audience")
        
        try:
            choice = input("\nEnter choice (1-5): ").strip()
            
            audience_map = {
                '1': 'executive',
                '2': 'technical',
                '3': 'hackathon',
                '4': 'partner',
                '5': 'executive'  # Default to executive for mixed
            }
            
            selected_demo = audience_map.get(choice, 'executive')
            
            # Time constraints
            print(f"\n⏱️  How much time do you have?")
            print(f"   Recommended: {self.demo_types[selected_demo]['duration']}")
            
            time_input = input("Enter available time (minutes) or press Enter for recommended: ").strip()
            
            if time_input and int(time_input) < 5:
                print("⚠️  Very short time - consider key highlights only")
            
            # Validation preferences
            print(f"\n🔍 Pre-demo validation?")
            validate = input("Run system validation? (y/N): ").strip().lower() in ['y', 'yes']
            
            check_timing = input("Check presentation timing? (y/N): ").strip().lower() in ['y', 'yes']
            
            return selected_demo, validate, check_timing
            
        except (ValueError, KeyboardInterrupt):
            print("\n🔄 Using default executive demo")
            return 'executive', True, True
    
    async def run_interactive_launcher(self):
        """Run interactive demo launcher."""
        self.print_launcher_header()
        
        while True:
            try:
                print("\n📋 DEMO LAUNCHER OPTIONS")
                print("-" * 30)
                print("1. Interactive demo selection")
                print("2. Quick launch (executive demo)")
                print("3. Show all demo options")
                print("4. Run system validation")
                print("5. Test presentation timing")
                print("6. Show recommendations")
                print("7. Troubleshooting guide")
                print("8. Exit")
                
                choice = input("\nEnter choice (1-8): ").strip()
                
                if choice == '1':
                    demo_type, validate, check_timing = self.interactive_demo_selection()
                    await self.launch_demo(demo_type, validate, check_timing)
                
                elif choice == '2':
                    await self.launch_demo('executive', validate=True, check_timing=False)
                
                elif choice == '3':
                    self.show_demo_menu()
                
                elif choice == '4':
                    await self.run_system_validation()
                
                elif choice == '5':
                    self.run_timing_validation()
                
                elif choice == '6':
                    self.show_demo_recommendations()
                
                elif choice == '7':
                    self.show_troubleshooting_guide()
                
                elif choice == '8':
                    print("\n👋 Thank you for using Chorus Demo Launcher!")
                    break
                
                else:
                    print("❌ Invalid choice. Please try again.")
                
                input("\nPress Enter to continue...")
                
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")
                input("Press Enter to continue...")

async def main():
    """Main entry point for optimized demo launcher."""
    parser = argparse.ArgumentParser(description="Chorus Optimized Demo Launcher")
    parser.add_argument(
        'demo_type',
        nargs='?',
        choices=['executive', 'technical', 'hackathon', 'partner', 'interactive'],
        default='interactive',
        help='Type of demo to launch'
    )
    parser.add_argument(
        '--no-validate',
        action='store_true',
        help='Skip system validation'
    )
    parser.add_argument(
        '--no-timing',
        action='store_true',
        help='Skip timing validation'
    )
    parser.add_argument(
        '--offline',
        action='store_true',
        help='Force offline/backup demo'
    )
    
    args = parser.parse_args()
    
    launcher = OptimizedDemoLauncher()
    
    if args.demo_type == 'interactive':
        await launcher.run_interactive_launcher()
    else:
        if args.offline:
            await launcher.run_backup_demo(args.demo_type)
        else:
            await launcher.launch_demo(
                args.demo_type,
                validate=not args.no_validate,
                check_timing=not args.no_timing
            )

if __name__ == "__main__":
    print("🚀 Chorus Optimized Demo Launcher")
    print("Maximum impact presentations with reliability assurance")
    print()
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Demo launcher interrupted")
    except Exception as e:
        print(f"❌ Demo launcher failed: {e}")
        sys.exit(1)