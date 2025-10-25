"""
知识点解析器 - 动态从课程实例获取知识点信息

这个模块提供了一个灵活的知识点解析机制，避免了硬编码的知识点映射，
使系统能够支持任意课程和知识点体系。
"""

from typing import Optional, List, Dict, Any
from models.data_models import Course, KnowledgePoint


class KnowledgePointResolver:
    """知识点解析器 - 从课程实例动态获取知识点信息
    
    这个类负责将知识点ID转换为可读的名称和详细信息。
    它从Course实例中获取信息，而不是依赖固定的配置文件。
    
    用法示例：
        # 从课程创建解析器
        resolver = KnowledgePointResolver(course)
        
        # 获取单个知识点名称
        name = resolver.get_name("kp_1")
        
        # 获取多个知识点名称
        names = resolver.get_names(["kp_1", "kp_2", "kp_3"])
        
        # 获取完整的知识点对象
        kp = resolver.get_knowledge_point("kp_1")
    """
    
    def __init__(self, course: Optional[Course] = None):
        """初始化解析器
        
        Args:
            course: 课程实例，如果为None，则在使用时必须调用set_course
        """
        self.course = course
        self._id_to_kp_cache: Dict[str, KnowledgePoint] = {}
        self._name_to_id_cache: Dict[str, str] = {}
        
        if course:
            self._build_cache()
    
    def _build_cache(self):
        """构建知识点缓存，提高查询效率"""
        if not self.course:
            return
        
        self._id_to_kp_cache.clear()
        self._name_to_id_cache.clear()
        
        for kp in self.course.knowledge_points:
            self._id_to_kp_cache[kp.id] = kp
            self._name_to_id_cache[kp.name] = kp.id
    
    def set_course(self, course: Course):
        """设置或更新课程
        
        Args:
            course: 新的课程实例
        """
        self.course = course
        self._build_cache()
    
    def get_knowledge_point(self, kp_id: str) -> Optional[KnowledgePoint]:
        """获取完整的知识点对象
        
        Args:
            kp_id: 知识点ID
            
        Returns:
            KnowledgePoint对象，如果未找到则返回None
        """
        if not self.course:
            return None
        
        return self._id_to_kp_cache.get(kp_id)
    
    def get_name(self, kp_id: str, fallback: bool = True) -> str:
        """获取知识点名称
        
        Args:
            kp_id: 知识点ID
            fallback: 如果找不到，是否返回ID本身（True）或None（False）
            
        Returns:
            知识点名称，如果未找到且fallback=True则返回kp_id
        """
        kp = self.get_knowledge_point(kp_id)
        if kp:
            return kp.name
        
        # 降级方案：尝试从旧的固定映射获取
        if fallback:
            try:
                from config.knowledge_points_mapping import KNOWLEDGE_POINTS_MAPPING
                return KNOWLEDGE_POINTS_MAPPING.get(kp_id, kp_id)
            except ImportError:
                return kp_id
        
        return None
    
    def get_names(self, kp_ids: List[str], fallback: bool = True) -> List[str]:
        """批量获取知识点名称
        
        Args:
            kp_ids: 知识点ID列表
            fallback: 如果找不到，是否返回ID本身
            
        Returns:
            知识点名称列表
        """
        return [self.get_name(kp_id, fallback) for kp_id in kp_ids]
    
    def get_description(self, kp_id: str) -> Optional[str]:
        """获取知识点描述
        
        Args:
            kp_id: 知识点ID
            
        Returns:
            知识点描述
        """
        kp = self.get_knowledge_point(kp_id)
        return kp.description if kp else None
    
    def get_id_by_name(self, kp_name: str) -> Optional[str]:
        """根据名称获取知识点ID（反向查询）
        
        Args:
            kp_name: 知识点名称
            
        Returns:
            知识点ID
        """
        return self._name_to_id_cache.get(kp_name)
    
    def get_difficulty(self, kp_id: str) -> Optional[int]:
        """获取知识点难度等级
        
        Args:
            kp_id: 知识点ID
            
        Returns:
            难度等级 (1-5)
        """
        kp = self.get_knowledge_point(kp_id)
        return kp.difficulty_level if kp else None
    
    def get_prerequisites(self, kp_id: str) -> List[str]:
        """获取知识点的前置知识点ID列表
        
        Args:
            kp_id: 知识点ID
            
        Returns:
            前置知识点ID列表
        """
        kp = self.get_knowledge_point(kp_id)
        return kp.prerequisites if kp else []
    
    def get_learning_objectives(self, kp_id: str) -> List[str]:
        """获取知识点的学习目标
        
        Args:
            kp_id: 知识点ID
            
        Returns:
            学习目标列表
        """
        kp = self.get_knowledge_point(kp_id)
        return kp.learning_objectives if kp else []
    
    def format_for_display(self, kp_id: str) -> str:
        """格式化知识点信息用于显示
        
        Args:
            kp_id: 知识点ID
            
        Returns:
            格式化的字符串，如 "算法基础 (难度: 3, ID: kp_1)"
        """
        kp = self.get_knowledge_point(kp_id)
        if not kp:
            return kp_id
        
        return f"{kp.name} (难度: {kp.difficulty_level}, ID: {kp.id})"
    
    def to_dict(self, kp_id: str) -> Optional[Dict[str, Any]]:
        """将知识点转换为字典格式
        
        Args:
            kp_id: 知识点ID
            
        Returns:
            知识点的字典表示
        """
        kp = self.get_knowledge_point(kp_id)
        if not kp:
            return None
        
        return {
            "id": kp.id,
            "name": kp.name,
            "description": kp.description,
            "difficulty_level": kp.difficulty_level,
            "prerequisites": kp.prerequisites,
            "learning_objectives": kp.learning_objectives,
            "key_concepts": kp.key_concepts,
            "estimated_hours": kp.estimated_hours
        }
    
    def is_valid_id(self, kp_id: str) -> bool:
        """检查知识点ID是否有效
        
        Args:
            kp_id: 知识点ID
            
        Returns:
            True如果ID存在于当前课程中
        """
        return kp_id in self._id_to_kp_cache
    
    def get_all_ids(self) -> List[str]:
        """获取所有知识点ID
        
        Returns:
            知识点ID列表
        """
        return list(self._id_to_kp_cache.keys())
    
    def get_all_names(self) -> List[str]:
        """获取所有知识点名称
        
        Returns:
            知识点名称列表
        """
        return [kp.name for kp in self._id_to_kp_cache.values()]


class GlobalKnowledgePointResolver:
    """全局知识点解析器管理器
    
    这是一个单例类，用于在整个应用程序中管理当前活动的解析器。
    适用于单课程模拟场景。
    
    用法：
        # 设置当前课程
        GlobalKnowledgePointResolver.set_course(course)
        
        # 在任何地方获取解析器
        resolver = GlobalKnowledgePointResolver.get_resolver()
        name = resolver.get_name("kp_1")
    """
    
    _instance: Optional[KnowledgePointResolver] = None
    
    @classmethod
    def set_course(cls, course: Course):
        """设置当前活动的课程
        
        Args:
            course: 课程实例
        """
        if cls._instance is None:
            cls._instance = KnowledgePointResolver(course)
        else:
            cls._instance.set_course(course)
    
    @classmethod
    def get_resolver(cls) -> Optional[KnowledgePointResolver]:
        """获取当前的解析器实例
        
        Returns:
            KnowledgePointResolver实例，如果未设置课程则返回None
        """
        return cls._instance
    
    @classmethod
    def reset(cls):
        """重置全局解析器"""
        cls._instance = None
    
    @classmethod
    def get_name(cls, kp_id: str) -> str:
        """便捷方法：获取知识点名称
        
        Args:
            kp_id: 知识点ID
            
        Returns:
            知识点名称
        """
        if cls._instance:
            return cls._instance.get_name(kp_id)
        return kp_id
    
    @classmethod
    def get_names(cls, kp_ids: List[str]) -> List[str]:
        """便捷方法：批量获取知识点名称
        
        Args:
            kp_ids: 知识点ID列表
            
        Returns:
            知识点名称列表
        """
        if cls._instance:
            return cls._instance.get_names(kp_ids)
        return kp_ids
