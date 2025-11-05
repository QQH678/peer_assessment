#!/usr/bin/env python3
"""
自动下载推荐的语义检索模型
"""

import os
import sys
import logging
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    print("❌ sentence-transformers 未安装")
    print("请运行: pip install sentence-transformers torch")
    sys.exit(1)


def download_model(model_name: str, cache_folder: str) -> bool:
    """下载并缓存模型"""
    try:
        print(f"\n📥 正在下载模型: {model_name}")
        print(f"   缓存目录: {cache_folder}")
        
        model = SentenceTransformer(
            model_name,
            cache_folder=cache_folder,
            device='cpu'
        )
        
        # 测试编码
        test_text = "这是一个测试句子 This is a test sentence"
        embedding = model.encode(test_text)
        
        print(f"✅ 模型下载成功!")
        print(f"   维度: {len(embedding)}")
        print(f"   位置: {os.path.join(cache_folder, model_name.replace('/', '_'))}")
        return True
        
    except Exception as e:
        print(f"❌ 模型下载失败: {e}")
        return False


def main():
    """主函数"""
    print("=" * 60)
    print("自动下载推荐的语义检索模型")
    print("=" * 60)
    
    # 设置缓存目录
    cache_folder = os.path.join(
        os.path.dirname(__file__),
        "models",
        "sentence_transformers"
    )
    os.makedirs(cache_folder, exist_ok=True)
    
    print(f"\n模型将被下载到: {cache_folder}")
    
    # 下载推荐模型
    model_name = "paraphrase-multilingual-MiniLM-L12-v2"
    print(f"\n正在下载推荐模型: {model_name}")
    print("说明: 多语言模型，支持中文，384维，约420MB")
    
    success = download_model(model_name, cache_folder)
    
    if success:
        print("\n" + "=" * 60)
        print("✅ 模型下载完成!")
        print("=" * 60)
        print("\n现在可以运行主程序，模型将从本地缓存加载。")
        print("如果网络不稳定，模型会自动使用已缓存的版本。")
        return 0
    else:
        print("\n" + "=" * 60)
        print("❌ 模型下载失败")
        print("=" * 60)
        print("\n建议:")
        print("1. 检查网络连接")
        print("2. 使用镜像站点: export HF_ENDPOINT=https://hf-mirror.com")
        print("3. 查看 MODEL_SETUP_GUIDE.md 了解手动下载方法")
        return 1


if __name__ == "__main__":
    sys.exit(main())
