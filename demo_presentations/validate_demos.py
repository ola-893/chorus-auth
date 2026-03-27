#!/usr/bin/env python3
"""
Demo Validation Script - Validates demo materials without full system dependencies
"""
import os
import sys
from pathlib import Path

def validate_demo_files():
    """Validate that all demo files exist and are accessible."""
    demo_dir = Path(__file__).parent
    
    validation_results = {
        'scenarios': {},
        'scripts': {},
        'backup_materials': {},
        'video_production': {},
        'testing': {}
    }
    
    # Check scenario files
    scenarios_dir = demo_dir / 'scenarios'
    required_scenarios = [
        'executive_demo.py',
        'technical_demo.py', 
        'hackathon_demo.py',
        'partner_showcase_demo.py'
    ]
    
    for scenario in required_scenarios:
        scenario_path = scenarios_dir / scenario
        validation_results['scenarios'][scenario] = {
            'exists': scenario_path.exists(),
            'size': scenario_path.stat().st_size if scenario_path.exists() else 0,
            'readable': scenario_path.is_file() if scenario_path.exists() else False
        }
    
    # Check script files
    scripts_dir = demo_dir / 'scripts'
    required_scripts = [
        'executive_narrative.md'
    ]
    
    for script in required_scripts:
        script_path = scripts_dir / script
        validation_results['scripts'][script] = {
            'exists': script_path.exists(),
            'size': script_path.stat().st_size if script_path.exists() else 0,
            'readable': script_path.is_file() if script_path.exists() else False
        }
    
    # Check backup materials
    backup_dir = demo_dir / 'backup_materials'
    required_backups = [
        'offline_demo.py'
    ]
    
    for backup in required_backups:
        backup_path = backup_dir / backup
        validation_results['backup_materials'][backup] = {
            'exists': backup_path.exists(),
            'size': backup_path.stat().st_size if backup_path.exists() else 0,
            'readable': backup_path.is_file() if backup_path.exists() else False
        }
    
    # Check video production materials
    video_dir = demo_dir / 'video_production'
    required_video = [
        'storyboard.md'
    ]
    
    for video in required_video:
        video_path = video_dir / video
        validation_results['video_production'][video] = {
            'exists': video_path.exists(),
            'size': video_path.stat().st_size if video_path.exists() else 0,
            'readable': video_path.is_file() if video_path.exists() else False
        }
    
    # Check testing materials
    testing_dir = demo_dir / 'testing'
    required_testing = [
        'demo_validator.py',
        'timing_tests.py'
    ]
    
    for test in required_testing:
        test_path = testing_dir / test
        validation_results['testing'][test] = {
            'exists': test_path.exists(),
            'size': test_path.stat().st_size if test_path.exists() else 0,
            'readable': test_path.is_file() if test_path.exists() else False
        }
    
    return validation_results

def print_validation_report(results):
    """Print a formatted validation report."""
    print("\n" + "="*60)
    print("DEMO MATERIALS VALIDATION REPORT")
    print("="*60)
    
    total_files = 0
    valid_files = 0
    
    for category, files in results.items():
        print(f"\n{category.upper()}:")
        for filename, status in files.items():
            total_files += 1
            if status['exists'] and status['readable'] and status['size'] > 0:
                valid_files += 1
                print(f"  ✓ {filename} ({status['size']} bytes)")
            else:
                print(f"  ✗ {filename} (missing or empty)")
    
    success_rate = (valid_files / total_files) * 100 if total_files > 0 else 0
    
    print(f"\nSUMMARY:")
    print(f"  Total Files: {total_files}")
    print(f"  Valid Files: {valid_files}")
    print(f"  Success Rate: {success_rate:.1f}%")
    
    if success_rate >= 90:
        print(f"  Status: ✅ READY FOR PRESENTATION")
    elif success_rate >= 70:
        print(f"  Status: ⚠️  MOSTLY READY (minor issues)")
    else:
        print(f"  Status: ❌ NEEDS ATTENTION")
    
    print("="*60)
    
    return success_rate >= 70

def main():
    """Main validation function."""
    print("Validating demo presentation materials...")
    
    results = validate_demo_files()
    success = print_validation_report(results)
    
    if success:
        print("\n🎉 Demo materials are ready for hackathon presentation!")
        return 0
    else:
        print("\n⚠️  Some demo materials need attention.")
        return 1

if __name__ == "__main__":
    sys.exit(main())