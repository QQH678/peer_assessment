"""
自适应学习系统
基于记忆系统数据实现个性化学习路径
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import numpy as np
import logging


@dataclass
class LearningGoal:
    """学习目标"""
    concept: str
    target_mastery: float  # 目标掌握度
    current_mastery: float  # 当前掌握度
    priority: str  # high, medium, low
    estimated_time: int  # 预计学习时间（分钟）
    recommended_actions: List[str]


@dataclass
class LearningPath:
    """学习路径"""
    student_id: str
    goals: List[LearningGoal]
    current_stage: str
    next_assignment_recommendation: Dict[str, Any]
    estimated_completion_time: int  # 总预计时间（天）
    success_probability: float  # 成功概率


class ConceptMasteryAnalyzer:
    """概念掌握度分析器"""
    
    def __init__(self):
        # 掌握度等级划分
        self.mastery_levels = {
            "novice": (0.0, 0.3),        # 新手
            "beginner": (0.3, 0.5),      # 初学
            "intermediate": (0.5, 0.7),  # 中级
            "advanced": (0.7, 0.85),     # 高级
            "expert": (0.85, 1.0)        # 专家
        }
        
        # 概念依赖关系图
        self.concept_dependencies = {
            "算法复杂度": [],
            "指针与内存管理": [],
            "顺序存储": ["指针与内存管理"],
            "链式存储": ["指针与内存管理"],
            "指针操作": ["指针与内存管理"],
            "LIFO/FIFO": ["顺序存储"],
            "栈溢出处理": ["LIFO/FIFO"],
            "循环队列": ["LIFO/FIFO", "顺序存储"],
            "递归终止条件": [],
            "分治时间复杂度": ["递归终止条件", "算法复杂度"],
            "线性结构实现": ["顺序存储", "链式存储"],
            "链表与数组特性对比": ["顺序存储", "链式存储"],
            "栈/队列应用": ["LIFO/FIFO", "循环队列"],
            "递归分治排序": ["递归终止条件", "分治时间复杂度"],
            "内存管理": ["指针与内存管理", "动态内存分配"],
        }
    
    def analyze_mastery(self, concept_mastery: Dict[str, float]) -> Dict[str, Any]:
        """分析概念掌握情况"""
        analysis = {
            "total_concepts": len(concept_mastery),
            "mastered_concepts": [],     # > 0.7
            "weak_concepts": [],         # < 0.5
            "learning_concepts": [],     # 0.5-0.7
            "unlearned_concepts": [],    # < 0.3
            "mastery_distribution": {level: 0 for level in self.mastery_levels.keys()},
            "overall_mastery": 0.0,
            "learning_stage": ""
        }
        
        if not concept_mastery:
            return analysis
        
        # 分类概念
        for concept, mastery in concept_mastery.items():
            if mastery >= 0.7:
                analysis["mastered_concepts"].append(concept)
            elif mastery >= 0.5:
                analysis["learning_concepts"].append(concept)
            elif mastery >= 0.3:
                analysis["weak_concepts"].append(concept)
            else:
                analysis["unlearned_concepts"].append(concept)
            
            # 分布统计
            for level, (min_m, max_m) in self.mastery_levels.items():
                if min_m <= mastery < max_m:
                    analysis["mastery_distribution"][level] += 1
                    break
        
        # 整体掌握度
        analysis["overall_mastery"] = np.mean(list(concept_mastery.values()))
        
        # 学习阶段判断
        if analysis["overall_mastery"] >= 0.7:
            analysis["learning_stage"] = "advanced"
        elif analysis["overall_mastery"] >= 0.5:
            analysis["learning_stage"] = "intermediate"
        elif analysis["overall_mastery"] >= 0.3:
            analysis["learning_stage"] = "beginner"
        else:
            analysis["learning_stage"] = "novice"
        
        return analysis
    
    def identify_learning_priorities(self, 
                                    concept_mastery: Dict[str, float],
                                    current_assignment_concepts: List[str] = None) -> List[Tuple[str, float, str]]:
        """
        识别学习优先级
        
        Returns:
            List of (concept, priority_score, reason)
        """
        priorities = []
        
        for concept, mastery in concept_mastery.items():
            priority_score = 0.0
            reasons = []
            
            # 1. 掌握度低的优先
            if mastery < 0.5:
                priority_score += (0.5 - mastery) * 2  # 越低优先级越高
                reasons.append("掌握度较低")
            
            # 2. 当前课程相关的优先
            if current_assignment_concepts and concept in current_assignment_concepts:
                priority_score += 0.5
                reasons.append("当前课程重点")
            
            # 3. 是其他概念的前置依赖
            dependent_concepts = [
                c for c, deps in self.concept_dependencies.items() 
                if concept in deps
            ]
            if dependent_concepts:
                # 检查依赖概念的掌握情况
                unmastered_dependents = [
                    c for c in dependent_concepts 
                    if concept_mastery.get(c, 0) < 0.5
                ]
                if unmastered_dependents:
                    priority_score += len(unmastered_dependents) * 0.2
                    reasons.append(f"影响{len(unmastered_dependents)}个后续概念")
            
            # 4. 前置依赖已掌握（学习准备度）
            prerequisites = self.concept_dependencies.get(concept, [])
            if prerequisites:
                prereq_mastery = np.mean([concept_mastery.get(p, 0) for p in prerequisites])
                if prereq_mastery >= 0.6:
                    priority_score += 0.3
                    reasons.append("前置知识已具备")
            
            if priority_score > 0:
                reason_text = "、".join(reasons)
                priorities.append((concept, priority_score, reason_text))
        
        # 排序
        priorities.sort(key=lambda x: x[1], reverse=True)
        return priorities
    
    def check_prerequisites(self, 
                          concept: str,
                          concept_mastery: Dict[str, float],
                          threshold: float = 0.6) -> Tuple[bool, List[str]]:
        """
        检查前置知识是否满足
        
        Returns:
            (is_ready, missing_prerequisites)
        """
        prerequisites = self.concept_dependencies.get(concept, [])
        
        if not prerequisites:
            return True, []
        
        missing = []
        for prereq in prerequisites:
            if concept_mastery.get(prereq, 0) < threshold:
                missing.append(prereq)
        
        return len(missing) == 0, missing


class AdaptiveLearningPathGenerator:
    """自适应学习路径生成器"""
    
    def __init__(self):
        self.mastery_analyzer = ConceptMasteryAnalyzer()
        
        # 学习资源类型
        self.resource_types = {
            "tutorial": "基础教程",
            "practice": "练习题",
            "project": "项目实战",
            "review": "复习巩固",
            "challenge": "挑战题"
        }
    
    def generate_learning_path(self,
                              student_id: str,
                              concept_mastery: Dict[str, float],
                              performance_history: List[Dict] = None,
                              time_budget: int = 30) -> LearningPath:
        """
        生成个性化学习路径
        
        Args:
            student_id: 学生ID
            concept_mastery: 概念掌握度字典
            performance_history: 历史表现数据
            time_budget: 时间预算（天）
        
        Returns:
            LearningPath对象
        """
        # 分析当前掌握情况
        mastery_analysis = self.mastery_analyzer.analyze_mastery(concept_mastery)
        
        # 识别学习优先级
        priorities = self.mastery_analyzer.identify_learning_priorities(concept_mastery)
        
        # 生成学习目标
        goals = self._generate_learning_goals(
            priorities,
            concept_mastery,
            mastery_analysis,
            time_budget
        )
        
        # 推荐下一个作业
        next_assignment = self._recommend_next_assignment(
            goals,
            concept_mastery,
            mastery_analysis,
            performance_history
        )
        
        # 估算完成时间
        total_time = sum(goal.estimated_time for goal in goals)
        estimated_days = total_time // (60 * 2)  # 假设每天学习2小时
        
        # 计算成功概率
        success_prob = self._estimate_success_probability(
            concept_mastery,
            mastery_analysis,
            performance_history
        )
        
        return LearningPath(
            student_id=student_id,
            goals=goals,
            current_stage=mastery_analysis["learning_stage"],
            next_assignment_recommendation=next_assignment,
            estimated_completion_time=estimated_days,
            success_probability=success_prob
        )
    
    def _generate_learning_goals(self,
                                priorities: List[Tuple[str, float, str]],
                                concept_mastery: Dict[str, float],
                                mastery_analysis: Dict[str, Any],
                                time_budget: int) -> List[LearningGoal]:
        """生成学习目标"""
        goals = []
        
        # 基于优先级生成目标
        for concept, priority_score, reason in priorities[:5]:  # 最多5个主要目标
            current_mastery = concept_mastery.get(concept, 0.0)
            
            # 设定目标掌握度
            if current_mastery < 0.3:
                target_mastery = 0.6  # 新手 -> 中级
            elif current_mastery < 0.5:
                target_mastery = 0.7  # 初学 -> 高级
            elif current_mastery < 0.7:
                target_mastery = 0.85  # 中级 -> 专家
            else:
                continue  # 已经掌握较好，不设为主要目标
            
            # 确定优先级
            if priority_score > 1.0:
                priority = "high"
            elif priority_score > 0.5:
                priority = "medium"
            else:
                priority = "low"
            
            # 估算学习时间
            mastery_gap = target_mastery - current_mastery
            estimated_time = int(mastery_gap * 300)  # 每0.1掌握度需要30分钟
            
            # 推荐学习行动
            actions = self._recommend_learning_actions(concept, current_mastery, target_mastery)
            
            goals.append(LearningGoal(
                concept=concept,
                target_mastery=target_mastery,
                current_mastery=current_mastery,
                priority=priority,
                estimated_time=estimated_time,
                recommended_actions=actions
            ))
        
        return goals
    
    def _recommend_learning_actions(self,
                                   concept: str,
                                   current_mastery: float,
                                   target_mastery: float) -> List[str]:
        """推荐学习行动"""
        actions = []
        
        if current_mastery < 0.3:
            actions.append(f"📚 学习{concept}的基础教程和概念讲解")
            actions.append(f"✍️ 完成{concept}相关的基础练习题（至少3题）")
            actions.append(f"📝 总结{concept}的核心要点和使用场景")
        elif current_mastery < 0.5:
            actions.append(f"🔄 复习{concept}的核心概念")
            actions.append(f"💪 完成中等难度的{concept}练习题（5-8题）")
            actions.append(f"🔍 对比学习{concept}与相关概念的区别")
        elif current_mastery < 0.7:
            actions.append(f"🎯 挑战{concept}的复杂应用场景")
            actions.append(f"🚀 参与涉及{concept}的项目实战")
            actions.append(f"👥 尝试讲解{concept}给他人或写技术博客")
        else:
            actions.append(f"⭐ 深入研究{concept}的高级应用")
            actions.append(f"🏆 挑战{concept}相关的竞赛题或开源项目")
        
        return actions
    
    def _recommend_next_assignment(self,
                                  goals: List[LearningGoal],
                                  concept_mastery: Dict[str, float],
                                  mastery_analysis: Dict[str, Any],
                                  performance_history: List[Dict] = None) -> Dict[str, Any]:
        """推荐下一个作业"""
        if not goals:
            # 没有明确目标，推荐综合性作业
            return {
                "type": "comprehensive",
                "target_concepts": mastery_analysis.get("mastered_concepts", [])[:3],
                "difficulty": 4,
                "focus": "综合应用",
                "description": "综合运用已掌握的概念解决实际问题",
                "estimated_time": 180
            }
        
        # 选择最高优先级的目标
        primary_goal = goals[0]
        
        # 检查前置知识
        is_ready, missing_prereqs = self.mastery_analyzer.check_prerequisites(
            primary_goal.concept,
            concept_mastery
        )
        
        if not is_ready:
            # 需要先学习前置知识
            return {
                "type": "prerequisite",
                "target_concepts": missing_prereqs,
                "difficulty": 2,
                "focus": f"{primary_goal.concept}的前置知识",
                "description": f"学习{', '.join(missing_prereqs)}以准备{primary_goal.concept}",
                "estimated_time": 120,
                "note": f"完成后可以开始学习{primary_goal.concept}"
            }
        
        # 根据当前掌握度推荐作业类型
        if primary_goal.current_mastery < 0.3:
            assignment_type = "tutorial"
            difficulty = 1
            description = f"通过简单的练习理解{primary_goal.concept}的基本概念"
        elif primary_goal.current_mastery < 0.5:
            assignment_type = "practice"
            difficulty = 2
            description = f"通过多样化的练习巩固{primary_goal.concept}的应用"
        elif primary_goal.current_mastery < 0.7:
            assignment_type = "project"
            difficulty = 3
            description = f"在实际项目中深入应用{primary_goal.concept}"
        else:
            assignment_type = "challenge"
            difficulty = 4
            description = f"挑战{primary_goal.concept}的高级应用场景"
        
        # 包含相关概念
        related_concepts = [primary_goal.concept]
        if len(goals) > 1:
            related_concepts.append(goals[1].concept)
        
        return {
            "type": assignment_type,
            "target_concepts": related_concepts,
            "difficulty": difficulty,
            "focus": primary_goal.concept,
            "description": description,
            "estimated_time": primary_goal.estimated_time,
            "learning_objectives": primary_goal.recommended_actions[:2]
        }
    
    def _estimate_success_probability(self,
                                     concept_mastery: Dict[str, float],
                                     mastery_analysis: Dict[str, Any],
                                     performance_history: List[Dict] = None) -> float:
        """估算学习成功概率"""
        # 基于整体掌握度
        base_prob = mastery_analysis.get("overall_mastery", 0.5)
        
        # 考虑历史表现
        if performance_history:
            recent_performance = performance_history[-5:]  # 最近5次
            if recent_performance:
                avg_performance = np.mean([
                    p.get("success", 0.5) if isinstance(p.get("success"), (int, float))
                    else (1.0 if p.get("success") else 0.0)
                    for p in recent_performance
                ])
                # 历史表现占30%权重
                base_prob = base_prob * 0.7 + avg_performance * 0.3
        
        # 考虑进步趋势
        if len(concept_mastery) > 3:
            mastery_values = sorted(concept_mastery.values())
            if len(mastery_values) > 1:
                # 检查是否有进步趋势（较高的标准差表示有些概念掌握得好）
                std = np.std(mastery_values)
                if std > 0.2:  # 有区分度
                    base_prob += 0.1
        
        return min(max(base_prob, 0.0), 1.0)
    
    def recommend_resources(self,
                          concept: str,
                          mastery_level: float) -> List[Dict[str, Any]]:
        """推荐学习资源"""
        recommendations = []
        
        if mastery_level < 0.3:
            recommendations.extend([
                {
                    "type": "tutorial",
                    "title": f"{concept} 基础教程",
                    "difficulty": "beginner",
                    "estimated_time": 60,
                    "priority": "high"
                },
                {
                    "type": "video",
                    "title": f"{concept} 概念讲解视频",
                    "difficulty": "beginner",
                    "estimated_time": 30,
                    "priority": "high"
                },
                {
                    "type": "practice",
                    "title": f"{concept} 入门练习题",
                    "difficulty": "easy",
                    "estimated_time": 90,
                    "priority": "medium"
                }
            ])
        elif mastery_level < 0.5:
            recommendations.extend([
                {
                    "type": "practice",
                    "title": f"{concept} 进阶练习题",
                    "difficulty": "medium",
                    "estimated_time": 120,
                    "priority": "high"
                },
                {
                    "type": "tutorial",
                    "title": f"{concept} 常见应用场景",
                    "difficulty": "intermediate",
                    "estimated_time": 45,
                    "priority": "medium"
                }
            ])
        elif mastery_level < 0.7:
            recommendations.extend([
                {
                    "type": "project",
                    "title": f"{concept} 实战项目",
                    "difficulty": "hard",
                    "estimated_time": 180,
                    "priority": "high"
                },
                {
                    "type": "practice",
                    "title": f"{concept} 综合练习",
                    "difficulty": "hard",
                    "estimated_time": 150,
                    "priority": "medium"
                }
            ])
        else:
            recommendations.extend([
                {
                    "type": "challenge",
                    "title": f"{concept} 高级应用挑战",
                    "difficulty": "expert",
                    "estimated_time": 240,
                    "priority": "medium"
                },
                {
                    "type": "research",
                    "title": f"{concept} 前沿研究阅读",
                    "difficulty": "expert",
                    "estimated_time": 120,
                    "priority": "low"
                }
            ])
        
        return recommendations
    
    def generate_study_plan(self,
                          learning_path: LearningPath,
                          daily_study_time: int = 120) -> Dict[str, Any]:
        """
        生成详细的学习计划
        
        Args:
            learning_path: 学习路径
            daily_study_time: 每日学习时间（分钟）
        
        Returns:
            详细的学习计划
        """
        plan = {
            "student_id": learning_path.student_id,
            "total_duration_days": learning_path.estimated_completion_time,
            "daily_study_time": daily_study_time,
            "schedule": []
        }
        
        current_day = 0
        remaining_time = daily_study_time
        
        for goal in learning_path.goals:
            goal_time = goal.estimated_time
            
            while goal_time > 0:
                if remaining_time <= 0:
                    current_day += 1
                    remaining_time = daily_study_time
                
                time_to_allocate = min(goal_time, remaining_time)
                
                # 计算进度
                progress = (goal.estimated_time - goal_time) / goal.estimated_time
                
                plan["schedule"].append({
                    "day": current_day + 1,
                    "concept": goal.concept,
                    "activity": self._select_activity(goal, progress),
                    "duration_minutes": time_to_allocate,
                    "goal_progress": f"{progress*100:.0f}%",
                    "priority": goal.priority
                })
                
                goal_time -= time_to_allocate
                remaining_time -= time_to_allocate
        
        return plan
    
    def _select_activity(self, goal: LearningGoal, progress: float) -> str:
        """根据进度选择活动"""
        if progress < 0.3:
            return goal.recommended_actions[0] if goal.recommended_actions else "学习基础概念"
        elif progress < 0.7:
            return goal.recommended_actions[1] if len(goal.recommended_actions) > 1 else "完成练习"
        else:
            return goal.recommended_actions[2] if len(goal.recommended_actions) > 2 else "综合应用"


if __name__ == "__main__":
    # 测试代码
    generator = AdaptiveLearningPathGenerator()
    
    # 模拟学生概念掌握度
    test_mastery = {
        "算法复杂度": 0.4,
        "指针与内存管理": 0.6,
        "顺序存储": 0.3,
        "链式存储": 0.2,
        "LIFO/FIFO": 0.15,
        "递归终止条件": 0.5
    }
    
    # 生成学习路径
    path = generator.generate_learning_path(
        student_id="test_student",
        concept_mastery=test_mastery,
        time_budget=30
    )
    
    print(f"学习阶段: {path.current_stage}")
    print(f"预计完成时间: {path.estimated_completion_time}天")
    print(f"成功概率: {path.success_probability:.2%}")
    print(f"\n学习目标:")
    for goal in path.goals:
        print(f"  - {goal.concept} ({goal.current_mastery:.2f} -> {goal.target_mastery:.2f})")
        print(f"    优先级: {goal.priority}, 预计: {goal.estimated_time}分钟")
        for action in goal.recommended_actions:
            print(f"      • {action}")
    
    print(f"\n推荐下一个作业:")
    print(f"  类型: {path.next_assignment_recommendation['type']}")
    print(f"  难度: {path.next_assignment_recommendation['difficulty']}")
    print(f"  重点: {path.next_assignment_recommendation['focus']}")
    print(f"  说明: {path.next_assignment_recommendation['description']}")
