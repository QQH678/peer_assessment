import os
from typing import Dict, Any
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class Config:
    """配置类"""
    
    # API配置
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gpt-3.5-turbo")
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-ada-002")
    
    # 模拟参数
    DEFAULT_STUDENT_COUNT = int(os.getenv("DEFAULT_STUDENT_COUNT", 20))
    DEFAULT_ASSIGNMENT_COUNT = int(os.getenv("DEFAULT_ASSIGNMENT_COUNT", 5))
    DEFAULT_EVALUATIONS_PER_ASSIGNMENT = int(os.getenv("DEFAULT_EVALUATIONS_PER_ASSIGNMENT", 3))
    
    # 作业完成率配置
    ASSIGNMENT_COMPLETION_RATE = float(os.getenv("ASSIGNMENT_COMPLETION_RATE", 1.0))  # 默认100%完成
    
    # 教师Agent配置
    COURSE_DESIGN_TEMPERATURE = float(os.getenv("COURSE_DESIGN_TEMPERATURE", 0.3))
    ASSIGNMENT_CREATION_TEMPERATURE = float(os.getenv("ASSIGNMENT_CREATION_TEMPERATURE", 0.4))
    
    # 学生记忆系统配置
    SHORT_TERM_MEMORY_DECAY = float(os.getenv("SHORT_TERM_MEMORY_DECAY", 0.1))
    LONG_TERM_MEMORY_THRESHOLD = float(os.getenv("LONG_TERM_MEMORY_THRESHOLD", 0.6))
    MEMORY_CONSOLIDATION_THRESHOLD = float(os.getenv("MEMORY_CONSOLIDATION_THRESHOLD", 0.7))
    
    # 知识点掌握程度配置
    MASTERY_IMPROVEMENT_RATE = float(os.getenv("MASTERY_IMPROVEMENT_RATE", 0.1))
    LEARNING_EFFECTIVENESS_BASE = float(os.getenv("LEARNING_EFFECTIVENESS_BASE", 0.6))
    
    # 目录配置
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DATA_DIR = os.path.join(BASE_DIR, os.getenv("DATA_DIR", "data"))
    OUTPUT_DIR = os.path.join(BASE_DIR, os.getenv("OUTPUT_DIR", "output"))
    
    # 评价维度权重
    EVALUATION_WEIGHTS = {
        "functionality": 0.4,    # 功能实现
        "code_quality": 0.3,     # 代码质量
        "innovation": 0.15,      # 创新性
        "documentation": 0.15    # 文档完整性
    }
    
    # === 互评轮次配置 ===
    # 阶段配置
    ROUNDS_PER_STAGE = int(os.getenv("ROUNDS_PER_STAGE", 3))  # 每个教学阶段的互评轮次
    
    # 每轮互评配置
    PEERS_PER_ROUND = int(os.getenv("PEERS_PER_ROUND", 2))  # 每轮评价多少个同伴
    REVIEWS_PER_WORK = int(os.getenv("REVIEWS_PER_WORK", 2))  # 每份作业收到多少评价
    
    # 时间配置
    DAYS_PER_ROUND = int(os.getenv("DAYS_PER_ROUND", 7))  # 每轮互评时长（天）
    
    # === 新记忆系统配置 ===
    # 短期记忆配置
    STM_RETENTION_ROUNDS = int(os.getenv("STM_RETENTION_ROUNDS", 2))  # 短期记忆保留轮次
    STM_MAX_SIZE = int(os.getenv("STM_MAX_SIZE", 50))  # 短期记忆最大容量
    
    # 长期记忆配置
    LTM_CONSOLIDATION_ROUNDS = int(os.getenv("LTM_CONSOLIDATION_ROUNDS", 6))  # 长期记忆巩固轮次
    LTM_MAX_SIZE = int(os.getenv("LTM_MAX_SIZE", 200))  # 长期记忆最大容量
    LTM_IMPORTANCE_THRESHOLD = float(os.getenv("LTM_IMPORTANCE_THRESHOLD", 0.7))  # 重要性阈值
    
    # 温度参数配置
    MEMORY_BASE_TEMPERATURE = float(os.getenv("MEMORY_BASE_TEMPERATURE", 1.0))  # 基础温度
    MEMORY_TEMP_ADJUSTMENT = float(os.getenv("MEMORY_TEMP_ADJUSTMENT", 0.5))  # 温度调整系数
    
    # 优先级权重配置
    MEMORY_WEIGHT_RELEVANCE = float(os.getenv("MEMORY_WEIGHT_RELEVANCE", 0.4))
    MEMORY_WEIGHT_RECENCY = float(os.getenv("MEMORY_WEIGHT_RECENCY", 0.2))
    MEMORY_WEIGHT_IMPORTANCE = float(os.getenv("MEMORY_WEIGHT_IMPORTANCE", 0.3))
    MEMORY_WEIGHT_SUCCESS = float(os.getenv("MEMORY_WEIGHT_SUCCESS", 0.1))
    
    # 学生类型配置
    STUDENT_TYPES = {
        "excellent": {"ratio": 0.13, "score_bias": 0.1, "strictness": 0.8},
        "good": {"ratio": 0.22, "score_bias": 0.05, "strictness": 0.7},
        "average": {"ratio": 0.32, "score_bias": 0.0, "strictness": 0.6},
        "below_average": {"ratio": 0.13, "score_bias": -0.05, "strictness": 0.5},
        "strict": {"ratio": 0.05, "score_bias": -0.1, "strictness": 0.9},
        "lenient": {"ratio": 0.05, "score_bias": 0.15, "strictness": 0.3},
        "perfunctory": {"ratio": 0.10, "score_bias": 0.05, "strictness": 0.2}
    }
    
    @classmethod
    def ensure_directories(cls):
        """确保必要的目录存在"""
        os.makedirs(cls.DATA_DIR, exist_ok=True)
        os.makedirs(cls.OUTPUT_DIR, exist_ok=True)
        os.makedirs(os.path.join(cls.DATA_DIR, "assignments"), exist_ok=True)
        os.makedirs(os.path.join(cls.DATA_DIR, "evaluations"), exist_ok=True)
        os.makedirs(os.path.join(cls.DATA_DIR, "students"), exist_ok=True)
