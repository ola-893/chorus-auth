#!/usr/bin/env python3
"""
Chorus Demo Launcher

Simple launcher script that checks prerequisites and guides users through
the demo experience with helpful prompts and error handling.
"""

import os
import sys
import subprocess
import time
from pathlib import Path

def print_banner():
    """Print the Chorus demo banner."""
    banner = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║   🎭 CHORUS MULTI-AGENT IMMUNE SYSTEM - COMPREHENSIVE DEMO                  ║
║                                                                              ║
║   A real-time safety layer for decentralized multi-agent systems            ║
║   that predicts and prevents emergent failures before they cascade.         ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
    print(banner)

def check_python():
    """Check Python version."""
    print("🐍 Checking Python version...")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 9:
        print(f"   ✅ Python {version.major}.{version.minor}.{version.micro} - OK")
        return True
    else:
        print(f"   ❌ Python {version.major}.{version.minor}.{version.micro} - Need 3.9+")
        return False

def check_redis():
    """Check if Redis is available."""
    print("📊 Checking Redis server...")
    try:
        result = subprocess.run(['redis-cli', 'ping'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0 and 'PONG' in result.stdout:
            print("   ✅ Redis server - RUNNING")
            return True
        else:
            print("   ⚠️  Redis server - NOT RUNNING")
            return False
    except (subprocess.TimeoutExpired, FileNotFoundError):
        print("   ⚠️  Redis server - NOT FOUND")
        return False

def check_environment():
    """Check environment configuration."""
    print("⚙️  Checking environment configuration...")
    env_file = Path("backend/.env")
    
    if env_file.exists():
        print("   ✅ Environment file - FOUND")
        
        # Check for Gemini API key
        with open(env_file, 'r') as f:
            content = f.read()
            if 'CHORUS_GEMINI_API_KEY=' in content and 'your_' not in content:
                print("   ✅ Gemini API key - CONFIGURED")
                return True
            else:
                print("   ⚠️  Gemini API key - NOT CONFIGURED")
                return False
    else:
        print("   ❌ Environment file - NOT FOUND")
        return False

def check_dependencies():
    """Check Python dependencies."""
    print("📦 Checking Python dependencies...")
    
    # Check if virtual environment exists
    venv_path = Path("backend/venv")
    if venv_path.exists():
        print("   ✅ Virtual environment - FOUND")
    else:
        print("   ⚠️  Virtual environment - NOT FOUND")
        return False
    
    # Check if requirements are installed
    try:
        # Activate venv and check key packages
        if os.name == 'nt':  # Windows
            python_path = venv_path / "Scripts" / "python.exe"
        else:  # Unix/Linux/Mac
            python_path = venv_path / "bin" / "python"
        
        result = subprocess.run([str(python_path), '-c', 
                               'import google.generativeai, redis, fastapi, pytest'],
                              capture_output=True, timeout=10)
        
        if result.returncode == 0:
            print("   ✅ Dependencies - INSTALLED")
            return True
        else:
            print("   ❌ Dependencies - MISSING")
            return False
    except Exception:
        print("   ❌ Dependencies - CHECK FAILED")
        return False

def setup_environment():
    """Set up the environment if needed."""
    print("\n🔧 ENVIRONMENT SETUP")
    print("=" * 50)
    
    # Copy environment file if needed
    env_file = Path("backend/.env")
    env_example = Path("backend/.env.example")
    
    if not env_file.exists() and env_example.exists():
        print("📋 Copying environment configuration...")
        import shutil
        shutil.copy(env_example, env_file)
        print("   ✅ Environment file created")
        
        print("\n⚠️  IMPORTANT: Please edit backend/.env with your API keys:")
        print("   - CHORUS_GEMINI_API_KEY: Get from https://makersuite.google.com/app/apikey")
        print("   - CHORUS_DATADOG_API_KEY: Optional, for monitoring")
        print("   - CHORUS_ELEVENLABS_API_KEY: Optional, for voice alerts")
        
        input("\nPress Enter after configuring your API keys...")
    
    # Create virtual environment if needed
    venv_path = Path("backend/venv")
    if not venv_path.exists():
        print("🐍 Creating virtual environment...")
        subprocess.run([sys.executable, '-m', 'venv', str(venv_path)])
        print("   ✅ Virtual environment created")
        
        # Install dependencies
        print("📦 Installing dependencies...")
        if os.name == 'nt':  # Windows
            pip_path = venv_path / "Scripts" / "pip.exe"
        else:  # Unix/Linux/Mac
            pip_path = venv_path / "bin" / "pip"
        
        subprocess.run([str(pip_path), 'install', '-r', 'backend/requirements.txt'])
        print("   ✅ Dependencies installed")

def start_redis_if_needed():
    """Start Redis if it's not running."""
    if not check_redis():
        print("\n🚀 Starting Redis server...")
        try:
            # Try to start Redis
            if os.name == 'nt':  # Windows
                subprocess.Popen(['redis-server.exe'], 
                               creationflags=subprocess.CREATE_NEW_CONSOLE)
            else:  # Unix/Linux/Mac
                subprocess.Popen(['redis-server', '--daemonize', 'yes'])
            
            # Wait a moment and check again
            time.sleep(3)
            if check_redis():
                print("   ✅ Redis started successfully")
                return True
            else:
                print("   ⚠️  Redis start failed - some features may not work")
                return False
        except FileNotFoundError:
            print("   ⚠️  Redis not found - using demo mode")
            return False

def show_demo_options():
    """Show available demo options."""
    print("\n🎬 DEMO OPTIONS")
    print("=" * 50)
    
    options = [
        ("1", "🌟 Full System Demo (10 min)", "Complete demonstration of all capabilities"),
        ("2", "🤖 Agent Simulation (5 min)", "Focus on agent behavior and conflict prediction"),
        ("3", "📊 Interactive Dashboard", "Real-time CLI monitoring interface"),
        ("4", "🔮 Conflict Prediction", "AI-powered analysis demonstration"),
        ("5", "🌐 API Integration (2 min)", "REST API and service integration"),
        ("6", "🔧 Interactive Menu", "Full menu with all options and tools"),
        ("0", "❌ Exit", "Exit the demo launcher")
    ]
    
    for code, name, desc in options:
        print(f"  {code}) {name}")
        print(f"     {desc}")
        print()
    
    return options

def run_demo(choice):
    """Run the selected demo."""
    print(f"\n🚀 LAUNCHING DEMO")
    print("=" * 50)
    
    # Change to backend directory for demos
    original_dir = os.getcwd()
    
    try:
        if choice == "1":
            print("Starting Full System Demo...")
            subprocess.run([sys.executable, 'comprehensive_demo.py', '--mode', 'full'])
        
        elif choice == "2":
            print("Starting Agent Simulation Demo...")
            subprocess.run([sys.executable, 'comprehensive_demo.py', '--mode', 'simulation'])
        
        elif choice == "3":
            print("Starting Interactive Dashboard...")
            os.chdir("backend")
            subprocess.run([sys.executable, 'demo_cli_dashboard.py', '--agents', '8'])
        
        elif choice == "4":
            print("Starting Conflict Prediction Demo...")
            os.chdir("backend")
            subprocess.run([sys.executable, 'demo_intervention.py'])
        
        elif choice == "5":
            print("Starting API Integration Demo...")
            subprocess.run([sys.executable, 'comprehensive_demo.py', '--mode', 'api'])
        
        elif choice == "6":
            print("Starting Interactive Menu...")
            subprocess.run(['./demo_scenarios.sh'])
        
        else:
            print("Invalid choice")
            return False
            
    except KeyboardInterrupt:
        print("\n🛑 Demo interrupted by user")
    except Exception as e:
        print(f"❌ Demo failed: {e}")
    finally:
        os.chdir(original_dir)
    
    return True

def main():
    """Main launcher function."""
    print_banner()
    
    print("🔍 SYSTEM CHECK")
    print("=" * 50)
    
    # Check prerequisites
    checks = [
        ("Python 3.9+", check_python()),
        ("Redis Server", check_redis()),
        ("Environment Config", check_environment()),
        ("Dependencies", check_dependencies())
    ]
    
    all_good = all(result for _, result in checks)
    
    if not all_good:
        print(f"\n⚠️  Some prerequisites are missing. Setting up environment...")
        
        # Offer to set up environment
        setup_choice = input("\nWould you like to set up the environment automatically? (y/n): ")
        if setup_choice.lower() in ['y', 'yes']:
            setup_environment()
            start_redis_if_needed()
            
            # Re-check
            print(f"\n🔍 RE-CHECKING SYSTEM")
            print("=" * 30)
            for name, _ in checks:
                if name == "Python 3.9+":
                    result = check_python()
                elif name == "Redis Server":
                    result = check_redis()
                elif name == "Environment Config":
                    result = check_environment()
                elif name == "Dependencies":
                    result = check_dependencies()
        else:
            print("\n📚 Please see DEMO_README.md for manual setup instructions.")
            return
    
    # Show demo options
    while True:
        options = show_demo_options()
        
        try:
            choice = input("Choose a demo option (0-6): ").strip()
            
            if choice == "0":
                print("\n👋 Thanks for trying Chorus! See you next time.")
                break
            elif choice in ["1", "2", "3", "4", "5", "6"]:
                run_demo(choice)
                
                # Ask if user wants to run another demo
                again = input("\nWould you like to run another demo? (y/n): ")
                if again.lower() not in ['y', 'yes']:
                    break
            else:
                print("❌ Invalid choice. Please try again.")
                
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()