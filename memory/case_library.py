"""
案例库系统
支持结构化案例存储、检索和管理
"""

import uuid
import json
import numpy as np
from datetime import datetime
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass, asdict
from collections import defaultdict
import logging

from .memory_base import MemoryEncoder, SimilarityCalculator

@dataclass
class Case:
    """案例数据结构"""
    id: str
    problem_description: str
    solution: str
    context: Dict[str, Any]
    outcome: Dict[str, Any]
    tags: List[str]
    timestamp: datetime
    embedding: Optional[np.ndarray] = None
    
    # 案例元数据
    difficulty_level: int = 1
    success_score: float = 0.0
    usage_count: int = 0
    last_accessed: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        if self.last_accessed:
            data['last_accessed'] = self.last_accessed.isoformat()
        if self.embedding is not None:
            data['embedding'] = self.embedding.tolist()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Case':
        """从字典创建案例"""
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        if data.get('last_accessed'):
            data['last_accessed'] = datetime.fromisoformat(data['last_accessed'])
        if data.get('embedding'):
            data['embedding'] = np.array(data['embedding'])
        return cls(**data)
    
    def update_access(self):
        """更新访问信息"""
        self.usage_count += 1
        self.last_accessed = datetime.now()

class CaseIndex:
    """案例索引系统"""
    
    def __init__(self):
        self.tag_index = defaultdict(list)  # 标签索引
        self.difficulty_index = defaultdict(list)  # 难度索引
        self.success_index = defaultdict(list)  # 成功率索引
        self.temporal_index = defaultdict(list)  # 时间索引
    
    def add_case(self, case: Case):
        """添加案例到索引"""
        # 标签索引
        for tag in case.tags:
            self.tag_index[tag].append(case.id)
        
        # 难度索引
        self.difficulty_index[case.difficulty_level].append(case.id)
        
        # 成功率索引（分档）
        success_tier = self._get_success_tier(case.success_score)
        self.success_index[success_tier].append(case.id)
        
        # 时间索引（按月份）
        month_key = case.timestamp.strftime("%Y-%m")
        self.temporal_index[month_key].append(case.id)
    
    def remove_case(self, case: Case):
        """从索引中移除案例"""
        # 从所有索引中移除
        for tag in case.tags:
            if case.id in self.tag_index[tag]:
                self.tag_index[tag].remove(case.id)
        
        if case.id in self.difficulty_index[case.difficulty_level]:
            self.difficulty_index[case.difficulty_level].remove(case.id)
        
        success_tier = self._get_success_tier(case.success_score)
        if case.id in self.success_index[success_tier]:
            self.success_index[success_tier].remove(case.id)
        
        month_key = case.timestamp.strftime("%Y-%m")
        if case.id in self.temporal_index[month_key]:
            self.temporal_index[month_key].remove(case.id)
    
    def find_by_tags(self, tags: List[str]) -> List[str]:
        """根据标签查找案例ID"""
        if not tags:
            return []
        
        # 查找包含任一标签的案例
        case_ids = set()
        for tag in tags:
            case_ids.update(self.tag_index.get(tag, []))
        
        return list(case_ids)
    
    def find_by_difficulty(self, difficulty: int) -> List[str]:
        """根据难度查找案例ID"""
        return self.difficulty_index.get(difficulty, [])
    
    def find_by_success_range(self, min_score: float, max_score: float) -> List[str]:
        """根据成功率范围查找案例ID"""
        case_ids = []
        for tier, ids in self.success_index.items():
            tier_min, tier_max = self._parse_success_tier(tier)
            if (tier_min <= max_score and tier_max >= min_score):
                case_ids.extend(ids)
        return case_ids
    
    def _get_success_tier(self, score: float) -> str:
        """获取成功率分档"""
        if score >= 0.9:
            return "excellent"
        elif score >= 0.7:
            return "good"
        elif score >= 0.5:
            return "average"
        else:
            return "poor"
    
    def _parse_success_tier(self, tier: str) -> tuple:
        """解析成功率分档范围"""
        tier_ranges = {
            "excellent": (0.9, 1.0),
            "good": (0.7, 0.9),
            "average": (0.5, 0.7),
            "poor": (0.0, 0.5)
        }
        return tier_ranges.get(tier, (0.0, 1.0))

class CaseLibrary:
    """案例库主类"""
    
    def __init__(self, encoder: Optional[MemoryEncoder] = None):
        self.cases: Dict[str, Case] = {}
        self.index = CaseIndex()
        self.encoder = encoder or MemoryEncoder()
        self.similarity_calculator = SimilarityCalculator()
        
    def add_case(self, case_or_problem, solution=None, context=None, outcome=None, 
                 tags=None, difficulty_level=1, success_score=0.0) -> str:
        """添加新案例 - 支持两种调用方式"""
        
        if isinstance(case_or_problem, Case):
            # 直接传入Case对象
            case = case_or_problem
            # 生成向量嵌入
            case_text = f"{case.problem_description} {case.solution}"
            case.embedding = self.encoder.encode_concepts(case_text)
            
            # 存储案例和更新索引
            self.cases[case.id] = case
            self.index.add_case(case)
            
            logging.info(f"Added case {case.id} with tags: {case.tags}")
            return case.id
        
        else:
            # 传入参数构建案例
            problem_description = case_or_problem
            case_id = str(uuid.uuid4())
            tags = tags or []
            
            # 创建案例
            case = Case(
                id=case_id,
                problem_description=problem_description,
                solution=solution,
                context=context or {},
                outcome=outcome or {},
                tags=tags,
                timestamp=datetime.now(),
                difficulty_level=difficulty_level,
                success_score=success_score
            )
            
            # 生成向量嵌入
            case_text = f"{problem_description} {solution}"
            case.embedding = self.encoder.encode_concepts(case_text)
            
            # 存储案例和更新索引
            self.cases[case_id] = case
            self.index.add_case(case)
            
            logging.info(f"Added case {case_id} with tags: {tags}")
            return case_id
    
    def get_case_by_id(self, case_id: str) -> Optional[Case]:
        """根据ID获取案例（别名方法）"""
        return self.get_case(case_id)
    
    def search_similar(self, query_text: str, threshold: float = 0.7, top_k: int = 10) -> List[tuple]:
        """根据相似度搜索案例（别名方法）"""
        return self.search_by_similarity(query_text, threshold, top_k)
    
    def get_case(self, case_id: str) -> Optional[Case]:
        """获取指定案例"""
        case = self.cases.get(case_id)
        if case:
            case.update_access()
        return case
    
    def remove_case(self, case_id: str) -> bool:
        """移除案例"""
        if case_id in self.cases:
            case = self.cases[case_id]
            self.index.remove_case(case)
            del self.cases[case_id]
            logging.info(f"Removed case {case_id}")
            return True
        return False
    
    def search_by_tags(self, tags: List[str], limit: int = 10) -> List[Case]:
        """根据标签搜索案例"""
        case_ids = self.index.find_by_tags(tags)
        cases = [self.cases[cid] for cid in case_ids if cid in self.cases]
        
        # 按使用次数和成功率排序
        cases.sort(key=lambda x: (x.usage_count, x.success_score), reverse=True)
        return cases[:limit]
    
    def search_by_similarity(self, 
                           query_text: str, 
                           threshold: float = 0.7,
                           limit: int = 10) -> List[tuple]:
        """根据相似度搜索案例"""
        query_embedding = self.encoder.encode_concepts(query_text)
        
        similar_cases = []
        for case in self.cases.values():
            if case.embedding is not None:
                similarity = self.similarity_calculator.cosine_similarity(
                    query_embedding, case.embedding
                )
                if similarity >= threshold:
                    similar_cases.append((case, similarity))
        
        # 按相似度排序
        similar_cases.sort(key=lambda x: x[1], reverse=True)
        return similar_cases[:limit]
    
    def search_by_criteria(self,
                          tags: List[str] = None,
                          difficulty_level: int = None,
                          min_success_score: float = None,
                          max_success_score: float = None,
                          limit: int = 10) -> List[Case]:
        """根据多个条件搜索案例"""
        candidate_ids = set(self.cases.keys())
        
        # 按标签过滤
        if tags:
            tag_ids = set(self.index.find_by_tags(tags))
            candidate_ids = candidate_ids.intersection(tag_ids)
        
        # 按难度过滤
        if difficulty_level is not None:
            difficulty_ids = set(self.index.find_by_difficulty(difficulty_level))
            candidate_ids = candidate_ids.intersection(difficulty_ids)
        
        # 按成功率过滤
        if min_success_score is not None or max_success_score is not None:
            min_score = min_success_score or 0.0
            max_score = max_success_score or 1.0
            success_ids = set(self.index.find_by_success_range(min_score, max_score))
            candidate_ids = candidate_ids.intersection(success_ids)
        
        # 获取案例并排序
        cases = [self.cases[cid] for cid in candidate_ids if cid in self.cases]
        cases.sort(key=lambda x: (x.success_score, x.usage_count), reverse=True)
        
        return cases[:limit]
    
    def get_popular_cases(self, limit: int = 10) -> List[Case]:
        """获取热门案例"""
        cases = list(self.cases.values())
        cases.sort(key=lambda x: x.usage_count, reverse=True)
        return cases[:limit]
    
    def get_recent_cases(self, limit: int = 10) -> List[Case]:
        """获取最新案例"""
        cases = list(self.cases.values())
        cases.sort(key=lambda x: x.timestamp, reverse=True)
        return cases[:limit]
    
    def update_case_outcome(self, case_id: str, new_outcome: Dict[str, Any], new_success_score: float):
        """更新案例结果"""
        if case_id in self.cases:
            case = self.cases[case_id]
            case.outcome = new_outcome
            case.success_score = new_success_score
            # 重新索引
            self.index.remove_case(case)
            self.index.add_case(case)
            logging.info(f"Updated case {case_id} with new outcome")
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取案例库统计信息"""
        if not self.cases:
            return {"total_cases": 0}
        
        cases = list(self.cases.values())
        success_scores = [case.success_score for case in cases]
        usage_counts = [case.usage_count for case in cases]
        
        return {
            "total_cases": len(self.cases),
            "average_success_score": sum(success_scores) / len(success_scores),
            "max_success_score": max(success_scores),
            "min_success_score": min(success_scores),
            "total_usage": sum(usage_counts),
            "average_usage": sum(usage_counts) / len(usage_counts),
            "most_used_case": max(cases, key=lambda x: x.usage_count).id,
            "most_successful_case": max(cases, key=lambda x: x.success_score).id
        }
    
    def save_to_file(self, filepath: str):
        """保存案例库到文件"""
        data = {
            "cases": {cid: case.to_dict() for cid, case in self.cases.items()},
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "total_cases": len(self.cases)
            }
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logging.info(f"Saved case library to {filepath}")
    
    def load_from_file(self, filepath: str):
        """从文件加载案例库"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.cases = {}
            for cid, case_data in data["cases"].items():
                case = Case.from_dict(case_data)
                self.cases[cid] = case
                self.index.add_case(case)
            
            logging.info(f"Loaded {len(self.cases)} cases from {filepath}")
            
        except FileNotFoundError:
            logging.warning(f"Case library file {filepath} not found")
        except Exception as e:
            logging.error(f"Error loading case library: {e}")