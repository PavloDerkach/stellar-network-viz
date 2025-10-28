#!/usr/bin/env python3
"""
Script to check and install scipy for hierarchical layout support.
"""
import sys
import subprocess

def check_scipy():
    """Check if scipy is installed."""
    try:
        import scipy
        print(f"✅ scipy is already installed (version {scipy.__version__})")
        return True
    except ImportError:
        print("❌ scipy is not installed")
        return False

def install_scipy():
    """Install scipy."""
    print("\n📦 Installing scipy...")
    try:
        subprocess.check_call([
            sys.executable, 
            "-m", 
            "pip", 
            "install", 
            "scipy",
            "--break-system-packages"
        ])
        print("✅ scipy installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install scipy: {e}")
        print("\nTry manually:")
        print(f"  {sys.executable} -m pip install scipy --break-system-packages")
        return False

def verify_installation():
    """Verify scipy can be imported and used."""
    try:
        import scipy
        import networkx as nx
        
        # Test kamada_kawai_layout
        G = nx.karate_club_graph()
        pos = nx.kamada_kawai_layout(G)
        
        print("✅ scipy is working correctly!")
        print(f"   Tested kamada_kawai_layout on {G.number_of_nodes()} nodes")
        return True
    except Exception as e:
        print(f"❌ scipy verification failed: {e}")
        return False

if __name__ == "__main__":
    print("🔍 Checking scipy installation...\n")
    
    if check_scipy():
        print("\n🎉 scipy is ready to use!")
        verify_installation()
    else:
        print("\n" + "="*50)
        response = input("Would you like to install scipy now? (y/n): ")
        if response.lower() == 'y':
            if install_scipy():
                print("\n" + "="*50)
                print("🔄 Verifying installation...")
                verify_installation()
        else:
            print("\n⚠️  Please install scipy manually:")
            print(f"   {sys.executable} -m pip install scipy --break-system-packages")
