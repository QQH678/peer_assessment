"""
互评系统配置助手
提供灵活的配置接口
"""

from typing import Optional
from dataclasses import dataclass
from config.settings import Config


@dataclass
class PeerReviewConfig:
    """互评配置"""
    # 轮次配置
    rounds_per_stage: int = Config.ROUNDS_PER_STAGE
    peers_per_round: int = Config.PEERS_PER_ROUND
    reviews_per_work: int = Config.REVIEWS_PER_WORK
    days_per_round: int = Config.DAYS_PER_ROUND
    
    # 记忆配置
    stm_retention_rounds: int = Config.STM_RETENTION_ROUNDS
    ltm_consolidation_rounds: int = Config.LTM_CONSOLIDATION_ROUNDS
    stm_max_size: int = Config.STM_MAX_SIZE
    ltm_max_size: int = Config.LTM_MAX_SIZE
    
    # 温度参数
    base_temperature: float = Config.MEMORY_BASE_TEMPERATURE
    temp_adjustment: float = Config.MEMORY_TEMP_ADJUSTMENT
    
    def to_memory_config(self) -> dict:
        """转换为记忆系统配置"""
        return {
            "base_temperature": self.base_temperature,
            "temperature_adjustment": self.temp_adjustment,
            "weight_relevance": Config.MEMORY_WEIGHT_RELEVANCE,
            "weight_recency": Config.MEMORY_WEIGHT_RECENCY,
            "weight_importance": Config.MEMORY_WEIGHT_IMPORTANCE,
            "weight_success": Config.MEMORY_WEIGHT_SUCCESS,
            "consolidation_min_rounds": self.ltm_consolidation_rounds,
            "stm_max_size": self.stm_max_size,
            "ltm_max_size": self.ltm_max_size
        }
    
    def validate(self) -> bool:
        """验证配置合法性"""
        checks = [
            self.rounds_per_stage > 0,
            self.peers_per_round > 0,
            self.reviews_per_work > 0,
            self.days_per_round > 0,
            0.1 <= self.base_temperature <= 2.0,
            self.stm_max_size > 0,
            self.ltm_max_size > 0
        ]
        return all(checks)
    
    @classmethod
    def create_custom(
        cls,
        rounds_per_stage: Optional[int] = None,
        peers_per_round: Optional[int] = None,
        **kwargs
    ) -> 'PeerReviewConfig':
        """创建自定义配置"""
        config = cls()
        
        if rounds_per_stage is not None:
            config.rounds_per_stage = rounds_per_stage
        if peers_per_round is not None:
            config.peers_per_round = peers_per_round
        
        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)
        
        if not config.validate():
            raise ValueError("配置参数不合法")
        
        return config


if __name__ == "__main__":
    # 测试配置
    print("=== 默认互评配置 ===")
    default_config = PeerReviewConfig()
    print(f"每阶段轮次: {default_config.rounds_per_stage}")
    print(f"每轮评价同伴数: {default_config.peers_per_round}")
    print(f"每作业收到评价数: {default_config.reviews_per_work}")
    print(f"基础温度: {default_config.base_temperature}")
    
    print("\n=== 自定义配置 ===")
    custom_config = PeerReviewConfig.create_custom(
        rounds_per_stage=5,
        peers_per_round=3,
        base_temperature=0.8
    )
    print(f"每阶段轮次: {custom_config.rounds_per_stage}")
    print(f"每轮评价同伴数: {custom_config.peers_per_round}")
    print(f"基础温度: {custom_config.base_temperature}")
    
    print("\n=== 记忆系统配置 ===")
    mem_config = default_config.to_memory_config()
    print(f"配置字典: {mem_config}")
    
    print("\n✅ 配置助手测试完成")
