"""
增强版记忆系统集成模块
整合语义检索和自适应学习
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import logging
import os
import pickle

from .semantic_retrieval import (
    SemanticEncoder, 
    SemanticVectorRetrieval,
    create_semantic_retrieval_engine,
    SENTENCE_TRANSFORMERS_AVAILABLE
)
from .intelligent_memory import (
    StudentMemorySystem,
    MemoryContext,
    LearningOutcome,
    MemoryRetrievalResult
)

# 导入优化模块
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'optimization'))

try:
    from optimization.adaptive_learning import (
        AdaptiveLearningPathGenerator,
        ConceptMasteryAnalyzer,
        LearningPath
    )
    ADAPTIVE_LEARNING_AVAILABLE = True
except ImportError:
    ADAPTIVE_LEARNING_AVAILABLE = False
    logging.warning("Adaptive learning module not available")


class EnhancedStudentMemorySystem(StudentMemorySystem):
    """增强版学生记忆系统"""
    
    def __init__(self, 
                 student_id: str,
                 config: Dict[str, Any] = None,
                 use_semantic_retrieval: bool = True):
        """
        初始化增强版记忆系统
        
        Args:
            student_id: 学生ID
            config: 配置参数
            use_semantic_retrieval: 是否使用语义检索（需要安装sentence-transformers）
        """
        # 调用父类初始化
        super().__init__(student_id, config)
        
        self.use_semantic_retrieval = use_semantic_retrieval and SENTENCE_TRANSFORMERS_AVAILABLE
        
        # 初始化语义检索引擎
        if self.use_semantic_retrieval:
            try:
                model_name = config.get("semantic_model", "paraphrase-multilingual-MiniLM-L12-v2")
                self.semantic_engine = create_semantic_retrieval_engine(
                    model_name=model_name,
                    use_faiss=config.get("use_faiss", None),
                    use_gpu=config.get("use_gpu", False)
                )
                logging.info(f"Semantic retrieval engine initialized for student {student_id}")
                
                # 加载已有案例到语义索引
                self._migrate_to_semantic_index()
            except Exception as e:
                logging.error(f"Failed to initialize semantic retrieval: {e}")
                self.use_semantic_retrieval = False
                self.semantic_engine = None
        else:
            self.semantic_engine = None
            if use_semantic_retrieval:
                logging.warning(
                    "Semantic retrieval requested but sentence-transformers not available. "
                    "Install with: pip install sentence-transformers"
                )
        
        # 初始化自适应学习模块
        if ADAPTIVE_LEARNING_AVAILABLE:
            self.learning_path_generator = AdaptiveLearningPathGenerator()
            self.mastery_analyzer = ConceptMasteryAnalyzer()
            logging.info(f"Adaptive learning module initialized for student {student_id}")
        else:
            self.learning_path_generator = None
            self.mastery_analyzer = None
    
    def save_memory_state(self, filepath: str):
        """
        保存记忆状态（增强版）
        
        包含语义检索配置信息
        """
        # 先调用父类保存
        super().save_memory_state(filepath)
        
        # 如果使用语义检索，添加语义配置信息
        if self.use_semantic_retrieval and self.semantic_engine:
            try:
                import json
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 添加语义检索配置
                encoder = self.semantic_engine.encoder
                semantic_config = {
                    'encoding_method': 'semantic',
                    'model_name': encoder.model_name,
                    'vector_dimension': encoder.dimension
                }
                
                # 添加device信息（如果可用）
                if hasattr(encoder, 'device'):
                    semantic_config['device'] = str(encoder.device)
                
                data['memory_state']['encoder_config'] = semantic_config
                
                # 重新保存
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                    
                logging.info(f"Saved enhanced memory state with semantic config to {filepath}")
            except Exception as e:
                logging.error(f"Failed to update semantic config in saved file: {e}")
    
    def retrieve_relevant_cases(self,
                               current_problem: str,
                               context: MemoryContext,
                               max_cases: int = 5) -> MemoryRetrievalResult:
        """
        检索相关案例（增强版）
        
        优先使用语义检索，失败则回退到传统方法
        """
        if self.use_semantic_retrieval and self.semantic_engine:
            try:
                # 使用语义检索
                return self._semantic_retrieve(current_problem, context, max_cases)
            except Exception as e:
                logging.error(f"Semantic retrieval failed: {e}, falling back to traditional method")
        
        # 回退到传统检索方法
        return super().retrieve_relevant_cases(current_problem, context, max_cases)
    
    def _semantic_retrieve(self,
                          current_problem: str,
                          context: MemoryContext,
                          max_cases: int = 5) -> MemoryRetrievalResult:
        """使用语义检索"""
        start_time = datetime.now()
        
        # 构建查询文本（包含上下文信息）
        query_parts = [current_problem]
        if context.knowledge_point_ids:
            query_parts.append(f"知识点: {', '.join(context.knowledge_point_ids)}")
        query_text = " | ".join(query_parts)
        
        # 检索
        results = self.semantic_engine.retrieve_with_context(
            query=query_text,
            context={
                "knowledge_point_ids": context.knowledge_point_ids,
                "difficulty_level": context.difficulty_level
            },
            top_k=max_cases
        )
        
        # 构建返回结果
        retrieval_time = (datetime.now() - start_time).total_seconds() * 1000
        
        return MemoryRetrievalResult(
            retrieved_cases=results["retrieved_cases"],
            similarity_scores=results["similarity_scores"],
            retrieval_time_ms=retrieval_time,
            confidence_level=results["confidence_level"],
            explanation=results["explanation"]
        )
    
    def store_learning_experience(self,
                                 problem: str,
                                 solution: str,
                                 context: MemoryContext,
                                 outcome: LearningOutcome):
        """
        存储学习经验（增强版）
        
        同时更新传统索引和语义索引
        """
        # 调用父类方法存储到传统索引
        super().store_learning_experience(problem, solution, context, outcome)
        
        # 添加到语义索引
        if self.use_semantic_retrieval and self.semantic_engine:
            try:
                # 获取最新添加的案例
                if self.memory_state.stored_cases:
                    latest_case = self.memory_state.stored_cases[-1]
                    case_id = latest_case.get("id", f"{self.student_id}_{len(self.memory_state.stored_cases)-1}")
                    
                    # 添加到语义索引
                    self.semantic_engine.add_case(case_id, latest_case)
                    logging.debug(f"Case {case_id} added to semantic index")
            except Exception as e:
                logging.error(f"Failed to add case to semantic index: {e}")
    
    def _migrate_to_semantic_index(self):
        """将已有案例迁移到语义索引"""
        if not self.semantic_engine:
            return
        
        try:
            if self.memory_state.stored_cases:
                cases_to_add = [
                    (case.get("id", f"{self.student_id}_{i}"), case)
                    for i, case in enumerate(self.memory_state.stored_cases)
                ]
                
                if cases_to_add:
                    self.semantic_engine.add_cases_batch(cases_to_add)
                    logging.info(f"Migrated {len(cases_to_add)} cases to semantic index")
        except Exception as e:
            logging.error(f"Failed to migrate cases to semantic index: {e}")
    
    def generate_learning_path(self,
                              time_budget: int = 30,
                              daily_study_time: int = 120) -> Optional[LearningPath]:
        """
        生成个性化学习路径
        
        Args:
            time_budget: 时间预算（天）
            daily_study_time: 每日学习时间（分钟）
        
        Returns:
            LearningPath对象，如果模块未启用则返回None
        """
        if not self.learning_path_generator:
            logging.warning("Adaptive learning module not available")
            return None
        
        try:
            # 获取概念掌握度
            concept_mastery = self.memory_state.concept_mastery
            
            # 生成学习路径
            learning_path = self.learning_path_generator.generate_learning_path(
                student_id=self.student_id,
                concept_mastery=concept_mastery,
                performance_history=self._get_performance_history(),
                time_budget=time_budget
            )
            
            return learning_path
        except Exception as e:
            logging.error(f"Failed to generate learning path: {e}")
            return None
    
    def analyze_concept_mastery(self) -> Optional[Dict[str, Any]]:
        """
        分析概念掌握情况
        
        Returns:
            分析结果字典，如果模块未启用则返回None
        """
        if not self.mastery_analyzer:
            logging.warning("Concept mastery analyzer not available")
            return None
        
        try:
            return self.mastery_analyzer.analyze_mastery(
                self.memory_state.concept_mastery
            )
        except Exception as e:
            logging.error(f"Failed to analyze concept mastery: {e}")
            return None
    
    def get_learning_recommendations(self, 
                                    context: MemoryContext) -> List[Dict[str, Any]]:
        """
        获取学习建议（增强版）
        
        结合传统推荐和自适应学习推荐
        """
        recommendations = super().get_learning_recommendations(context)
        
        # 添加基于自适应学习的推荐
        if self.learning_path_generator:
            try:
                # 识别学习优先级
                priorities = self.mastery_analyzer.identify_learning_priorities(
                    self.memory_state.concept_mastery,
                    context.knowledge_point_ids
                )
                
                # 添加优先级建议
                for concept, priority_score, reason in priorities[:3]:
                    recommendations.append({
                        "type": "priority_concept",
                        "concept": concept,
                        "priority_score": priority_score,
                        "reason": reason,
                        "current_mastery": self.memory_state.concept_mastery.get(concept, 0.0),
                        "recommended_resources": self.learning_path_generator.recommend_resources(
                            concept,
                            self.memory_state.concept_mastery.get(concept, 0.0)
                        )
                    })
            except Exception as e:
                logging.error(f"Failed to generate adaptive recommendations: {e}")
        
        return recommendations
    
    def _get_performance_history(self) -> List[Dict]:
        """获取历史表现数据"""
        history = []
        
        for case in self.memory_state.stored_cases:
            if "outcome" in case:
                outcome = case["outcome"]
                history.append({
                    "success": outcome.get("success", False),
                    "score": outcome.get("score", 0.0),
                    "time_spent": outcome.get("time_spent", 0),
                    "timestamp": case.get("timestamp")
                })
        
        return history
    
    def get_system_statistics(self) -> Dict[str, Any]:
        """获取系统统计信息（增强版）"""
        stats = {
            "student_id": self.student_id,
            "total_cases": len(self.memory_state.stored_cases),
            "total_retrievals": self.memory_state.total_retrievals,
            "total_replays": self.memory_state.total_replays,
            "concept_mastery": self.memory_state.concept_mastery,
            "memory_effectiveness": self.memory_state.memory_effectiveness,
            "use_semantic_retrieval": self.use_semantic_retrieval,
            "use_adaptive_learning": ADAPTIVE_LEARNING_AVAILABLE
        }
        
        # 添加语义检索统计
        if self.semantic_engine:
            stats["semantic_retrieval"] = self.semantic_engine.get_statistics()
        
        # 添加概念掌握分析
        if self.mastery_analyzer:
            stats["mastery_analysis"] = self.analyze_concept_mastery()
        
        return stats


def create_enhanced_memory_system(student_id: str,
                                 config: Dict[str, Any] = None) -> EnhancedStudentMemorySystem:
    """
    创建增强版记忆系统的便捷函数
    
    Args:
        student_id: 学生ID
        config: 配置参数
            - semantic_model: 语义模型名称
            - use_faiss: 是否使用FAISS
            - use_gpu: 是否使用GPU
            - use_semantic_retrieval: 是否使用语义检索
    
    Returns:
        EnhancedStudentMemorySystem实例
    """
    default_config = {
        "semantic_model": "paraphrase-multilingual-MiniLM-L12-v2",
        "use_faiss": None,  # 自动判断
        "use_gpu": False,
        "use_semantic_retrieval": True
    }
    
    if config:
        default_config.update(config)
    
    return EnhancedStudentMemorySystem(
        student_id=student_id,
        config=default_config,
        use_semantic_retrieval=default_config["use_semantic_retrieval"]
    )


if __name__ == "__main__":
    # 测试代码
    print("Testing Enhanced Memory System...")
    
    # 创建测试系统
    memory_system = create_enhanced_memory_system(
        student_id="test_student",
        config={"use_semantic_retrieval": SENTENCE_TRANSFORMERS_AVAILABLE}
    )
    
    print(f"System initialized:")
    print(f"  - Semantic retrieval: {memory_system.use_semantic_retrieval}")
    print(f"  - Adaptive learning: {ADAPTIVE_LEARNING_AVAILABLE}")
    
    # 测试存储和检索
    if memory_system.use_semantic_retrieval:
        from .intelligent_memory import MemoryContext, LearningOutcome
        
        # 存储测试案例
        test_context = MemoryContext(
            knowledge_point_ids=["链表", "数组"],
            difficulty_level=3,
            current_problem="实现图书管理系统",
            available_resources=["教材", "网络资源"],
            time_constraints=120,
            learning_objectives=["掌握链表操作", "理解动态内存"]
        )
        
        test_outcome = LearningOutcome(
            success=True,
            score=85.0,
            concepts_learned=["链表", "数组"],
            concepts_reinforced=[],
            errors_made=[],
            time_spent=100,
            reflection="很好的学习经历"
        )
        
        memory_system.store_learning_experience(
            problem="实现图书管理系统",
            solution="使用链表和数组...",
            context=test_context,
            outcome=test_outcome
        )
        
        print("\nCase stored successfully")
        
        # 测试检索
        result = memory_system.retrieve_relevant_cases(
            current_problem="设计学生管理系统",
            context=test_context,
            max_cases=3
        )
        
        print(f"\nRetrieval result:")
        print(f"  - Confidence: {result.confidence_level:.2f}")
        print(f"  - Explanation: {result.explanation}")
        print(f"  - Cases found: {len(result.retrieved_cases)}")
    
    # 测试学习路径生成
    if ADAPTIVE_LEARNING_AVAILABLE:
        learning_path = memory_system.generate_learning_path(time_budget=30)
        if learning_path:
            print(f"\nLearning path generated:")
            print(f"  - Stage: {learning_path.current_stage}")
            print(f"  - Goals: {len(learning_path.goals)}")
            print(f"  - Success probability: {learning_path.success_probability:.2%}")
    
    # 获取统计
    stats = memory_system.get_system_statistics()
    print(f"\nSystem statistics:")
    for key, value in stats.items():
        if not isinstance(value, dict):
            print(f"  - {key}: {value}")
