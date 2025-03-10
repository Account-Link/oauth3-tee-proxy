# Apply patches from plugins

# Import Twitter patches
from plugins.twitter.patches import apply_patches as apply_twitter_patches

def apply_patches():
    """
    Apply all necessary patches for the application.
    This function calls individual patch functions from plugins.
    """
    # Apply Twitter patches
    apply_twitter_patches()
    
    # Add other plugin patches here as needed