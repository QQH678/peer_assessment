"""
新一代记忆检索系统
基于温度参数的智能优先级检索
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np
import logging
from collections import defaultdict

from .new_memory_models import (
    MemoryItem,
    MemoryDimension,
    MemoryType,
    LearningMemory,
    PeerEvaluationMemory,
    ReceivedEvaluationMemory,
    TeacherFeedbackMemory,
    MemoryPriorityScore,
    MemoryRetrievalConfig,
    MemoryRetrievalResult,
    StudentMemoryState,
    MemoryConsolidationRule,
    compute_memory_priority,
    softmax_with_temperature,
    compute_adaptive_temperature
)

# 尝试导入语义检索
try:
    from .semantic_retrieval import SemanticEncoder, SemanticVectorRetrieval
    SEMANTIC_AVAILABLE = True
except ImportError:
    SEMANTIC_AVAILABLE = False
    logging.warning("Semantic retrieval not available")


class TemperatureBasedMemoryRetrieval:
    """基于温度参数的记忆检索系统"""
    
    def __init__(
        self,
        student_id: str,
        config: Optional[MemoryRetrievalConfig] = None,
        use_semantic: bool = True
    ):
        self.student_id = student_id
        self.config = config or MemoryRetrievalConfig()
        
        # 语义检索引擎
        self.semantic_encoder = None
        self.use_semantic = use_semantic and SEMANTIC_AVAILABLE
        
        if self.use_semantic:
            try:
                self.semantic_encoder = SemanticEncoder()
                logging.info(f"学生 {student_id}: 语义检索已启用")
            except Exception as e:
                logging.warning(f"语义检索初始化失败: {e}")
                self.use_semantic = False
        
        # 检索统计
        self.retrieval_stats = {
            "total_retrievals": 0,
            "by_dimension": defaultdict(int),
            "avg_temperature": 0.0
        }
    
    def retrieve_memories(
        self,
        query: str,
        memory_pool: List[MemoryItem],
        knowledge_mastery: Dict[str, float],
        context: Optional[Dict[str, Any]] = None,
        dimension_filter: Optional[List[MemoryDimension]] = None,
        top_k: Optional[int] = None
    ) -> MemoryRetrievalResult:
        """
        检索记忆（核心方法）
        
        Args:
            query: 查询文本
            memory_pool: 候选记忆池
            knowledge_mastery: 知识掌握度字典
            context: 额外上下文信息
            dimension_filter: 维度过滤器
            top_k: 返回top-k记忆
        
        Returns:
            检索结果
        """
        if not memory_pool:
            return MemoryRetrievalResult(
                query=query,
                retrieved_memories=[],
                priority_scores=[],
                temperature_used=self.config.base_temperature,
                total_candidates=0
            )
        
        # 1. 维度过滤
        if dimension_filter:
            memory_pool = [m for m in memory_pool if m.dimension in dimension_filter]
        
        # 2. 计算相关性得分
        relevance_scores = self._compute_relevance_scores(query, memory_pool)
        
        # 3. 计算优先级分数
        priority_scores = []
        for i, memory in enumerate(memory_pool):
            score = compute_memory_priority(
                memory=memory,
                relevance=relevance_scores[i],
                config=self.config
            )
            # 应用维度权重
            dimension_weight = self.config.dimension_weights.get(memory.dimension, 1.0)
            score.total_priority *= dimension_weight
            
            priority_scores.append(score)
        
        # 4. 计算自适应温度
        avg_mastery = np.mean(list(knowledge_mastery.values())) if knowledge_mastery else 0.5
        temperature = compute_adaptive_temperature(
            base_temperature=self.config.base_temperature,
            mastery_level=avg_mastery,
            adjustment_factor=self.config.temperature_adjustment
        )
        
        # 5. 温度软化的softmax选择
        priorities = [s.total_priority for s in priority_scores]
        probabilities = softmax_with_temperature(priorities, temperature)
        
        # 更新检索概率
        for i, score in enumerate(priority_scores):
            score.retrieval_probability = probabilities[i]
        
        # 6. 选择top-k
        k = top_k or self.config.top_k
        # 按概率加权排序
        sorted_indices = np.argsort(probabilities)[::-1][:k]
        
        selected_memories = [memory_pool[i] for i in sorted_indices]
        selected_scores = [priority_scores[i] for i in sorted_indices]
        
        # 7. 更新访问记录
        for memory in selected_memories:
            memory.access_count += 1
            memory.last_accessed = datetime.now()
        
        # 8. 统计
        self._update_stats(selected_memories, temperature)
        
        # 9. 构建结果
        dimensions_retrieved = defaultdict(int)
        for mem in selected_memories:
            dimensions_retrieved[mem.dimension] += 1
        
        return MemoryRetrievalResult(
            query=query,
            retrieved_memories=selected_memories,
            priority_scores=selected_scores,
            temperature_used=temperature,
            total_candidates=len(memory_pool),
            dimensions_retrieved=dict(dimensions_retrieved)
        )
    
    def _compute_relevance_scores(
        self,
        query: str,
        memories: List[MemoryItem]
    ) -> List[float]:
        """计算相关性得分"""
        if self.use_semantic and self.semantic_encoder:
            return self._semantic_relevance(query, memories)
        else:
            return self._keyword_relevance(query, memories)
    
    def _semantic_relevance(
        self,
        query: str,
        memories: List[MemoryItem]
    ) -> List[float]:
        """基于语义编码的相关性"""
        try:
            # 编码查询
            query_embedding = self.semantic_encoder.encode(query)
            
            # 计算相似度
            scores = []
            for memory in memories:
                if memory.embedding is None:
                    # 动态编码记忆内容
                    memory.embedding = self.semantic_encoder.encode(memory.content).tolist()
                
                # 余弦相似度
                similarity = self._cosine_similarity(
                    query_embedding,
                    np.array(memory.embedding)
                )
                scores.append(max(0.0, similarity))  # 确保非负
            
            return scores
        except Exception as e:
            logging.warning(f"语义相关性计算失败: {e}，使用关键词方法")
            return self._keyword_relevance(query, memories)
    
    def _keyword_relevance(
        self,
        query: str,
        memories: List[MemoryItem]
    ) -> List[float]:
        """基于关键词的相关性（降级方案）"""
        query_words = set(query.lower().split())
        
        scores = []
        for memory in memories:
            content_words = set(memory.content.lower().split())
            
            # 计算词重叠比例
            if len(query_words) > 0:
                overlap = len(query_words & content_words) / len(query_words)
            else:
                overlap = 0.0
            
            # 考虑知识点匹配
            kp_bonus = 0.0
            if hasattr(memory, 'knowledge_points'):
                for kp in memory.knowledge_points:
                    if kp.lower() in query.lower():
                        kp_bonus += 0.1
            
            scores.append(min(1.0, overlap + kp_bonus))
        
        return scores
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """计算余弦相似度"""
        dot_product = np.dot(vec1, vec2)
        norm_product = np.linalg.norm(vec1) * np.linalg.norm(vec2)
        
        if norm_product == 0:
            return 0.0
        
        return dot_product / norm_product
    
    def _update_stats(self, memories: List[MemoryItem], temperature: float):
        """更新统计信息"""
        self.retrieval_stats["total_retrievals"] += 1
        
        for mem in memories:
            self.retrieval_stats["by_dimension"][mem.dimension] += 1
        
        # 更新平均温度
        n = self.retrieval_stats["total_retrievals"]
        old_avg = self.retrieval_stats["avg_temperature"]
        self.retrieval_stats["avg_temperature"] = (
            (old_avg * (n - 1) + temperature) / n
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """获取检索统计"""
        return dict(self.retrieval_stats)


class MemoryConsolidationManager:
    """记忆巩固管理器"""
    
    def __init__(self, rule: Optional[MemoryConsolidationRule] = None):
        self.rule = rule or MemoryConsolidationRule()
        self.consolidation_log = []
    
    def check_consolidation(
        self,
        memory: MemoryItem,
        current_round: int,
        memory_creation_round: int
    ) -> bool:
        """
        检查记忆是否应该巩固到长期记忆
        
        Args:
            memory: 记忆项
            current_round: 当前轮次
            memory_creation_round: 记忆创建轮次
        
        Returns:
            是否应该巩固
        """
        # 已经是长期记忆
        if memory.memory_type == MemoryType.LONG_TERM:
            return False
        
        # 已经巩固过
        if memory.is_consolidated:
            return False
        
        # 突破性事件自动巩固
        if self.rule.auto_consolidate_breakthrough and memory.is_breakthrough:
            return True
        
        # 计算年龄
        age = current_round - memory_creation_round
        
        # 满足以下任一组合即可巩固：
        # 方案A: 时间足够 (最宽松，只看年龄)
        if age >= self.rule.min_age_rounds:
            # 只要年龄够了，就检查其他条件（OR关系）
            if memory.importance >= self.rule.importance_threshold:
                return True  # 重要性够
            if memory.access_count >= self.rule.min_access_count:
                return True  # 访问次数够
            # 即使重要性和访问次数都不够，年龄够了也可以巩固一部分
            # 但为了避免记忆爆炸，要求至少达到一半阈值
            if memory.importance >= self.rule.importance_threshold * 0.6 or \
               memory.access_count >= max(1, self.rule.min_access_count * 0.5):
                return True
        
        # 方案B: 特别重要（无需年龄）
        if memory.importance >= 0.85:
            return True
        
        # 方案C: 频繁访问（无需年龄）
        if memory.access_count >= 5:
            return True
        
        return False
    
    def consolidate_memory(self, memory: MemoryItem) -> MemoryItem:
        """
        巩固记忆（STM -> LTM）
        
        Args:
            memory: 待巩固的记忆
        
        Returns:
            巩固后的记忆
        """
        # 标记为长期记忆
        memory.memory_type = MemoryType.LONG_TERM
        memory.is_consolidated = True
        
        # 可选：压缩内容（提取关键信息）
        # 这里可以添加摘要生成逻辑
        
        # 记录日志
        self.consolidation_log.append({
            "memory_id": memory.id,
            "dimension": memory.dimension,
            "timestamp": datetime.now(),
            "importance": memory.importance,
            "access_count": memory.access_count
        })
        
        logging.info(f"记忆已巩固: {memory.id} ({memory.dimension})")
        
        return memory
    
    def prune_memories(
        self,
        memories: List[MemoryItem],
        max_stm_size: int = 50,
        max_ltm_size: int = 200
    ) -> Tuple[List[MemoryItem], List[MemoryItem]]:
        """
        修剪记忆（防止过载）
        
        Args:
            memories: 所有记忆
            max_stm_size: 短期记忆最大容量
            max_ltm_size: 长期记忆最大容量
        
        Returns:
            (保留的记忆, 删除的记忆)
        """
        stm = [m for m in memories if m.memory_type == MemoryType.SHORT_TERM]
        ltm = [m for m in memories if m.memory_type == MemoryType.LONG_TERM]
        
        removed = []
        
        # 修剪短期记忆：保留最新和最重要的
        if len(stm) > max_stm_size:
            # 按时间和重要性排序
            stm_sorted = sorted(
                stm,
                key=lambda m: (m.timestamp, m.importance),
                reverse=True
            )
            removed.extend(stm_sorted[max_stm_size:])
            stm = stm_sorted[:max_stm_size]
        
        # 修剪长期记忆：保留最重要和最常访问的
        if len(ltm) > max_ltm_size:
            ltm_sorted = sorted(
                ltm,
                key=lambda m: (m.importance, m.access_count),
                reverse=True
            )
            removed.extend(ltm_sorted[max_ltm_size:])
            ltm = ltm_sorted[:max_ltm_size]
        
        kept = stm + ltm
        
        logging.info(f"记忆修剪: 保留 {len(kept)}, 删除 {len(removed)}")
        
        return kept, removed


class NewMemorySystem:
    """新一代记忆系统（集成类）"""
    
    def __init__(
        self,
        student_id: str,
        config: Optional[MemoryRetrievalConfig] = None,
        consolidation_rule: Optional[MemoryConsolidationRule] = None,
        use_semantic: bool = True
    ):
        self.student_id = student_id
        
        # 记忆状态
        self.memory_state = StudentMemoryState(
            student_id=student_id,
            retrieval_config=config or MemoryRetrievalConfig(),
            consolidation_rule=consolidation_rule or MemoryConsolidationRule()
        )
        
        # 检索引擎
        self.retrieval_engine = TemperatureBasedMemoryRetrieval(
            student_id=student_id,
            config=self.memory_state.retrieval_config,
            use_semantic=use_semantic
        )
        
        # 巩固管理器
        self.consolidation_manager = MemoryConsolidationManager(
            rule=self.memory_state.consolidation_rule
        )
        
        # 轮次追踪（用于巩固判断）
        self.current_round = 0
        self.memory_creation_rounds = {}  # memory_id -> round
    
    def add_memory(self, memory: MemoryItem):
        """添加新记忆"""
        # 记录创建轮次
        self.memory_creation_rounds[memory.id] = self.current_round
        
        # 添加到短期记忆
        self.memory_state.short_term_memories.append(memory)
        self.memory_state.total_memories += 1
        
        # 更新统计
        dim = memory.dimension
        self.memory_state.memories_by_dimension[dim] = \
            self.memory_state.memories_by_dimension.get(dim, 0) + 1
        
        logging.info(f"新记忆已添加: {memory.id} ({memory.dimension})")
    
    def retrieve(
        self,
        query: str,
        dimension_filter: Optional[List[MemoryDimension]] = None,
        top_k: Optional[int] = None
    ) -> MemoryRetrievalResult:
        """检索记忆"""
        # 合并短期和长期记忆
        all_memories = (
            self.memory_state.short_term_memories +
            self.memory_state.long_term_memories
        )
        
        return self.retrieval_engine.retrieve_memories(
            query=query,
            memory_pool=all_memories,
            knowledge_mastery=self.memory_state.knowledge_mastery,
            dimension_filter=dimension_filter,
            top_k=top_k
        )
    
    def advance_round(self):
        """推进轮次（触发巩固检查）"""
        self.current_round += 1
        logging.info(f"推进到第 {self.current_round} 轮")
        
        # 检查哪些记忆需要巩固
        to_consolidate = []
        for memory in self.memory_state.short_term_memories:
            creation_round = self.memory_creation_rounds.get(memory.id, self.current_round)
            if self.consolidation_manager.check_consolidation(
                memory, self.current_round, creation_round
            ):
                to_consolidate.append(memory)
        
        # 执行巩固
        for memory in to_consolidate:
            consolidated = self.consolidation_manager.consolidate_memory(memory)
            self.memory_state.short_term_memories.remove(memory)
            self.memory_state.long_term_memories.append(consolidated)
        
        # 修剪记忆
        all_memories = (
            self.memory_state.short_term_memories +
            self.memory_state.long_term_memories
        )
        kept, removed = self.consolidation_manager.prune_memories(all_memories)
        
        self.memory_state.short_term_memories = [
            m for m in kept if m.memory_type == MemoryType.SHORT_TERM
        ]
        self.memory_state.long_term_memories = [
            m for m in kept if m.memory_type == MemoryType.LONG_TERM
        ]
        self.memory_state.total_memories = len(kept)
    
    def update_knowledge_mastery(self, knowledge_point: str, mastery: float):
        """更新知识掌握度"""
        self.memory_state.knowledge_mastery[knowledge_point] = mastery
    
    def get_state(self) -> StudentMemoryState:
        """获取记忆状态"""
        return self.memory_state
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "student_id": self.student_id,
            "current_round": self.current_round,
            "total_memories": self.memory_state.total_memories,
            "stm_count": len(self.memory_state.short_term_memories),
            "ltm_count": len(self.memory_state.long_term_memories),
            "memories_by_dimension": dict(self.memory_state.memories_by_dimension),
            "retrieval_stats": self.retrieval_engine.get_stats(),
            "consolidation_log": self.consolidation_manager.consolidation_log[-10:]  # 最近10条
        }


if __name__ == "__main__":
    # 测试新记忆系统
    print("=== 测试新一代记忆系统 ===\n")
    
    # 创建记忆系统
    memory_system = NewMemorySystem(
        student_id="student_001",
        use_semantic=False  # 为测试简化，不使用语义检索
    )
    
    # 添加一些测试记忆
    from .new_memory_models import LearningMemory, PeerEvaluationMemory
    
    # 第0轮：学习记忆
    mem1 = LearningMemory(
        id="mem_001",
        content="完成了二叉树遍历作业，掌握了递归和DFS",
        assignment_id="assign_001",
        assignment_title="二叉树遍历",
        knowledge_points=["二叉树", "递归", "DFS"],
        score=85,
        time_spent=3.0,
        importance=0.8,
        success_score=0.85
    )
    memory_system.add_memory(mem1)
    
    # 第0轮：评价记忆
    mem2 = PeerEvaluationMemory(
        id="mem_002",
        content="评价了张三的代码，学到了更简洁的写法",
        evaluated_student_id="student_002",
        evaluated_work_id="work_002",
        assignment_id="assign_001",
        evaluation_content="代码简洁清晰",
        evaluation_score=90,
        importance=0.7,
        success_score=0.9
    )
    memory_system.add_memory(mem2)
    
    print(f"✅ 已添加 {memory_system.memory_state.total_memories} 条记忆\n")
    
    # 检索测试
    print("=== 检索测试 ===")
    result = memory_system.retrieve("二叉树递归")
    print(f"查询: '二叉树递归'")
    print(f"检索到 {len(result.retrieved_memories)} 条记忆")
    print(f"使用温度: {result.temperature_used:.2f}")
    for i, mem in enumerate(result.retrieved_memories):
        score = result.priority_scores[i]
        print(f"  {i+1}. {mem.content[:50]}... (优先级: {score.total_priority:.3f})")
    print()
    
    # 推进几轮
    print("=== 推进轮次 ===")
    for i in range(7):
        memory_system.advance_round()
        if i == 6:
            stats = memory_system.get_stats()
            print(f"第{stats['current_round']}轮:")
            print(f"  STM: {stats['stm_count']}, LTM: {stats['ltm_count']}")
    
    print("\n✅ 新记忆系统测试完成！")
