#!/usr/bin/env python3
"""
Test script for graph layout algorithms.
Tests all available layouts to ensure they work correctly.
"""
import sys
import networkx as nx
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

print("🧪 Testing Graph Layout Algorithms\n")
print("="*60)

# Create test graph
G = nx.karate_club_graph()
print(f"📊 Test graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges\n")

# Test layouts
layouts_to_test = {
    "spring": "Spring/Force-directed layout",
    "circular": "Circular layout",
    "spectral": "Spectral layout",
    "kamada": "Kamada-Kawai layout (requires scipy)"
}

results = {}

for layout_name, description in layouts_to_test.items():
    print(f"\n{'='*60}")
    print(f"Testing: {layout_name} - {description}")
    print(f"{'='*60}")
    
    try:
        if layout_name == "spring":
            pos = nx.spring_layout(G)
            print("✅ Spring layout: SUCCESS")
            results[layout_name] = "✅ PASS"
            
        elif layout_name == "circular":
            pos = nx.circular_layout(G)
            print("✅ Circular layout: SUCCESS")
            results[layout_name] = "✅ PASS"
            
        elif layout_name == "spectral":
            # Spectral requires connected graph
            if nx.is_connected(G):
                pos = nx.spectral_layout(G)
                print("✅ Spectral layout: SUCCESS")
                results[layout_name] = "✅ PASS"
            else:
                # For disconnected graphs, work on largest component
                largest_cc = max(nx.connected_components(G), key=len)
                subG = G.subgraph(largest_cc)
                pos = nx.spectral_layout(subG)
                print("✅ Spectral layout: SUCCESS (using largest component)")
                results[layout_name] = "✅ PASS"
                
        elif layout_name == "kamada":
            try:
                import scipy
                print(f"   scipy version: {scipy.__version__}")
                pos = nx.kamada_kawai_layout(G)
                print("✅ Kamada-Kawai layout: SUCCESS")
                results[layout_name] = "✅ PASS"
            except ImportError:
                print("❌ scipy is not installed")
                print("   Install with: pip install scipy --break-system-packages")
                results[layout_name] = "❌ FAIL (scipy not installed)"
                
        # Verify positions
        if layout_name in ["spring", "circular", "spectral"] or (layout_name == "kamada" and "scipy" in sys.modules):
            assert len(pos) > 0, "Layout returned empty positions"
            assert all(len(coord) == 2 for coord in pos.values()), "Invalid coordinate format"
            print(f"   Generated {len(pos)} node positions")
            
    except Exception as e:
        print(f"❌ {layout_name} layout: FAILED")
        print(f"   Error: {str(e)}")
        results[layout_name] = f"❌ FAIL: {str(e)}"

# Summary
print("\n" + "="*60)
print("📋 SUMMARY")
print("="*60)

for layout_name, result in results.items():
    description = layouts_to_test[layout_name]
    print(f"{layout_name:12} - {description:40} {result}")

print("\n" + "="*60)

# Check if all passed
passed = sum(1 for r in results.values() if r.startswith("✅"))
total = len(results)

if passed == total:
    print(f"🎉 All {total} layouts PASSED!")
    print("\n✅ Graph visualization is ready to use!")
    sys.exit(0)
else:
    print(f"⚠️  {passed}/{total} layouts passed")
    
    # Check scipy specifically
    if any("scipy not installed" in str(r) for r in results.values()):
        print("\n📦 To fix scipy issue:")
        print("   pip install scipy --break-system-packages")
        print("\nOr run the install script:")
        print("   python scripts/install_scipy.py")
    
    sys.exit(1)
