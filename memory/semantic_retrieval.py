"""
升级版记忆系统 - 语义向量检索
使用 sentence-transformers 实现真正的语义理解
"""

import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import logging
import os
import time

# 在导入 SentenceTransformer 之前设置离线模式环境变量
# 这样可以防止它尝试联网验证模型
os.environ['TRANSFORMERS_OFFLINE'] = '1'
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['HF_DATASETS_OFFLINE'] = '1'

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logging.warning("sentence-transformers not installed. Install with: pip install sentence-transformers")

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    logging.warning("faiss not installed. Install with: pip install faiss-cpu")


def load_model_with_retry(model_name: str, cache_folder: str, max_retries: int = 1, timeout: int = 120) -> Optional[SentenceTransformer]:
    """
    带重试机制的模型加载器 - 优先使用本地缓存，完全离线
    
    Args:
        model_name: 模型名称
        cache_folder: 缓存目录
        max_retries: 最大重试次数（默认1次，因为本地加载应该立即成功）
        timeout: 每次尝试的超时时间（秒）
    
    Returns:
        加载的模型或None
    """
    # 支持多种本地缓存路径格式
    # 格式1: 直接目录 {cache_folder}/{model_name}
    direct_path = os.path.join(cache_folder, model_name)
    # 格式2: HuggingFace标准格式 {cache_folder}/models--sentence-transformers--{model_name}
    hf_cache_path = os.path.join(cache_folder, f"models--sentence-transformers--{model_name}")
    
    # 检查哪个路径存在
    if os.path.exists(direct_path):
        logging.info(f"Found model in direct format: {direct_path}")
        try:
            model = SentenceTransformer(direct_path, device='cpu')
            logging.info(f"✓ Successfully loaded model from: {direct_path}")
            return model
        except Exception as e:
            logging.error(f"Failed to load model from {direct_path}: {e}")
    
    elif os.path.exists(hf_cache_path):
        logging.info(f"Found model in HuggingFace cache format: {hf_cache_path}")
        try:
            # 对于HuggingFace缓存格式，需要使用模型名称 + cache_folder参数
            # SentenceTransformer会自动在cache_folder中查找HF格式的缓存
            logging.info(f"Loading from HF cache using model name: {model_name}")
            model = SentenceTransformer(model_name, cache_folder=cache_folder, device='cpu')
            logging.info(f"✓ Successfully loaded model from HF cache")
            return model
        except Exception as e:
            logging.error(f"Failed to load model from HF cache: {e}")
            # 如果上面失败了，尝试直接使用snapshots路径
            try:
                snapshots_dir = os.path.join(hf_cache_path, "snapshots")
                if os.path.exists(snapshots_dir):
                    # 找到最新的snapshot
                    snapshots = os.listdir(snapshots_dir)
                    if snapshots:
                        latest_snapshot = os.path.join(snapshots_dir, snapshots[0])
                        logging.info(f"Trying snapshot path: {latest_snapshot}")
                        model = SentenceTransformer(latest_snapshot, device='cpu')
                        logging.info(f"✓ Successfully loaded model from snapshot")
                        return model
            except Exception as e2:
                logging.error(f"Failed to load from snapshot: {e2}")
    
    # 如果本地没有模型，给出明确提示
    logging.error(f"Model {model_name} not found in cache folder: {cache_folder}")
    logging.error(f"Expected paths:")
    logging.error(f"  - {direct_path}")
    logging.error(f"  - {hf_cache_path}")
    logging.error(f"Please run: python auto_download_model.py")
    return None


class SemanticEncoder:
    """语义编码器 - 使用预训练模型进行语义向量化"""
    
    def __init__(self, model_name: str = "paraphrase-multilingual-MiniLM-L12-v2", 
                 cache_folder: Optional[str] = None,
                 fallback_models: Optional[List[str]] = None):
        """
        初始化语义编码器
        
        推荐模型：
        - paraphrase-multilingual-MiniLM-L12-v2: 支持中文，维度384，速度快
        - paraphrase-multilingual-mpnet-base-v2: 支持中文，维度768，效果更好
        - distiluse-base-multilingual-cased-v2: 多语言，维度512
        - all-MiniLM-L6-v2: 英文，维度384，非常快
        
        Args:
            model_name: 模型名称或本地路径
            cache_folder: 模型缓存目录，默认为 ./models/sentence_transformers
            fallback_models: 备选模型列表（如果主模型加载失败）
        """
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            raise ImportError(
                "sentence-transformers is required. "
                "Install with: pip install sentence-transformers"
            )
        
        # 设置缓存目录
        if cache_folder is None:
            cache_folder = os.path.join(os.path.dirname(__file__), "..", "models", "sentence_transformers")
        
        os.makedirs(cache_folder, exist_ok=True)
        
        self.cache_folder = cache_folder
        
        # 只尝试加载主模型（已下载的模型）
        logging.info(f"Loading model: {model_name} from {cache_folder}")
        self.model = load_model_with_retry(model_name, cache_folder, max_retries=1)
        
        if self.model is None:
            raise RuntimeError(
                f"Failed to load semantic model: {model_name}. "
                f"Please ensure the model is downloaded to {cache_folder}. "
                f"Run: python auto_download_model.py"
            )
        
        self.model_name = model_name
        self.dimension = self.model.get_sentence_embedding_dimension()
        logging.info(f"✓ Semantic encoder ready: {self.model_name}, dimension={self.dimension}")
    
    def encode(self, text: str) -> np.ndarray:
        """编码单个文本"""
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.astype(np.float32)
    
    def encode_batch(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """批量编码文本"""
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            convert_to_numpy=True,
            show_progress_bar=len(texts) > 100
        )
        return embeddings.astype(np.float32)
    
    def get_dimension(self) -> int:
        """获取向量维度"""
        return self.dimension


class FAISSVectorIndex:
    """基于FAISS的高性能向量索引"""
    
    def __init__(self, dimension: int, use_gpu: bool = False):
        """
        初始化FAISS索引
        
        Args:
            dimension: 向量维度
            use_gpu: 是否使用GPU加速（需要安装faiss-gpu）
        """
        if not FAISS_AVAILABLE:
            raise ImportError(
                "faiss is required for high-performance search. "
                "Install with: pip install faiss-cpu (or faiss-gpu for GPU support)"
            )
        
        self.dimension = dimension
        self.use_gpu = use_gpu
        
        # 创建索引（使用内积相似度，相当于余弦相似度对于归一化向量）
        self.index = faiss.IndexFlatIP(dimension)  # Inner Product
        
        # 如果使用GPU
        if use_gpu and faiss.get_num_gpus() > 0:
            res = faiss.StandardGpuResources()
            self.index = faiss.index_cpu_to_gpu(res, 0, self.index)
            logging.info("FAISS index using GPU")
        
        self.id_map = []  # 索引位置 -> ID映射
        self.metadata_map = {}  # ID -> metadata
        
    def add_vectors(self, ids: List[str], vectors: np.ndarray, metadata: List[Dict] = None):
        """批量添加向量"""
        # 归一化向量（用于余弦相似度）
        vectors = self._normalize_vectors(vectors)
        
        # 添加到索引
        self.index.add(vectors)
        
        # 更新映射
        for i, id in enumerate(ids):
            self.id_map.append(id)
            if metadata:
                self.metadata_map[id] = metadata[i]
    
    def search(self, query_vector: np.ndarray, top_k: int = 10) -> List[Tuple[str, float]]:
        """搜索最相似的向量"""
        # 检查索引是否为空
        if self.index.ntotal == 0 or len(self.id_map) == 0:
            return []
        
        # 归一化查询向量
        query_vector = self._normalize_vectors(query_vector.reshape(1, -1))
        
        # 搜索
        similarities, indices = self.index.search(query_vector, min(top_k, self.index.ntotal))
        
        # 构建结果
        results = []
        for sim, idx in zip(similarities[0], indices[0]):
            if idx >= 0 and idx < len(self.id_map):  # 检查索引有效性
                results.append((self.id_map[idx], float(sim)))
        
        return results
    
    def _normalize_vectors(self, vectors: np.ndarray) -> np.ndarray:
        """归一化向量"""
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1  # 避免除零
        return vectors / norms
    
    def get_size(self) -> int:
        """获取索引大小"""
        return self.index.ntotal
    
    def save(self, filepath: str):
        """保存索引"""
        faiss.write_index(faiss.index_gpu_to_cpu(self.index) if self.use_gpu else self.index, 
                         filepath)
        
    def load(self, filepath: str):
        """加载索引"""
        self.index = faiss.read_index(filepath)
        if self.use_gpu and faiss.get_num_gpus() > 0:
            res = faiss.StandardGpuResources()
            self.index = faiss.index_cpu_to_gpu(res, 0, self.index)


class NumpyVectorIndex:
    """基于Numpy的简单向量索引（无需FAISS依赖）"""
    
    def __init__(self, dimension: int):
        self.dimension = dimension
        self.vectors = []
        self.id_map = []
        self.metadata_map = {}
    
    def add_vectors(self, ids: List[str], vectors: np.ndarray, metadata: List[Dict] = None):
        """批量添加向量"""
        for i, id in enumerate(ids):
            self.vectors.append(vectors[i])
            self.id_map.append(id)
            if metadata:
                self.metadata_map[id] = metadata[i]
    
    def search(self, query_vector: np.ndarray, top_k: int = 10) -> List[Tuple[str, float]]:
        """搜索最相似的向量"""
        if not self.vectors or len(self.id_map) == 0:
            return []
        
        vectors = np.array(self.vectors)
        
        # 归一化
        query_norm = query_vector / (np.linalg.norm(query_vector) + 1e-8)
        vectors_norm = vectors / (np.linalg.norm(vectors, axis=1, keepdims=True) + 1e-8)
        
        # 计算余弦相似度
        similarities = np.dot(vectors_norm, query_norm)
        
        # 获取top_k
        top_k = min(top_k, len(self.vectors))  # 确保top_k不超过向量数量
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            if idx < len(self.id_map):  # 安全检查
                results.append((self.id_map[idx], float(similarities[idx])))
        
        return results
    
    def get_size(self) -> int:
        return len(self.vectors)


class SemanticVectorRetrieval:
    """语义向量检索引擎"""
    
    def __init__(self, 
                 encoder: SemanticEncoder,
                 use_faiss: bool = None,
                 use_gpu: bool = False):
        """
        初始化语义检索引擎
        
        Args:
            encoder: 语义编码器
            use_faiss: 是否使用FAISS（None则自动判断）
            use_gpu: 是否使用GPU
        """
        self.encoder = encoder
        self.dimension = encoder.get_dimension()
        
        # 自动判断是否使用FAISS
        if use_faiss is None:
            use_faiss = FAISS_AVAILABLE
        
        # 创建索引
        if use_faiss:
            try:
                self.index = FAISSVectorIndex(self.dimension, use_gpu)
                self.index_type = "FAISS"
                logging.info("Using FAISS index for high-performance search")
            except Exception as e:
                logging.warning(f"Failed to create FAISS index: {e}, falling back to Numpy")
                self.index = NumpyVectorIndex(self.dimension)
                self.index_type = "Numpy"
        else:
            self.index = NumpyVectorIndex(self.dimension)
            self.index_type = "Numpy"
        
        # 缓存
        self.query_cache = {}
        self.cache_size = 1000
        
        # 统计
        self.stats = {
            "total_retrievals": 0,
            "cache_hits": 0,
            "average_retrieval_time": 0.0
        }
    
    def add_case(self, case_id: str, case_data: Dict[str, Any]):
        """添加案例到索引"""
        # 构建文本表示
        text = self._build_text_representation(case_data)
        
        # 编码
        vector = self.encoder.encode(text)
        
        # 添加到索引
        self.index.add_vectors([case_id], vector.reshape(1, -1), [case_data])
    
    def add_cases_batch(self, cases: List[Tuple[str, Dict[str, Any]]]):
        """批量添加案例"""
        if not cases:
            return
        
        ids = [case_id for case_id, _ in cases]
        texts = [self._build_text_representation(case_data) for _, case_data in cases]
        metadata = [case_data for _, case_data in cases]
        
        # 批量编码
        vectors = self.encoder.encode_batch(texts)
        
        # 添加到索引
        self.index.add_vectors(ids, vectors, metadata)
    
    def retrieve(self, 
                query: str,
                top_k: int = 5,
                use_cache: bool = True) -> List[Tuple[str, float, Dict]]:
        """
        检索相关案例
        
        Returns:
            List of (case_id, similarity_score, case_data)
        """
        start_time = datetime.now()
        
        # 检查缓存
        if use_cache and query in self.query_cache:
            self.stats["cache_hits"] += 1
            return self.query_cache[query]
        
        # 编码查询
        query_vector = self.encoder.encode(query)
        
        # 搜索
        results = self.index.search(query_vector, top_k)
        
        # 添加metadata
        full_results = []
        for case_id, similarity in results:
            metadata = self.index.metadata_map.get(case_id, {})
            full_results.append((case_id, similarity, metadata))
        
        # 更新缓存
        if use_cache:
            if len(self.query_cache) >= self.cache_size:
                # 简单的FIFO策略
                self.query_cache.pop(next(iter(self.query_cache)))
            self.query_cache[query] = full_results
        
        # 更新统计
        self.stats["total_retrievals"] += 1
        retrieval_time = (datetime.now() - start_time).total_seconds()
        self.stats["average_retrieval_time"] = (
            (self.stats["average_retrieval_time"] * (self.stats["total_retrievals"] - 1) + retrieval_time)
            / self.stats["total_retrievals"]
        )
        
        return full_results
    
    def retrieve_with_context(self,
                             query: str,
                             context: Dict[str, Any],
                             top_k: int = 5) -> Dict[str, Any]:
        """
        带上下文的检索（增强版）
        
        考虑：
        - 知识点匹配
        - 难度匹配
        - 历史成功率
        """
        # 基础检索
        base_results = self.retrieve(query, top_k * 2)  # 先检索更多候选
        
        # 如果没有结果，返回空
        if not base_results:
            return {
                "retrieved_cases": [],
                "similarity_scores": [],
                "case_ids": [],
                "confidence_level": 0.0,
                "explanation": "索引为空，暂无可检索案例",
                "retrieval_time_ms": 0.0
            }
        
        # 重排序（结合上下文）
        reranked_results = self._rerank_with_context(base_results, context)
        
        # 计算置信度
        confidence = self._calculate_confidence(reranked_results, context)
        
        # 生成解释
        explanation = self._generate_explanation(reranked_results, context, confidence)
        
        return {
            "retrieved_cases": [r[2] for r in reranked_results[:top_k]],
            "similarity_scores": [r[1] for r in reranked_results[:top_k]],
            "case_ids": [r[0] for r in reranked_results[:top_k]],
            "confidence_level": confidence,
            "explanation": explanation,
            "retrieval_time_ms": self.stats["average_retrieval_time"] * 1000
        }
    
    def _build_text_representation(self, case_data: Dict[str, Any]) -> str:
        """构建案例的文本表示"""
        parts = []
        
        # 问题描述
        if "problem_description" in case_data:
            parts.append(f"问题: {case_data['problem_description']}")
        
        # 解决方案（截取部分）
        if "solution" in case_data:
            solution = case_data["solution"][:500]  # 限制长度
            parts.append(f"方案: {solution}")
        
        # 知识点
        if "context" in case_data and "knowledge_point_ids" in case_data["context"]:
            kps = ", ".join(case_data["context"]["knowledge_point_ids"])
            parts.append(f"知识点: {kps}")
        
        # 标签
        if "tags" in case_data:
            tags = ", ".join(case_data["tags"])
            parts.append(f"标签: {tags}")
        
        return " | ".join(parts)
    
    def _rerank_with_context(self, 
                            results: List[Tuple[str, float, Dict]],
                            context: Dict[str, Any]) -> List[Tuple[str, float, Dict]]:
        """结合上下文重排序"""
        reranked = []
        
        for case_id, similarity, case_data in results:
            # 基础相似度分数
            score = similarity
            
            # 知识点匹配度
            if "knowledge_point_ids" in context:
                case_kps = set(case_data.get("context", {}).get("knowledge_point_ids", []))
                query_kps = set(context["knowledge_point_ids"])
                if query_kps:
                    kp_match = len(case_kps & query_kps) / len(query_kps)
                    score = score * 0.7 + kp_match * 0.3
            
            # 难度匹配度
            if "difficulty_level" in context:
                case_diff = case_data.get("context", {}).get("difficulty_level", 3)
                query_diff = context["difficulty_level"]
                diff_penalty = abs(case_diff - query_diff) * 0.05
                score = score * (1 - diff_penalty)
            
            # 成功率加权
            if "outcome" in case_data:
                success_bonus = 0.1 if case_data["outcome"].get("success", False) else -0.1
                score = score + success_bonus
            
            reranked.append((case_id, score, case_data))
        
        # 排序
        reranked.sort(key=lambda x: x[1], reverse=True)
        return reranked
    
    def _calculate_confidence(self, 
                             results: List[Tuple[str, float, Dict]],
                             context: Dict[str, Any]) -> float:
        """计算检索置信度"""
        if not results:
            return 0.0
        
        # 基于最高相似度
        top_similarity = results[0][1]
        
        # 基于结果数量
        result_count_factor = min(len(results) / 5, 1.0)
        
        # 基于分数差异（top结果是否明显优于其他）
        if len(results) > 1:
            score_gap = results[0][1] - results[1][1]
            distinctiveness = min(score_gap / 0.2, 1.0)
        else:
            distinctiveness = 1.0
        
        # 综合置信度
        confidence = top_similarity * 0.6 + result_count_factor * 0.2 + distinctiveness * 0.2
        
        return min(confidence, 1.0)
    
    def _generate_explanation(self,
                             results: List[Tuple[str, float, Dict]],
                             context: Dict[str, Any],
                             confidence: float) -> str:
        """生成检索解释"""
        if not results:
            return "未找到相关案例"
        
        top_similarity = results[0][1]
        
        explanation = f"找到 {len(results)} 个相关案例（置信度: {confidence:.2f}）。"
        
        if top_similarity > 0.8:
            explanation += "最相关案例与当前问题高度相似，可以直接参考。"
        elif top_similarity > 0.6:
            explanation += "找到较为相关的案例，建议结合具体情况调整。"
        else:
            explanation += "案例相关性一般，建议主要依靠基础知识。"
        
        return explanation
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            **self.stats,
            "index_size": self.index.get_size(),
            "index_type": self.index_type,
            "cache_size": len(self.query_cache),
            "cache_hit_rate": self.stats["cache_hits"] / max(self.stats["total_retrievals"], 1)
        }


# 便捷函数
def create_semantic_retrieval_engine(
    model_name: str = "paraphrase-multilingual-MiniLM-L12-v2",
    use_faiss: bool = None,
    use_gpu: bool = False) -> SemanticVectorRetrieval:
    """
    创建语义检索引擎
    
    Args:
        model_name: 预训练模型名称
        use_faiss: 是否使用FAISS（None则自动判断）
        use_gpu: 是否使用GPU
    
    Returns:
        SemanticVectorRetrieval实例
    """
    encoder = SemanticEncoder(model_name)
    return SemanticVectorRetrieval(encoder, use_faiss, use_gpu)


if __name__ == "__main__":
    # 测试代码
    print("Testing Semantic Vector Retrieval...")
    
    if not SENTENCE_TRANSFORMERS_AVAILABLE:
        print("Please install sentence-transformers:")
        print("pip install sentence-transformers")
    else:
        # 创建引擎
        engine = create_semantic_retrieval_engine()
        
        # 添加测试案例
        test_cases = [
            ("case_1", {
                "problem_description": "实现一个图书管理系统，使用链表和数组",
                "solution": "使用动态数组存储图书...",
                "context": {
                    "knowledge_point_ids": ["链表", "数组", "动态内存"],
                    "difficulty_level": 3
                },
                "tags": ["数据结构", "链表", "数组"]
            }),
            ("case_2", {
                "problem_description": "设计一个学生成绩管理系统",
                "solution": "使用哈希表存储学生信息...",
                "context": {
                    "knowledge_point_ids": ["哈希表", "查找算法"],
                    "difficulty_level": 2
                },
                "tags": ["数据结构", "哈希表"]
            })
        ]
        
        engine.add_cases_batch(test_cases)
        
        # 检索
        query = "如何实现一个图书借阅系统"
        results = engine.retrieve(query, top_k=2)
        
        print(f"\nQuery: {query}")
        print(f"Results:")
        for case_id, similarity, metadata in results:
            print(f"  {case_id}: {similarity:.3f} - {metadata.get('problem_description', '')[:50]}")
        
        # 统计
        stats = engine.get_statistics()
        print(f"\nStatistics: {stats}")
