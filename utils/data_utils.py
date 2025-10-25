"""
实用工具函数
"""

import json
import pandas as pd
from typing import Dict, List, Any
from models.data_models import SimulationSession

def export_to_csv(session: SimulationSession, output_dir: str):
    """将模拟数据导出为CSV格式"""
    import os
    
    # 导出学生数据
    students_data = [student.to_dict() for student in session.students]
    students_df = pd.DataFrame(students_data)
    students_df.to_csv(os.path.join(output_dir, "students.csv"), index=False, encoding='utf-8-sig')
    
    # 导出作业数据
    assignments_data = [assignment.to_dict() for assignment in session.assignments]
    assignments_df = pd.DataFrame(assignments_data)
    assignments_df.to_csv(os.path.join(output_dir, "assignments.csv"), index=False, encoding='utf-8-sig')
    
    # 导出作品数据
    works_data = [work.to_dict() for work in session.works]
    works_df = pd.DataFrame(works_data)
    works_df.to_csv(os.path.join(output_dir, "works.csv"), index=False, encoding='utf-8-sig')
    
    # 导出评估数据（展开结构）
    evaluations_data = []
    for evaluation in session.evaluations:
        eval_dict = evaluation.to_dict()
        # 展开scores字典
        scores = eval_dict.pop('scores')
        for key, value in scores.items():
            eval_dict[f'score_{key}'] = value
        
        # 展开comments字典
        comments = eval_dict.pop('comments')
        for key, value in comments.items():
            eval_dict[f'comment_{key}'] = value
        
        evaluations_data.append(eval_dict)
    
    evaluations_df = pd.DataFrame(evaluations_data)
    evaluations_df.to_csv(os.path.join(output_dir, "evaluations.csv"), index=False, encoding='utf-8-sig')
    
    print(f"数据已导出到CSV文件: {output_dir}")

def generate_summary_statistics(session: SimulationSession) -> Dict[str, Any]:
    """生成汇总统计信息"""
    stats = {}
    
    # 基本统计
    stats['basic'] = {
        'total_students': len(session.students),
        'total_assignments': len(session.assignments),
        'total_works': len(session.works),
        'total_evaluations': len(session.evaluations)
    }
    
    # 学生统计
    student_types = [s.student_type.value for s in session.students]
    stats['students'] = {
        'type_counts': pd.Series(student_types).value_counts().to_dict(),
        'avg_gpa': sum(s.gpa for s in session.students) / len(session.students),
        'avg_experience': sum(s.programming_experience for s in session.students) / len(session.students)
    }
    
    # 评估统计
    if session.evaluations:
        all_scores = []
        for evaluation in session.evaluations:
            weighted_score = evaluation.scores.get_weighted_score({
                "functionality": 0.4,
                "code_quality": 0.3,
                "innovation": 0.15,
                "documentation": 0.15
            })
            all_scores.append(weighted_score)
        
        stats['evaluations'] = {
            'avg_score': sum(all_scores) / len(all_scores),
            'min_score': min(all_scores),
            'max_score': max(all_scores),
            'score_std': pd.Series(all_scores).std()
        }
    
    return stats

def compare_sessions(session_ids: List[str]) -> Dict[str, Any]:
    """比较多个模拟会话"""
    from simulation.simulator import PeerAssessmentSimulator
    
    simulator = PeerAssessmentSimulator()
    comparison = {}
    
    for session_id in session_ids:
        try:
            session = simulator.load_simulation_session(session_id)
            stats = generate_summary_statistics(session)
            comparison[session_id] = stats
        except FileNotFoundError:
            comparison[session_id] = {"error": "Session not found"}
    
    return comparison

def create_evaluation_matrix(session: SimulationSession) -> pd.DataFrame:
    """创建评估矩阵（学生 x 学生）"""
    # 创建学生ID到姓名的映射
    student_names = {s.id: s.name for s in session.students}
    
    # 创建矩阵数据
    matrix_data = []
    
    for evaluation in session.evaluations:
        # 找到被评估作品的作者
        work = next((w for w in session.works if w.id == evaluation.work_id), None)
        if work:
            evaluator_name = student_names.get(evaluation.evaluator_id, "Unknown")
            author_name = student_names.get(work.student_id, "Unknown")
            
            weighted_score = evaluation.scores.get_weighted_score({
                "functionality": 0.4,
                "code_quality": 0.3,
                "innovation": 0.15,
                "documentation": 0.15
            })
            
            matrix_data.append({
                'evaluator': evaluator_name,
                'author': author_name,
                'score': weighted_score
            })
    
    # 转换为透视表
    if matrix_data:
        df = pd.DataFrame(matrix_data)
        matrix = df.pivot_table(values='score', index='evaluator', columns='author', fill_value=0)
        return matrix
    else:
        return pd.DataFrame()

def filter_evaluations_by_criteria(session: SimulationSession, **criteria) -> List:
    """根据条件筛选评估"""
    filtered_evaluations = []
    
    for evaluation in session.evaluations:
        # 获取评估者信息
        evaluator = next((s for s in session.students if s.id == evaluation.evaluator_id), None)
        
        # 获取作品作者信息
        work = next((w for w in session.works if w.id == evaluation.work_id), None)
        author = None
        if work:
            author = next((s for s in session.students if s.id == work.student_id), None)
        
        # 检查筛选条件
        include = True
        
        if 'evaluator_type' in criteria and evaluator:
            if evaluator.student_type.value != criteria['evaluator_type']:
                include = False
        
        if 'author_type' in criteria and author:
            if author.student_type.value != criteria['author_type']:
                include = False
        
        if 'min_score' in criteria:
            weighted_score = evaluation.scores.get_weighted_score({
                "functionality": 0.4,
                "code_quality": 0.3,
                "innovation": 0.15,
                "documentation": 0.15
            })
            if weighted_score < criteria['min_score']:
                include = False
        
        if 'max_score' in criteria:
            weighted_score = evaluation.scores.get_weighted_score({
                "functionality": 0.4,
                "code_quality": 0.3,
                "innovation": 0.15,
                "documentation": 0.15
            })
            if weighted_score > criteria['max_score']:
                include = False
        
        if include:
            filtered_evaluations.append(evaluation)
    
    return filtered_evaluations
