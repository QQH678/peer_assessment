import uuid
import json
import random
import os
from datetime import datetime
from typing import List, Dict, Any, Tuple
from tqdm import tqdm

from models.data_models import SimulationSession, Student, Assignment, StudentWork, PeerEvaluation
from agents.students.student_generator import StudentGenerator
from agents.students.student_agent import StudentAgent
from agents.assignments.assignment_generator import AssignmentGenerator
from agents.evaluators.evaluator_agent import EvaluatorAgent
from config.settings import Config

class PeerAssessmentSimulator:
    """同伴互评模拟器"""
    
    def __init__(self):
        self.student_generator = StudentGenerator()
        self.assignment_generator = AssignmentGenerator()
        Config.ensure_directories()
    
    def run_simulation(self, 
                      student_count: int = None,
                      assignment_count: int = None,
                      evaluations_per_work: int = None) -> SimulationSession:
        """运行完整的模拟"""
        
        # 使用默认参数
        student_count = student_count or Config.DEFAULT_STUDENT_COUNT
        assignment_count = assignment_count or Config.DEFAULT_ASSIGNMENT_COUNT
        evaluations_per_work = evaluations_per_work or Config.DEFAULT_EVALUATIONS_PER_ASSIGNMENT
        
        print(f"开始同伴互评模拟...")
        print(f"参数：{student_count}名学生，{assignment_count}个作业，每个作业{evaluations_per_work}次互评")
        
        # 创建模拟会话
        session = SimulationSession(
            session_id=str(uuid.uuid4()),
            created_at=datetime.now(),
            parameters={
                "student_count": student_count,
                "assignment_count": assignment_count,
                "evaluations_per_work": evaluations_per_work
            },
            students=[],
            assignments=[],
            works=[],
            evaluations=[]
        )
        
        # 步骤1: 生成学生
        print("\n步骤1: 生成学生...")
        session.students = self.student_generator.generate_students(student_count)
        print(f"生成了{len(session.students)}名学生")
        
        # 步骤2: 生成作业
        print("\n步骤2: 生成作业...")
        session.assignments = self.assignment_generator.generate_assignments(assignment_count)
        print(f"生成了{len(session.assignments)}个作业")
        
        # 步骤3: 学生完成作业
        print("\n步骤3: 学生完成作业...")
        session.works = self._generate_student_works(session.students, session.assignments)
        print(f"生成了{len(session.works)}份学生作品")
        
        # 步骤4: 执行同伴互评
        print("\n步骤4: 执行同伴互评...")
        session.evaluations = self._conduct_peer_evaluations(
            session.students, session.works, session.assignments, evaluations_per_work
        )
        print(f"完成了{len(session.evaluations)}次互评")
        
        # 保存模拟结果
        self._save_simulation_session(session)
        
        print(f"\n模拟完成！会话ID: {session.session_id}")
        return session
    
    def _generate_student_works(self, students: List[Student], 
                              assignments: List[Assignment]) -> List[StudentWork]:
        """生成学生作品"""
        works = []
        
        # 为每个作业分配学生完成作业
        for assignment in tqdm(assignments, desc="生成作业"):
            # 使用配置的完成率，如果设置为1.0则所有学生都完成
            if Config.ASSIGNMENT_COMPLETION_RATE >= 1.0:
                participating_students = students  # 所有学生都参与
            else:
                # 随机选择指定比例的学生完成作业
                num_participants = max(1, int(len(students) * Config.ASSIGNMENT_COMPLETION_RATE))
                participating_students = random.sample(students, num_participants)
            
            print(f"  作业 '{assignment.title}': {len(participating_students)}/{len(students)} 名学生参与")
            
            for student in participating_students:
                try:
                    # 创建学生代理，配置智能记忆系统
                    memory_config = {
                        "index_dimension": 100,
                        "cache_size": 500,
                        "buffer_size": 2000,
                        "batch_size": 16
                    }
                    student_agent = StudentAgent(student, memory_config)
                    
                    # 确保记忆目录存在并加载学生的记忆状态
                    memory_path = f"data/memory_states"
                    os.makedirs(memory_path, exist_ok=True)
                    student_agent.load_memory_state(memory_path)
                    
                    work = student_agent.complete_assignment(assignment)
                    works.append(work)
                    
                    # 保存记忆状态
                    student_agent.save_memory_state(memory_path)
                    
                except Exception as e:
                    print(f"学生 {student.name} 完成作业时出错: {e}")
                    continue
        
        return works
    
    def _conduct_peer_evaluations(self, students: List[Student], 
                                works: List[StudentWork],
                                assignments: List[Assignment],
                                evaluations_per_work: int) -> List[PeerEvaluation]:
        """执行同伴互评"""
        evaluations = []
        
        # 按作业分组作品
        works_by_assignment = {}
        for work in works:
            if work.assignment_id not in works_by_assignment:
                works_by_assignment[work.assignment_id] = []
            works_by_assignment[work.assignment_id].append(work)
        
        # 为每个作业的作品安排互评
        for assignment in tqdm(assignments, desc="执行互评"):
            assignment_works = works_by_assignment.get(assignment.id, [])
            if len(assignment_works) < 2:
                continue  # 至少需要2个作品才能互评
            
            # 为每个作品分配评估者
            for work in assignment_works:
                # 找出除作者外的其他学生作为潜在评估者
                potential_evaluators = [
                    s for s in students 
                    if s.id != work.student_id and 
                    any(w.student_id == s.id for w in assignment_works)  # 确保评估者也提交了作业
                ]
                
                if len(potential_evaluators) < evaluations_per_work:
                    # 如果潜在评估者不够，就用所有可用的
                    selected_evaluators = potential_evaluators
                else:
                    # 随机选择指定数量的评估者
                    selected_evaluators = random.sample(potential_evaluators, evaluations_per_work)
                
                # 找到作品作者
                work_author = next((s for s in students if s.id == work.student_id), None)
                if not work_author:
                    continue
                
                # 执行评估
                for evaluator in selected_evaluators:
                    try:
                        evaluator_agent = EvaluatorAgent(evaluator)
                        evaluation = evaluator_agent.evaluate_work(work, assignment, work_author)
                        evaluations.append(evaluation)
                    except Exception as e:
                        print(f"评估者 {evaluator.name} 评估作品时出错: {e}")
                        continue
        
        return evaluations
    
    def _save_simulation_session(self, session: SimulationSession):
        """保存模拟会话数据"""
        import os
        
        # 创建会话目录
        session_dir = os.path.join(Config.DATA_DIR, f"session_{session.session_id}")
        os.makedirs(session_dir, exist_ok=True)
        
        # 保存学生数据
        students_data = [student.to_dict() for student in session.students]
        with open(os.path.join(session_dir, "students.json"), 'w', encoding='utf-8') as f:
            json.dump(students_data, f, ensure_ascii=False, indent=2, default=str)
        
        # 保存作业数据
        assignments_data = [assignment.to_dict() for assignment in session.assignments]
        with open(os.path.join(session_dir, "assignments.json"), 'w', encoding='utf-8') as f:
            json.dump(assignments_data, f, ensure_ascii=False, indent=2, default=str)
        
        # 保存作品数据
        works_data = [work.to_dict() for work in session.works]
        with open(os.path.join(session_dir, "works.json"), 'w', encoding='utf-8') as f:
            json.dump(works_data, f, ensure_ascii=False, indent=2, default=str)
        
        # 保存评估数据
        evaluations_data = [evaluation.to_dict() for evaluation in session.evaluations]
        with open(os.path.join(session_dir, "evaluations.json"), 'w', encoding='utf-8') as f:
            json.dump(evaluations_data, f, ensure_ascii=False, indent=2, default=str)
        
        # 保存会话统计
        statistics = session.get_statistics()
        with open(os.path.join(session_dir, "statistics.json"), 'w', encoding='utf-8') as f:
            json.dump(statistics, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"模拟数据已保存到: {session_dir}")
    
    def load_simulation_session(self, session_id: str) -> SimulationSession:
        """加载已保存的模拟会话"""
        import os
        
        session_dir = os.path.join(Config.DATA_DIR, f"session_{session_id}")
        if not os.path.exists(session_dir):
            raise FileNotFoundError(f"找不到会话: {session_id}")
        
        # 加载各类数据
        with open(os.path.join(session_dir, "students.json"), 'r', encoding='utf-8') as f:
            students_data = json.load(f)
            students = [Student(**data) for data in students_data]
        
        with open(os.path.join(session_dir, "assignments.json"), 'r', encoding='utf-8') as f:
            assignments_data = json.load(f)
            assignments = [Assignment(**data) for data in assignments_data]
        
        with open(os.path.join(session_dir, "works.json"), 'r', encoding='utf-8') as f:
            works_data = json.load(f)
            works = [StudentWork(**data) for data in works_data]
        
        with open(os.path.join(session_dir, "evaluations.json"), 'r', encoding='utf-8') as f:
            evaluations_data = json.load(f)
            evaluations = [PeerEvaluation(**data) for data in evaluations_data]
        
        return SimulationSession(
            session_id=session_id,
            created_at=datetime.now(),  # 这里可以从文件中读取实际创建时间
            parameters={},
            students=students,
            assignments=assignments,
            works=works,
            evaluations=evaluations
        )
