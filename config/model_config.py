"""
模型配置文件
管理语义检索模型的下载和使用
"""

import os

# 模型配置
SEMANTIC_MODEL_CONFIG = {
    # 默认使用的模型（轻量级，支持中文）
    "default": "paraphrase-multilingual-MiniLM-L12-v2",
    
    # 备选模型列表（按优先级排序）
    "fallback_models": [
        "paraphrase-multilingual-MiniLM-L12-v2",  # 384维，快速
        "distiluse-base-multilingual-cased-v2",    # 512维，多语言
        "all-MiniLM-L6-v2",                        # 384维，英文为主
    ],
    
    # 本地模型缓存目录
    "cache_folder": os.path.join(
        os.path.dirname(__file__), 
        "..", 
        "models", 
        "sentence_transformers"
    ),
    
    # 是否使用本地模型（如果为True，不会尝试在线下载）
    "offline_mode": False,
    
    # 是否启用语义检索（如果为False，使用简单的关键词检索）
    "enable_semantic_retrieval": True,
    
    # 模型加载超时时间（秒）
    "load_timeout": 300,
    
    # 是否使用GPU
    "use_gpu": False,
}


def get_model_cache_path(model_name: str = None) -> str:
    """获取模型缓存路径"""
    if model_name is None:
        model_name = SEMANTIC_MODEL_CONFIG["default"]
    
    cache_folder = SEMANTIC_MODEL_CONFIG["cache_folder"]
    os.makedirs(cache_folder, exist_ok=True)
    return cache_folder


def should_use_semantic_retrieval() -> bool:
    """判断是否应该使用语义检索"""
    return SEMANTIC_MODEL_CONFIG["enable_semantic_retrieval"]


def get_offline_mode() -> bool:
    """判断是否使用离线模式"""
    return SEMANTIC_MODEL_CONFIG["offline_mode"]
