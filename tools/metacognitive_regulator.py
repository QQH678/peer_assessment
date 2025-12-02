"""
元认知调节器 (Metacognitive Regulator)
基于Zimmerman自我调节学习理论和Flavell元认知理论

核心功能：
- 根据学习情境动态调整记忆检索的4个权重参数
- 使用简单的神经网络（2层MLP）进行参数优化
- 基于学生表现反馈进行在线学习
- 无需引入新参数，只优化现有4个权重

教育理论依据：
1. 自我调节学习理论 (Zimmerman, 2002)
   - 优秀学习者会根据任务特征调整学习策略
   
2. 元认知理论 (Flavell, 1979)
   - 元认知监控：了解自己的认知过程
   - 元认知调节：根据情境调整认知策略

3. 情境学习理论 (Lave & Wenger, 1991)
   - 学习策略应该适应具体情境
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Any
import json
import logging
from dataclasses import dataclass
from datetime import datetime
import os


@dataclass
class LearningContext:
    """学习情境特征（简化版）"""
    # 学生状态
    current_mastery: float  # 0-1，当前知识掌握度
    metacognition_level: float  # 0-1，元认知水平
    
    # 记忆状态
    stm_size: int          # 短期记忆数量
    ltm_size: int          # 长期记忆数量
    
    def to_feature_vector(self) -> np.ndarray:
        """转换为特征向量（归一化）"""
        features = [
            self.current_mastery,
            self.metacognition_level,
            min(self.stm_size / 50.0, 1.0),  # 归一化到0-1
            min(self.ltm_size / 200.0, 1.0)
        ]
        return np.array(features, dtype=np.float32)


@dataclass
class PerformanceFeedback:
    """性能反馈"""
    assignment_score: float  # 作业得分 0-1
    evaluation_quality: float  # 评价质量 0-1
    learning_gain: float  # 学习增益（相比上次的进步）
    
    def to_reward(self) -> float:
        """转换为奖励信号"""
        # 综合奖励 = 0.5×作业分数 + 0.3×评价质量 + 0.2×学习增益
        return 0.5 * self.assignment_score + 0.3 * self.evaluation_quality + 0.2 * self.learning_gain


class SimpleWeightNetwork:
    """简单的权重调节网络（2层MLP）"""
    
    def __init__(self, input_dim: int = 4, hidden_dim: int = 8):
        """
        Args:
            input_dim: 输入特征维度（默认4：掌握度、元认知、STM大小、LTM大小）
            hidden_dim: 隐藏层维度
        """
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        
        # 初始化权重（Xavier初始化）
        self.W1 = np.random.randn(input_dim, hidden_dim) * np.sqrt(2.0 / input_dim)
        self.b1 = np.zeros(hidden_dim)
        self.W2 = np.random.randn(hidden_dim, 4) * np.sqrt(2.0 / hidden_dim)
        self.b2 = np.zeros(4)
        
        # 学习率
        self.learning_rate = 0.01
        
        # 历史记录
        self.training_history = []
        
    def forward(self, x: np.ndarray) -> np.ndarray:
        """
        前向传播
        
        Args:
            x: 输入特征向量 [input_dim]
            
        Returns:
            权重调整量 [4]（相对于默认值的调整）
        """
        # 隐藏层：ReLU激活
        self.h = np.maximum(0, np.dot(x, self.W1) + self.b1)
        
        # 输出层：tanh激活（输出范围-1到1）
        self.output = np.tanh(np.dot(self.h, self.W2) + self.b2)
        
        # 缓存输入用于反向传播
        self.x = x
        
        return self.output
    
    def get_adjusted_weights(self, context: LearningContext) -> Dict[str, float]:
        """
        根据学习情境获取调整后的权重
        
        Args:
            context: 学习情境
            
        Returns:
            调整后的4个权重（确保和为1）
        """
        # 默认权重
        default_weights = {
            'relevance': 0.4,
            'recency': 0.2,
            'importance': 0.3,
            'success': 0.1
        }
        
        # 获取调整量（-0.2到+0.2）
        x = context.to_feature_vector()
        adjustments = self.forward(x) * 0.2  # 限制调整幅度
        
        # 应用调整
        adjusted = {
            'relevance': default_weights['relevance'] + adjustments[0],
            'recency': default_weights['recency'] + adjustments[1],
            'importance': default_weights['importance'] + adjustments[2],
            'success': default_weights['success'] + adjustments[3]
        }
        
        # 确保非负
        adjusted = {k: max(0.05, v) for k, v in adjusted.items()}
        
        # 归一化到和为1
        total = sum(adjusted.values())
        adjusted = {k: v / total for k, v in adjusted.items()}
        
        return adjusted
    
    def update(self, reward: float, gamma: float = 0.9):
        """
        根据奖励更新网络参数（策略梯度）
        
        Args:
            reward: 奖励信号（-1到1）
            gamma: 折扣因子
        """
        # 计算输出层梯度（简化的策略梯度）
        # dL/d_output = reward * (1 - tanh^2(output))
        grad_output = reward * (1 - self.output ** 2)
        
        # 反向传播到隐藏层
        grad_W2 = np.outer(self.h, grad_output)
        grad_b2 = grad_output
        
        grad_h = np.dot(grad_output, self.W2.T)
        grad_h[self.h <= 0] = 0  # ReLU梯度
        
        grad_W1 = np.outer(self.x, grad_h)
        grad_b1 = grad_h
        
        # 梯度更新
        self.W2 += self.learning_rate * grad_W2
        self.b2 += self.learning_rate * grad_b2
        self.W1 += self.learning_rate * grad_W1
        self.b1 += self.learning_rate * grad_b1
        
        # 记录
        self.training_history.append({
            'timestamp': datetime.now().isoformat(),
            'reward': float(reward),
            'weights_adjusted': True
        })
    
    def save(self, filepath: str):
        """保存模型"""
        state = {
            'W1': self.W1.tolist(),
            'b1': self.b1.tolist(),
            'W2': self.W2.tolist(),
            'b2': self.b2.tolist(),
            'input_dim': self.input_dim,
            'hidden_dim': self.hidden_dim,
            'learning_rate': self.learning_rate,
            'training_history': self.training_history[-100:]  # 只保存最近100条
        }
        
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
        
        logging.info(f"元认知调节器已保存到: {filepath}")
    
    @classmethod
    def load(cls, filepath: str) -> 'SimpleWeightNetwork':
        """加载模型"""
        with open(filepath, 'r', encoding='utf-8') as f:
            state = json.load(f)
        
        network = cls(
            input_dim=state['input_dim'],
            hidden_dim=state['hidden_dim']
        )
        
        network.W1 = np.array(state['W1'])
        network.b1 = np.array(state['b1'])
        network.W2 = np.array(state['W2'])
        network.b2 = np.array(state['b2'])
        network.learning_rate = state['learning_rate']
        network.training_history = state.get('training_history', [])
        
        logging.info(f"元认知调节器已从 {filepath} 加载")
        return network


class MetacognitiveRegulator:
    """
    元认知调节器
    
    核心功能：
    1. 分析学习情境
    2. 调用神经网络调整权重
    3. 收集性能反馈
    4. 在线更新网络
    """
    
    def __init__(self, student_id: str, save_dir: str = "data/regulators"):
        """
        Args:
            student_id: 学生ID
            save_dir: 保存目录
        """
        self.student_id = student_id
        self.save_dir = save_dir
        self.model_path = os.path.join(save_dir, f"regulator_{student_id}.json")
        
        # 加载或创建网络
        if os.path.exists(self.model_path):
            self.network = SimpleWeightNetwork.load(self.model_path)
            logging.info(f"为学生 {student_id} 加载已有调节器")
        else:
            self.network = SimpleWeightNetwork()
            logging.info(f"为学生 {student_id} 创建新调节器")
        
        # 历史记录
        self.context_history: List[LearningContext] = []
        self.weight_history: List[Dict[str, float]] = []
        self.feedback_history: List[PerformanceFeedback] = []
        
        # 上一次权重（用于计算是否需要更新）
        self.last_weights = None
        
    def regulate(self, context: LearningContext) -> Dict[str, float]:
        """
        根据学习情境调节权重
        
        Args:
            context: 学习情境
            
        Returns:
            调节后的权重
        """
        # 获取调整后的权重
        adjusted_weights = self.network.get_adjusted_weights(context)
        
        # 记录
        self.context_history.append(context)
        self.weight_history.append(adjusted_weights)
        self.last_weights = adjusted_weights
        
        logging.info(f"[学生 {self.student_id}] 权重调节:")
        logging.info(f"  情境: 掌握度={context.current_mastery:.2f}, "
                    f"元认知={context.metacognition_level:.2f}, "
                    f"STM={context.stm_size}, LTM={context.ltm_size}")
        logging.info(f"  权重: relevance={adjusted_weights['relevance']:.3f}, "
                    f"recency={adjusted_weights['recency']:.3f}, "
                    f"importance={adjusted_weights['importance']:.3f}, "
                    f"success={adjusted_weights['success']:.3f}")
        
        return adjusted_weights
    
    def provide_feedback(self, feedback: PerformanceFeedback):
        """
        提供性能反馈并更新网络
        
        Args:
            feedback: 性能反馈
        """
        if len(self.context_history) == 0:
            logging.warning("没有历史情境，无法更新")
            return
        
        # 计算奖励
        reward = feedback.to_reward()
        
        # 归一化奖励到[-1, 1]
        normalized_reward = 2 * reward - 1
        
        # 更新网络
        self.network.update(normalized_reward)
        
        # 记录反馈
        self.feedback_history.append(feedback)
        
        logging.info(f"[学生 {self.student_id}] 收到反馈: "
                    f"作业={feedback.assignment_score:.2f}, "
                    f"评价质量={feedback.evaluation_quality:.2f}, "
                    f"学习增益={feedback.learning_gain:.2f}, "
                    f"奖励={normalized_reward:.2f}")
        
        # 定期保存
        if len(self.feedback_history) % 5 == 0:
            self.save()
    
    def save(self):
        """保存调节器"""
        self.network.save(self.model_path)
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        if len(self.weight_history) == 0:
            return {}
        
        # 计算各权重的平均值和标准差
        relevance_vals = [w['relevance'] for w in self.weight_history]
        recency_vals = [w['recency'] for w in self.weight_history]
        importance_vals = [w['importance'] for w in self.weight_history]
        success_vals = [w['success'] for w in self.weight_history]
        
        stats = {
            'total_regulations': len(self.weight_history),
            'total_updates': len(self.feedback_history),
            'weight_statistics': {
                'relevance': {
                    'mean': float(np.mean(relevance_vals)) if len(relevance_vals) > 0 else 0.0,
                    'std': float(np.std(relevance_vals)) if len(relevance_vals) > 0 else 0.0,
                    'min': float(np.min(relevance_vals)) if len(relevance_vals) > 0 else 0.0,
                    'max': float(np.max(relevance_vals)) if len(relevance_vals) > 0 else 0.0
                },
                'recency': {
                    'mean': float(np.mean(recency_vals)) if len(recency_vals) > 0 else 0.0,
                    'std': float(np.std(recency_vals)) if len(recency_vals) > 0 else 0.0,
                    'min': float(np.min(recency_vals)) if len(recency_vals) > 0 else 0.0,
                    'max': float(np.max(recency_vals)) if len(recency_vals) > 0 else 0.0
                },
                'importance': {
                    'mean': float(np.mean(importance_vals)) if len(importance_vals) > 0 else 0.0,
                    'std': float(np.std(importance_vals)) if len(importance_vals) > 0 else 0.0,
                    'min': float(np.min(importance_vals)) if len(importance_vals) > 0 else 0.0,
                    'max': float(np.max(importance_vals)) if len(importance_vals) > 0 else 0.0
                },
                'success': {
                    'mean': float(np.mean(success_vals)) if len(success_vals) > 0 else 0.0,
                    'std': float(np.std(success_vals)) if len(success_vals) > 0 else 0.0,
                    'min': float(np.min(success_vals)) if len(success_vals) > 0 else 0.0,
                    'max': float(np.max(success_vals)) if len(success_vals) > 0 else 0.0
                }
            }
        }
        
        # 性能趋势
        if len(self.feedback_history) > 0:
            recent_5 = self.feedback_history[-5:] if len(self.feedback_history) >= 5 else self.feedback_history
            stats['recent_performance'] = {
                'avg_score': float(np.mean([f.assignment_score for f in recent_5])),
                'avg_eval_quality': float(np.mean([f.evaluation_quality for f in recent_5])),
                'avg_learning_gain': float(np.mean([f.learning_gain for f in recent_5]))
            }
        
        return stats


# ============== 工具接口函数 ==============

def create_regulator_for_student(student_id: str) -> MetacognitiveRegulator:
    """为学生创建元认知调节器"""
    return MetacognitiveRegulator(student_id)


def regulate_memory_weights(
    regulator: MetacognitiveRegulator,
    current_mastery: float,
    metacognition_level: float,
    stm_size: int,
    ltm_size: int
) -> Dict[str, float]:
    """
    调节记忆检索权重（简化版）
    
    Args:
        regulator: 元认知调节器
        current_mastery: 当前知识掌握度 (0-1)
        metacognition_level: 元认知水平 (0-1)
        stm_size: 短期记忆数量
        ltm_size: 长期记忆数量
    
    Returns:
        调节后的权重字典: {'relevance': x, 'recency': y, 'importance': z, 'success': w}
    """
    context = LearningContext(
        current_mastery=current_mastery,
        metacognition_level=metacognition_level,
        stm_size=stm_size,
        ltm_size=ltm_size
    )
    
    return regulator.regulate(context)


def update_regulator(
    regulator: MetacognitiveRegulator,
    assignment_score: float,
    evaluation_quality: float,
    learning_gain: float
):
    """
    更新调节器（提供性能反馈）
    """
    feedback = PerformanceFeedback(
        assignment_score=assignment_score,
        evaluation_quality=evaluation_quality,
        learning_gain=learning_gain
    )
    
    regulator.provide_feedback(feedback)


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    print("=== 元认知调节器测试 ===\n")
    
    # 创建调节器
    regulator = create_regulator_for_student("test_student_001")
    
    # 模拟几个学习场景
    scenarios = [
        # 场景1: 新手学生，记忆较少
        {
            'name': '初学者',
            'context': {
                'current_mastery': 0.3,
                'metacognition_level': 0.5,
                'stm_size': 10,
                'ltm_size': 20
            },
            'feedback': {
                'assignment_score': 0.65,
                'evaluation_quality': 0.7,
                'learning_gain': 0.15
            }
        },
        # 场景2: 高水平学生，记忆丰富
        {
            'name': '熟练者',
            'context': {
                'current_mastery': 0.8,
                'metacognition_level': 0.8,
                'stm_size': 25,
                'ltm_size': 80
            },
            'feedback': {
                'assignment_score': 0.9,
                'evaluation_quality': 0.85,
                'learning_gain': 0.05
            }
        },
        # 场景3: 中等水平，记忆适中
        {
            'name': '进阶者',
            'context': {
                'current_mastery': 0.6,
                'metacognition_level': 0.7,
                'stm_size': 18,
                'ltm_size': 50
            },
            'feedback': {
                'assignment_score': 0.75,
                'evaluation_quality': 0.8,
                'learning_gain': 0.1
            }
        }
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n--- 场景 {i}: {scenario['name']} ---")
        
        # 调节权重
        weights = regulate_memory_weights(regulator, **scenario['context'])
        
        print(f"调节后权重:")
        print(f"  相关性: {weights['relevance']:.3f}")
        print(f"  时新性: {weights['recency']:.3f}")
        print(f"  重要性: {weights['importance']:.3f}")
        print(f"  成功度: {weights['success']:.3f}")
        
        # 模拟一段时间后收到反馈
        update_regulator(regulator, **scenario['feedback'])
        print(f"反馈已提交，网络已更新")
    
    # 统计信息
    print("\n=== 调节器统计信息 ===")
    stats = regulator.get_statistics()
    print(json.dumps(stats, indent=2, ensure_ascii=False))
    
    print("\n测试完成！")
