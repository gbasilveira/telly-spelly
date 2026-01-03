"""GPU detection and model availability for Telly Spelly"""

import logging

logger = logging.getLogger(__name__)

# Approximate VRAM requirements for Whisper models (in GB)
# These are estimates based on fp32 inference
MODEL_VRAM_REQUIREMENTS = {
    'tiny': 1.0,
    'base': 1.0,
    'small': 2.0,
    'medium': 5.0,
    'large': 10.0,
    'turbo': 6.0,
}

# All models ordered by size/quality
ALL_MODELS = ['tiny', 'base', 'small', 'medium', 'large', 'turbo']

# CPU-only safe models (can run reasonably on CPU)
CPU_SAFE_MODELS = ['tiny', 'base', 'small']


def get_gpu_memory_gb():
    """
    Detect available GPU memory in GB.
    Returns None if no CUDA GPU is available.
    """
    try:
        import torch
        if not torch.cuda.is_available():
            logger.info("CUDA not available")
            return None

        # Get total memory of the first CUDA device
        device = torch.cuda.current_device()
        total_memory = torch.cuda.get_device_properties(device).total_memory
        total_gb = total_memory / (1024 ** 3)

        logger.info(f"Detected GPU: {torch.cuda.get_device_name(device)}")
        logger.info(f"GPU memory: {total_gb:.1f} GB")

        return total_gb

    except ImportError:
        logger.info("PyTorch not available, assuming CPU-only")
        return None
    except Exception as e:
        logger.warning(f"Error detecting GPU: {e}")
        return None


def get_available_models(gpu_memory_gb=None):
    """
    Get list of models that can run on the current hardware.

    Args:
        gpu_memory_gb: GPU memory in GB, or None for CPU-only

    Returns:
        List of model names that should work on this hardware
    """
    if gpu_memory_gb is None:
        # CPU-only mode - only small models are practical
        logger.info("CPU-only mode: limiting to small models")
        return CPU_SAFE_MODELS.copy()

    # Filter models based on available VRAM
    # Add 1GB safety margin
    available = []
    for model in ALL_MODELS:
        required = MODEL_VRAM_REQUIREMENTS.get(model, 10.0)
        if required + 1.0 <= gpu_memory_gb:
            available.append(model)

    if not available:
        # At minimum, tiny should always work
        available = ['tiny']

    logger.info(f"Available models for {gpu_memory_gb:.1f}GB VRAM: {available}")
    return available


def get_default_model(available_models):
    """
    Get the best default model from available models.
    Prefers 'turbo' > 'base' > first available.
    """
    if 'turbo' in available_models:
        return 'turbo'
    if 'base' in available_models:
        return 'base'
    if available_models:
        return available_models[0]
    return 'tiny'


def detect_and_configure(force_cpu=False):
    """
    Detect GPU and return configuration dict.

    Args:
        force_cpu: If True, ignore GPU and configure for CPU-only mode

    Returns:
        dict with keys:
            - gpu_memory_gb: float or None
            - available_models: list of model names
            - default_model: recommended default model
    """
    if force_cpu:
        logger.info("Force CPU mode enabled, skipping GPU detection")
        gpu_memory = None
    else:
        gpu_memory = get_gpu_memory_gb()
    available = get_available_models(gpu_memory)
    default = get_default_model(available)

    return {
        'gpu_memory_gb': gpu_memory,
        'available_models': available,
        'default_model': default,
    }
