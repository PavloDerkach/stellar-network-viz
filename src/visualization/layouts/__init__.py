"""Layout algorithms for graph visualization."""

from .base import BaseLayout
from .spring import SpringLayout
from .hierarchical import HierarchicalLayout
from .other import CircularLayout, SpectralLayout, KamadaKawaiLayout

__all__ = [
    'BaseLayout',
    'SpringLayout', 
    'HierarchicalLayout',
    'CircularLayout',
    'SpectralLayout',
    'KamadaKawaiLayout'
]

# Layout factory
def get_layout(layout_type: str) -> BaseLayout:
    """
    Get layout algorithm by name.
    
    Args:
        layout_type: Name of layout algorithm
        
    Returns:
        Layout algorithm instance
    """
    layouts = {
        'spring': SpringLayout,
        'hierarchical': HierarchicalLayout,
        'circular': CircularLayout,
        'spectral': SpectralLayout,
        'kamada_kawai': KamadaKawaiLayout,
        'kamada-kawai': KamadaKawaiLayout,  # Alternative name
    }
    
    layout_class = layouts.get(layout_type.lower(), SpringLayout)
    return layout_class()
