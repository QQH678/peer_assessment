"""
经验回放机制
支持优先级采样和学习策略
"""

import numpy as np
import random
import heapq
from typing import List, Dict, Any, Optional, Tuple, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import deque, defaultdict
import logging
import math

@dataclass
class Experience:
    """经验数据结构"""
    id: str
    content: Dict[str, Any]  # 经验内容
    context: Dict[str, Any]  # 上下文信息
    outcome: Dict[str, Any]  # 结果信息
    timestamp: datetime
    importance: float = 0.0  # 重要性分数
    success_score: float = 0.0  # 成功分数
    replay_count: int = 0  # 回放次数
    last_accessed: datetime = field(default_factory=datetime.now)
    tags: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        if self.last_accessed is None:
            self.last_accessed = self.timestamp
    
    def update_importance(self, new_importance: float):
        """更新重要性分数"""
        # 使用指数移动平均
        alpha = 0.3
        self.importance = alpha * new_importance + (1 - alpha) * self.importance
    
    def increment_replay(self):
        """增加回放计数"""
        self.replay_count += 1
        self.last_accessed = datetime.now()

class PriorityBuffer:
    """优先级缓冲区"""
    
    def __init__(self, max_size: int = 10000):
        self.max_size = max_size
        self.experiences = {}  # id -> Experience
        self.priority_heap = []  # (negative_priority, exp_id)
        self.temporal_buffer = deque(maxlen=1000)  # 时间缓冲区
        
    def add(self, experience: Experience):
        """添加经验"""
        exp_id = experience.id
        
        # 如果已存在，更新
        if exp_id in self.experiences:
            old_exp = self.experiences[exp_id]
            experience.replay_count = old_exp.replay_count
            
        self.experiences[exp_id] = experience
        self.temporal_buffer.append(exp_id)
        
        # 计算优先级
        priority = self._calculate_priority(experience)
        heapq.heappush(self.priority_heap, (-priority, exp_id))
        
        # 检查容量限制
        if len(self.experiences) > self.max_size:
            self._evict_old_experiences()
        
        logging.debug(f"Added experience {exp_id} with priority {priority}")
    
    def sample(self, batch_size: int, method: str = "priority") -> List[Experience]:
        """采样经验"""
        if method == "priority":
            return self._priority_sample(batch_size)
        elif method == "temporal":
            return self._temporal_sample(batch_size)
        elif method == "uniform":
            return self._uniform_sample(batch_size)
        elif method == "mixed":
            return self._mixed_sample(batch_size)
        else:
            raise ValueError(f"Unknown sampling method: {method}")
    
    def _priority_sample(self, batch_size: int) -> List[Experience]:
        """优先级采样"""
        sampled = []
        temp_heap = list(self.priority_heap)
        
        for _ in range(min(batch_size, len(temp_heap))):
            if not temp_heap:
                break
                
            # 选择最高优先级的经验
            neg_priority, exp_id = heapq.heappop(temp_heap)
            
            if exp_id in self.experiences:
                exp = self.experiences[exp_id]
                sampled.append(exp)
                exp.increment_replay()
        
        return sampled
    
    def _temporal_sample(self, batch_size: int) -> List[Experience]:
        """时间采样（最近的经验）"""
        recent_ids = list(self.temporal_buffer)[-batch_size:]
        return [self.experiences[exp_id] for exp_id in recent_ids if exp_id in self.experiences]
    
    def _uniform_sample(self, batch_size: int) -> List[Experience]:
        """均匀随机采样"""
        available_ids = list(self.experiences.keys())
        sampled_ids = random.sample(available_ids, min(batch_size, len(available_ids)))
        
        sampled_experiences = []
        for exp_id in sampled_ids:
            exp = self.experiences[exp_id]
            exp.increment_replay()
            sampled_experiences.append(exp)
        
        return sampled_experiences
    
    def _mixed_sample(self, batch_size: int) -> List[Experience]:
        """混合采样策略"""
        # 50% 优先级采样，30% 时间采样，20% 随机采样
        priority_count = int(batch_size * 0.5)
        temporal_count = int(batch_size * 0.3)
        uniform_count = batch_size - priority_count - temporal_count
        
        sampled = []
        sampled.extend(self._priority_sample(priority_count))
        sampled.extend(self._temporal_sample(temporal_count))
        sampled.extend(self._uniform_sample(uniform_count))
        
        # 去重并限制数量
        seen_ids = set()
        unique_sampled = []
        for exp in sampled:
            if exp.id not in seen_ids:
                seen_ids.add(exp.id)
                unique_sampled.append(exp)
        
        return unique_sampled[:batch_size]
    
    def _calculate_priority(self, experience: Experience) -> float:
        """计算经验优先级"""
        # 基础分数：重要性 + 成功分数
        base_score = experience.importance + experience.success_score
        
        # 时间衰减因子
        days_old = (datetime.now() - experience.timestamp).days
        time_decay = math.exp(-days_old / 30)  # 30天半衰期
        
        # 回放频率惩罚
        replay_penalty = 1.0 / (1.0 + experience.replay_count * 0.1)
        
        # 新颖性奖励（最近添加的经验获得奖励）
        recency_bonus = 1.0 if days_old < 1 else 0.5
        
        priority = base_score * time_decay * replay_penalty + recency_bonus
        
        return max(priority, 0.01)  # 最小优先级
    
    def _evict_old_experiences(self):
        """淘汰旧经验"""
        # 移除最低优先级的经验
        while len(self.experiences) > self.max_size:
            if not self.priority_heap:
                break
                
            # 找到最低优先级的经验
            lowest_priority_exp = None
            min_priority = float('inf')
            
            for neg_priority, exp_id in self.priority_heap:
                if exp_id in self.experiences:
                    priority = -neg_priority
                    if priority < min_priority:
                        min_priority = priority
                        lowest_priority_exp = exp_id
            
            if lowest_priority_exp:
                del self.experiences[lowest_priority_exp]
                # 重建堆（简化处理）
                self._rebuild_heap()
            else:
                break
    
    def _rebuild_heap(self):
        """重建优先级堆"""
        self.priority_heap = []
        for exp_id, experience in self.experiences.items():
            priority = self._calculate_priority(experience)
            heapq.heappush(self.priority_heap, (-priority, exp_id))
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取缓冲区统计信息"""
        if not self.experiences:
            return {
                "total_experiences": 0,
                "average_importance": 0,
                "average_success_score": 0,
                "average_replay_count": 0
            }
        
        total = len(self.experiences)
        avg_importance = np.mean([exp.importance for exp in self.experiences.values()])
        avg_success = np.mean([exp.success_score for exp in self.experiences.values()])
        avg_replay = np.mean([exp.replay_count for exp in self.experiences.values()])
        
        return {
            "total_experiences": total,
            "average_importance": avg_importance,
            "average_success_score": avg_success,
            "average_replay_count": avg_replay,
            "heap_size": len(self.priority_heap)
        }

class LearningScheduler:
    """学习调度器"""
    
    def __init__(self):
        self.last_replay_time = datetime.now()
        self.replay_interval = timedelta(minutes=30)  # 默认30分钟回放一次
        self.performance_history = deque(maxlen=100)
        self.adaptive_enabled = True
        
    def should_replay(self) -> bool:
        """判断是否应该进行经验回放"""
        time_condition = datetime.now() - self.last_replay_time >= self.replay_interval
        
        # 如果启用自适应调度
        if self.adaptive_enabled and len(self.performance_history) >= 10:
            # 如果性能下降，增加回放频率
            recent_performance = np.mean(list(self.performance_history)[-5:])
            historical_performance = np.mean(list(self.performance_history)[:-5])
            
            if recent_performance < historical_performance * 0.9:  # 性能下降10%
                return True
        
        return time_condition
    
    def update_performance(self, performance_score: float):
        """更新性能分数"""
        self.performance_history.append(performance_score)
    
    def adapt_schedule(self):
        """自适应调整回放间隔"""
        if not self.adaptive_enabled or len(self.performance_history) < 20:
            return
        
        recent_trend = np.polyfit(range(10), list(self.performance_history)[-10:], 1)[0]
        
        if recent_trend > 0:  # 性能提升，减少回放频率
            self.replay_interval = min(self.replay_interval * 1.1, timedelta(hours=2))
        else:  # 性能下降，增加回放频率
            self.replay_interval = max(self.replay_interval * 0.9, timedelta(minutes=10))
        
        logging.info(f"Adapted replay interval to {self.replay_interval}")

class ExperienceReplay:
    """经验回放主类"""
    
    def __init__(self, 
                 buffer_size: int = 10000,
                 default_batch_size: int = 32,
                 learning_rate: float = 0.01):
        
        self.buffer = PriorityBuffer(buffer_size)
        self.scheduler = LearningScheduler()
        self.default_batch_size = default_batch_size
        self.learning_rate = learning_rate
        
        # 学习统计
        self.replay_sessions = 0
        self.total_experiences_learned = 0
        self.learning_effectiveness = deque(maxlen=100)
        
    def add_experience(self, 
                      experience_id: str,
                      content: Dict[str, Any],
                      context: Dict[str, Any],
                      outcome: Dict[str, Any],
                      importance: float = 0.5,
                      success_score: float = 0.5,
                      tags: List[str] = None):
        """添加新经验"""
        
        experience = Experience(
            id=experience_id,
            content=content,
            context=context,
            outcome=outcome,
            timestamp=datetime.now(),
            importance=importance,
            success_score=success_score,
            tags=tags or []
        )
        
        self.buffer.add(experience)
        logging.info(f"Added experience: {experience_id}")
    
    def replay_session(self, 
                      batch_size: int = None,
                      sampling_method: str = "mixed",
                      learning_callback: Optional[callable] = None) -> Dict[str, Any]:
        """执行一次经验回放会话"""
        
        batch_size = batch_size or self.default_batch_size
        
        # 采样经验
        experiences = self.buffer.sample(batch_size, sampling_method)
        
        if not experiences:
            logging.warning("No experiences available for replay")
            return {"experiences_learned": 0, "effectiveness": 0.0}
        
        # 学习过程
        learning_results = []
        for experience in experiences:
            
            # 如果提供了学习回调函数
            if learning_callback:
                try:
                    result = learning_callback(experience)
                    learning_results.append(result)
                except Exception as e:
                    logging.error(f"Error in learning callback: {e}")
                    learning_results.append({"success": False, "error": str(e)})
            else:
                # 默认学习过程
                learning_results.append(self._default_learning(experience))
        
        # 更新统计信息
        self.replay_sessions += 1
        self.total_experiences_learned += len(experiences)
        
        # 计算学习效果
        successful_learning = sum(1 for result in learning_results if result.get("success", False))
        effectiveness = successful_learning / len(experiences) if experiences else 0.0
        self.learning_effectiveness.append(effectiveness)
        
        # 更新调度器
        self.scheduler.update_performance(effectiveness)
        self.scheduler.last_replay_time = datetime.now()
        
        session_result = {
            "experiences_learned": len(experiences),
            "successful_learning": successful_learning,
            "effectiveness": effectiveness,
            "sampling_method": sampling_method,
            "timestamp": datetime.now().isoformat()
        }
        
        logging.info(f"Replay session completed: {successful_learning}/{len(experiences)} successful")
        return session_result
    
    def auto_replay(self, learning_callback: Optional[callable] = None) -> Optional[Dict[str, Any]]:
        """自动经验回放（根据调度器）"""
        if self.scheduler.should_replay():
            result = self.replay_session(learning_callback=learning_callback)
            self.scheduler.adapt_schedule()
            return result
        return None
    
    def replay_by_tags(self, 
                      tags: List[str], 
                      batch_size: int = None,
                      learning_callback: Optional[callable] = None) -> Dict[str, Any]:
        """根据标签回放特定经验"""
        
        batch_size = batch_size or self.default_batch_size
        
        # 筛选具有指定标签的经验
        matching_experiences = []
        for experience in self.buffer.experiences.values():
            if any(tag in experience.tags for tag in tags):
                matching_experiences.append(experience)
        
        # 按重要性排序并选择top-k
        matching_experiences.sort(key=lambda x: x.importance, reverse=True)
        selected_experiences = matching_experiences[:batch_size]
        
        # 更新回放计数
        for exp in selected_experiences:
            exp.increment_replay()
        
        # 执行学习
        learning_results = []
        for experience in selected_experiences:
            if learning_callback:
                try:
                    result = learning_callback(experience)
                    learning_results.append(result)
                except Exception as e:
                    learning_results.append({"success": False, "error": str(e)})
            else:
                learning_results.append(self._default_learning(experience))
        
        successful_learning = sum(1 for result in learning_results if result.get("success", False))
        effectiveness = successful_learning / len(selected_experiences) if selected_experiences else 0.0
        
        return {
            "experiences_learned": len(selected_experiences),
            "successful_learning": successful_learning,
            "effectiveness": effectiveness,
            "tags": tags,
            "timestamp": datetime.now().isoformat()
        }
    
    def _default_learning(self, experience: Experience) -> Dict[str, Any]:
        """默认学习过程"""
        # 简单的默认学习：根据成功分数更新重要性
        new_importance = experience.importance + self.learning_rate * experience.success_score
        experience.update_importance(min(new_importance, 1.0))
        
        return {
            "success": True,
            "importance_updated": True,
            "new_importance": experience.importance
        }
    
    def get_experience_by_id(self, experience_id: str) -> Optional[Experience]:
        """根据ID获取经验"""
        return self.buffer.experiences.get(experience_id)
    
    def remove_experience(self, experience_id: str) -> bool:
        """移除经验"""
        if experience_id in self.buffer.experiences:
            del self.buffer.experiences[experience_id]
            self.buffer._rebuild_heap()
            logging.info(f"Removed experience: {experience_id}")
            return True
        return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取经验回放统计信息"""
        buffer_stats = self.buffer.get_statistics()
        
        avg_effectiveness = np.mean(self.learning_effectiveness) if self.learning_effectiveness else 0.0
        
        return {
            **buffer_stats,
            "replay_sessions": self.replay_sessions,
            "total_experiences_learned": self.total_experiences_learned,
            "average_learning_effectiveness": avg_effectiveness,
            "next_replay_in": max(timedelta(), 
                                self.scheduler.replay_interval - 
                                (datetime.now() - self.scheduler.last_replay_time)).total_seconds(),
            "adaptive_scheduling_enabled": self.scheduler.adaptive_enabled
        }
    
    def set_adaptive_scheduling(self, enabled: bool):
        """设置自适应调度"""
        self.scheduler.adaptive_enabled = enabled
        logging.info(f"Adaptive scheduling {'enabled' if enabled else 'disabled'}")
    
    def force_replay(self, learning_callback: Optional[callable] = None) -> Dict[str, Any]:
        """强制执行经验回放"""
        return self.replay_session(learning_callback=learning_callback)
    
    def clear_experiences(self, before_date: Optional[datetime] = None):
        """清理经验（可选择清理指定日期之前的）"""
        if before_date is None:
            # 清理所有
            self.buffer.experiences.clear()
            self.buffer.priority_heap.clear()
            self.buffer.temporal_buffer.clear()
            logging.info("Cleared all experiences")
        else:
            # 清理指定日期之前的
            to_remove = []
            for exp_id, experience in self.buffer.experiences.items():
                if experience.timestamp < before_date:
                    to_remove.append(exp_id)
            
            for exp_id in to_remove:
                del self.buffer.experiences[exp_id]
            
            self.buffer._rebuild_heap()
            logging.info(f"Cleared {len(to_remove)} experiences before {before_date}")