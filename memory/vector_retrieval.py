"""
向量检索引擎
支持语义相似度搜索和智能检索
"""

import numpy as np
import pickle
import os
from typing import List, Dict, Any, Optional, Tuple, Union
from datetime import datetime
import logging
from collections import defaultdict

from .memory_base import MemoryEncoder, SimilarityCalculator, MemoryMetrics
from .case_library import Case

class VectorIndex:
    """向量索引系统"""
    
    def __init__(self, dimension: int = 100):
        self.dimension = dimension
        self.vectors = {}  # id -> vector
        self.metadata = {}  # id -> metadata
        self.clusters = {}  # cluster_id -> [ids]
        self.inverted_index = defaultdict(list)  # term -> [ids]
        
    def add_vector(self, vector_id: str, vector: np.ndarray, metadata: Dict[str, Any] = None):
        """添加向量到索引"""
        if vector.shape[0] != self.dimension:
            # 如果维度不匹配，调整向量维度
            vector = self._adjust_dimension(vector)
            
        self.vectors[vector_id] = vector
        self.metadata[vector_id] = metadata or {}
        
        # 更新倒排索引
        if metadata and 'keywords' in metadata:
            for keyword in metadata['keywords']:
                self.inverted_index[keyword].append(vector_id)
    
    def remove_vector(self, vector_id: str):
        """从索引中移除向量"""
        if vector_id in self.vectors:
            del self.vectors[vector_id]
            
        if vector_id in self.metadata:
            # 从倒排索引中移除
            metadata = self.metadata[vector_id]
            if 'keywords' in metadata:
                for keyword in metadata['keywords']:
                    if vector_id in self.inverted_index[keyword]:
                        self.inverted_index[keyword].remove(vector_id)
            del self.metadata[vector_id]
    
    def search_similar(self, query_vector: np.ndarray, top_k: int = 10, threshold: float = 0.5) -> List[Tuple[str, float]]:
        """搜索相似向量"""
        if query_vector.shape[0] != self.dimension:
            query_vector = self._adjust_dimension(query_vector)
            
        similarities = []
        for vector_id, vector in self.vectors.items():
            similarity = SimilarityCalculator.cosine_similarity(query_vector, vector)
            if similarity >= threshold:
                similarities.append((vector_id, similarity))
        
        # 按相似度排序
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]
    
    def search_by_keywords(self, keywords: List[str]) -> List[str]:
        """根据关键词搜索"""
        candidate_ids = set()
        for keyword in keywords:
            candidate_ids.update(self.inverted_index.get(keyword, []))
        return list(candidate_ids)
    
    def _adjust_dimension(self, vector: np.ndarray) -> np.ndarray:
        """调整向量维度"""
        current_dim = vector.shape[0]
        if current_dim > self.dimension:
            # 截断
            return vector[:self.dimension]
        elif current_dim < self.dimension:
            # 补零
            padded = np.zeros(self.dimension)
            padded[:current_dim] = vector
            return padded
        return vector
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取索引统计信息"""
        return {
            "total_vectors": len(self.vectors),
            "dimension": self.dimension,
            "total_keywords": len(self.inverted_index),
            "average_vector_norm": np.mean([np.linalg.norm(v) for v in self.vectors.values()]) if self.vectors else 0
        }

class SemanticCache:
    """语义缓存系统"""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.cache = {}  # query_hash -> (result, timestamp, access_count)
        self.access_order = []  # LRU tracking
        
    def get(self, query_vector: np.ndarray) -> Optional[List[Tuple[str, float]]]:
        """从缓存获取结果"""
        query_hash = self._hash_vector(query_vector)
        if query_hash in self.cache:
            result, timestamp, access_count = self.cache[query_hash]
            # 更新访问信息
            self.cache[query_hash] = (result, timestamp, access_count + 1)
            # 更新LRU顺序
            if query_hash in self.access_order:
                self.access_order.remove(query_hash)
            self.access_order.append(query_hash)
            return result
        return None
    
    def put(self, query_vector: np.ndarray, result: List[Tuple[str, float]]):
        """存储结果到缓存"""
        query_hash = self._hash_vector(query_vector)
        
        # 检查是否需要清理缓存
        if len(self.cache) >= self.max_size:
            self._evict_lru()
        
        self.cache[query_hash] = (result, datetime.now(), 1)
        self.access_order.append(query_hash)
    
    def _hash_vector(self, vector: np.ndarray) -> str:
        """计算向量哈希值"""
        # 简化的向量哈希
        return str(hash(vector.tobytes()))
    
    def _evict_lru(self):
        """清理最少使用的缓存项"""
        if self.access_order:
            lru_hash = self.access_order.pop(0)
            if lru_hash in self.cache:
                del self.cache[lru_hash]

class VectorRetrievalEngine:
    """向量检索引擎主类"""
    
    def __init__(self, 
                 encoder: Optional[MemoryEncoder] = None,
                 index_dimension: int = 100,
                 cache_size: int = 1000):
        
        self.encoder = encoder or MemoryEncoder()
        self.index = VectorIndex(index_dimension)
        self.cache = SemanticCache(cache_size)
        self.metrics = MemoryMetrics()
        
        # 检索配置
        self.default_threshold = 0.5
        self.default_top_k = 10
        
    def add_document(self, 
                    doc_id: str, 
                    content: str, 
                    metadata: Dict[str, Any] = None):
        """添加文档到检索引擎"""
        
        # 编码文档内容
        vector = self.encoder.encode_concepts(content)
        
        # 提取关键词
        keywords = self._extract_keywords(content)
        doc_metadata = metadata or {}
        doc_metadata['keywords'] = keywords
        doc_metadata['content'] = content
        doc_metadata['added_at'] = datetime.now().isoformat()
        
        # 添加到索引
        self.index.add_vector(doc_id, vector, doc_metadata)
        
        logging.info(f"Added document {doc_id} to vector index")
    
    def add_case(self, case: Case):
        """添加案例到检索引擎"""
        content = f"{case.problem_description} {case.solution}"
        metadata = {
            'case_id': case.id,
            'tags': case.tags,
            'difficulty_level': case.difficulty_level,
            'success_score': case.success_score,
            'timestamp': case.timestamp.isoformat()
        }
        
        self.add_document(case.id, content, metadata)
    
    def search(self, 
               query: str, 
               top_k: int = None, 
               threshold: float = None,
               use_cache: bool = True) -> List[Tuple[str, float, Dict[str, Any]]]:
        """搜索相关文档"""
        
        start_time = datetime.now()
        top_k = top_k or self.default_top_k
        threshold = threshold or self.default_threshold
        
        # 编码查询
        query_vector = self.encoder.encode_concepts(query)
        
        # 检查缓存
        if use_cache:
            cached_result = self.cache.get(query_vector)
            if cached_result is not None:
                self.metrics.record_cache_hit()
                self.metrics.record_retrieval_time(
                    (datetime.now() - start_time).total_seconds() * 1000
                )
                # 添加元数据
                enhanced_result = []
                for doc_id, similarity in cached_result:
                    metadata = self.index.metadata.get(doc_id, {})
                    enhanced_result.append((doc_id, similarity, metadata))
                return enhanced_result
            else:
                self.metrics.record_cache_miss()
        
        # 向量搜索
        similar_docs = self.index.search_similar(query_vector, top_k, threshold)
        
        # 缓存结果
        if use_cache:
            self.cache.put(query_vector, similar_docs)
        
        # 添加元数据和记录指标
        enhanced_result = []
        for doc_id, similarity in similar_docs:
            metadata = self.index.metadata.get(doc_id, {})
            enhanced_result.append((doc_id, similarity, metadata))
            self.metrics.record_similarity_score(similarity)
        
        # 记录检索时间
        retrieval_time = (datetime.now() - start_time).total_seconds() * 1000
        self.metrics.record_retrieval_time(retrieval_time)
        
        logging.info(f"Search completed: {len(enhanced_result)} results in {retrieval_time:.2f}ms")
        return enhanced_result
    
    def hybrid_search(self, 
                     query: str,
                     keywords: List[str] = None,
                     filters: Dict[str, Any] = None,
                     top_k: int = None) -> List[Tuple[str, float, Dict[str, Any]]]:
        """混合搜索（向量+关键词+过滤器）"""
        
        top_k = top_k or self.default_top_k
        
        # 向量搜索
        vector_results = self.search(query, top_k * 2, use_cache=False)  # 获取更多候选
        
        # 关键词搜索
        keyword_candidates = set()
        if keywords:
            keyword_candidates.update(self.index.search_by_keywords(keywords))
        
        # 合并和重排序
        combined_results = []
        for doc_id, similarity, metadata in vector_results:
            score = similarity
            
            # 关键词匹配加分
            if keywords and doc_id in keyword_candidates:
                score += 0.1  # 关键词匹配奖励
            
            # 应用过滤器
            if self._apply_filters(metadata, filters):
                combined_results.append((doc_id, score, metadata))
        
        # 按综合分数排序
        combined_results.sort(key=lambda x: x[1], reverse=True)
        return combined_results[:top_k]
    
    def find_similar_cases(self, 
                          case: Case, 
                          top_k: int = 5) -> List[Tuple[str, float, Dict[str, Any]]]:
        """找到与给定案例相似的案例"""
        
        query = f"{case.problem_description} {case.solution}"
        
        # 过滤器：排除自身，相似难度级别
        filters = {
            'exclude_ids': [case.id],
            'difficulty_range': (case.difficulty_level - 1, case.difficulty_level + 1)
        }
        
        return self.hybrid_search(query, case.tags, filters, top_k)
    
    def recommend_cases(self, 
                       student_context: Dict[str, Any],
                       current_problem: str,
                       top_k: int = 3) -> List[Tuple[str, float, Dict[str, Any]]]:
        """为学生推荐相关案例"""
        
        # 构建查询
        query = current_problem
        
        # 基于学生上下文的过滤器
        filters = {
            'difficulty_range': (1, student_context.get('max_difficulty', 5)),
            'min_success_score': 0.6  # 推荐成功率较高的案例
        }
        
        # 从学生历史中提取关键词
        keywords = student_context.get('relevant_concepts', [])
        
        return self.hybrid_search(query, keywords, filters, top_k)
    
    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        # 简单的关键词提取
        import re
        words = re.findall(r'[\w\u4e00-\u9fff]+', text.lower())
        
        # 过滤常见停用词
        stop_words = {'的', '是', '在', '了', '和', 'the', 'is', 'at', 'and', 'or', 'but'}
        keywords = [word for word in words if word not in stop_words and len(word) > 1]
        
        # 返回唯一的关键词
        return list(set(keywords))
    
    def _apply_filters(self, metadata: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """应用过滤器"""
        if not filters:
            return True
        
        # 排除特定ID
        if 'exclude_ids' in filters:
            if metadata.get('case_id') in filters['exclude_ids']:
                return False
        
        # 难度范围过滤
        if 'difficulty_range' in filters:
            min_diff, max_diff = filters['difficulty_range']
            case_difficulty = metadata.get('difficulty_level', 1)
            if not (min_diff <= case_difficulty <= max_diff):
                return False
        
        # 最小成功率过滤
        if 'min_success_score' in filters:
            min_score = filters['min_success_score']
            case_score = metadata.get('success_score', 0.0)
            if case_score < min_score:
                return False
        
        # 标签过滤
        if 'required_tags' in filters:
            required_tags = set(filters['required_tags'])
            case_tags = set(metadata.get('tags', []))
            if not required_tags.intersection(case_tags):
                return False
        
        return True
    
    def remove_document(self, doc_id: str):
        """移除文档"""
        self.index.remove_vector(doc_id)
        logging.info(f"Removed document {doc_id} from vector index")
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取检索引擎统计信息"""
        index_stats = self.index.get_statistics()
        cache_hit_rate = self.metrics.get_cache_hit_rate()
        avg_retrieval_time = self.metrics.get_average_retrieval_time()
        avg_similarity = self.metrics.get_average_similarity()
        
        return {
            **index_stats,
            "cache_hit_rate": cache_hit_rate,
            "average_retrieval_time_ms": avg_retrieval_time,
            "average_similarity_score": avg_similarity,
            "total_searches": len(self.metrics.similarity_scores)
        }
    
    def save_index(self, filepath: str):
        """保存索引到文件"""
        index_data = {
            'vectors': self.index.vectors,
            'metadata': self.index.metadata,
            'inverted_index': dict(self.index.inverted_index),
            'dimension': self.index.dimension,
            'saved_at': datetime.now().isoformat()
        }
        
        with open(filepath, 'wb') as f:
            pickle.dump(index_data, f)
        
        logging.info(f"Saved vector index to {filepath}")
    
    def load_index(self, filepath: str):
        """从文件加载索引"""
        try:
            with open(filepath, 'rb') as f:
                index_data = pickle.load(f)
            
            self.index.vectors = index_data['vectors']
            self.index.metadata = index_data['metadata']
            self.index.inverted_index = defaultdict(list, index_data['inverted_index'])
            self.index.dimension = index_data['dimension']
            
            logging.info(f"Loaded vector index from {filepath}")
            
        except FileNotFoundError:
            logging.warning(f"Vector index file {filepath} not found")
        except Exception as e:
            logging.error(f"Error loading vector index: {e}")