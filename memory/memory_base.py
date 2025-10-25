"""
记忆系统基础模块
包含向量化编码和相似度计算等核心功能
"""

import numpy as np
from typing import List, Dict, Any, Union, Optional
from abc import ABC, abstractmethod
import logging

# 简化版的向量编码器（避免大型依赖）
class SimpleMemoryEncoder:
    """简化版记忆编码器，使用TF-IDF进行向量化"""
    
    def __init__(self):
        self.vocabulary = {}
        self.idf_scores = {}
        self.vocab_size = 0
        
    def build_vocabulary(self, texts: List[str]):
        """构建词汇表"""
        word_counts = {}
        doc_counts = {}
        
        # 统计词频和文档频率
        for text in texts:
            words = self._tokenize(text)
            word_set = set(words)
            
            for word in words:
                word_counts[word] = word_counts.get(word, 0) + 1
            
            for word in word_set:
                doc_counts[word] = doc_counts.get(word, 0) + 1
        
        # 构建词汇表
        self.vocabulary = {word: idx for idx, word in enumerate(word_counts.keys())}
        self.vocab_size = len(self.vocabulary)
        
        # 计算IDF分数
        total_docs = len(texts)
        for word, count in doc_counts.items():
            self.idf_scores[word] = np.log(total_docs / (count + 1))
    
    def encode(self, text: str) -> np.ndarray:
        """将文本编码为向量"""
        words = self._tokenize(text)
        vector = np.zeros(self.vocab_size)
        
        # 计算词频
        word_counts = {}
        for word in words:
            word_counts[word] = word_counts.get(word, 0) + 1
        
        # 计算TF-IDF向量
        total_words = len(words)
        for word, count in word_counts.items():
            if word in self.vocabulary:
                tf = count / total_words
                idf = self.idf_scores.get(word, 0)
                vector[self.vocabulary[word]] = tf * idf
        
        # 归一化
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
            
        return vector
    
    def _tokenize(self, text: str) -> List[str]:
        """简单的分词"""
        import re
        # 简单的中英文分词
        text = text.lower()
        words = re.findall(r'[\w\u4e00-\u9fff]+', text)
        return words

class MemoryEncoder:
    """记忆编码器接口"""
    
    def __init__(self, use_simple_encoder=True):
        if use_simple_encoder:
            self.encoder = SimpleMemoryEncoder()
        else:
            try:
                from sentence_transformers import SentenceTransformer
                self.encoder = SentenceTransformer('all-MiniLM-L6-v2')
            except ImportError:
                logging.warning("sentence-transformers not available, using simple encoder")
                self.encoder = SimpleMemoryEncoder()
        
        self.is_simple = isinstance(self.encoder, SimpleMemoryEncoder)
        self._is_trained = False
    
    def encode_concepts(self, concepts: Union[str, List[str]]) -> np.ndarray:
        """编码概念为向量"""
        if isinstance(concepts, list):
            text = " ".join(concepts)
        else:
            text = concepts
            
        if self.is_simple:
            if not self._is_trained:
                # 需要先训练简单编码器
                return np.random.rand(100)  # 返回随机向量作为备用
            return self.encoder.encode(text)
        else:
            return self.encoder.encode(text)
    
    def train_encoder(self, training_texts: List[str]):
        """训练编码器（仅对简单编码器有效）"""
        if self.is_simple:
            self.encoder.build_vocabulary(training_texts)
            self._is_trained = True

class SimilarityCalculator:
    """相似度计算器"""
    
    @staticmethod
    def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
        """计算余弦相似度"""
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    @staticmethod
    def euclidean_distance(vec1: np.ndarray, vec2: np.ndarray) -> float:
        """计算欧几里得距离"""
        return np.linalg.norm(vec1 - vec2)
    
    @staticmethod
    def manhattan_distance(vec1: np.ndarray, vec2: np.ndarray) -> float:
        """计算曼哈顿距离"""
        return np.sum(np.abs(vec1 - vec2))
    
    @staticmethod
    def semantic_similarity(concepts1: List[str], concepts2: List[str]) -> float:
        """计算概念间的语义相似度"""
        # 简单的集合相似度计算
        set1 = set(concepts1)
        set2 = set(concepts2)
        
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        
        if union == 0:
            return 0.0
        
        return intersection / union

class MemoryMetrics:
    """记忆系统性能指标"""
    
    def __init__(self):
        self.retrieval_times = []
        self.similarity_scores = []
        self.cache_hits = 0
        self.cache_misses = 0
    
    def record_retrieval_time(self, time_ms: float):
        """记录检索时间"""
        self.retrieval_times.append(time_ms)
    
    def record_similarity_score(self, score: float):
        """记录相似度分数"""
        self.similarity_scores.append(score)
    
    def record_cache_hit(self):
        """记录缓存命中"""
        self.cache_hits += 1
    
    def record_cache_miss(self):
        """记录缓存未命中"""
        self.cache_misses += 1
    
    def get_average_retrieval_time(self) -> float:
        """获取平均检索时间"""
        if not self.retrieval_times:
            return 0.0
        return sum(self.retrieval_times) / len(self.retrieval_times)
    
    def get_cache_hit_rate(self) -> float:
        """获取缓存命中率"""
        total = self.cache_hits + self.cache_misses
        if total == 0:
            return 0.0
        return self.cache_hits / total
    
    def get_average_similarity(self) -> float:
        """获取平均相似度"""
        if not self.similarity_scores:
            return 0.0
        return sum(self.similarity_scores) / len(self.similarity_scores)