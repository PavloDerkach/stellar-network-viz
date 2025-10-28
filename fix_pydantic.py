#!/usr/bin/env python3
"""
Quick fix script for pydantic compatibility issues.
"""
import subprocess
import sys

def fix_pydantic():
    print("🔧 Fixing Pydantic compatibility issue...")
    print("-" * 50)
    
    # Install pydantic-settings
    print("📦 Installing pydantic-settings...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pydantic-settings>=2.0.0"])
    
    print("\n✅ Fix applied successfully!")
    print("\nYou can now run the application with:")
    print("  streamlit run web/app.py")

if __name__ == "__main__":
    try:
        fix_pydantic()
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nPlease try manual installation:")
        print("  pip install pydantic-settings")
        sys.exit(1)
