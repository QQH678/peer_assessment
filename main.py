#!/usr/bin/env python3
"""
同伴互评模拟系统主程序
"""

import argparse
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from simulation.simulator import PeerAssessmentSimulator
from simulation.semester_simulator import SemesterSimulator
from config.settings import Config
from config.peer_review_config import PeerReviewConfig

def run_basic_simulation():
    """运行基础模拟实验"""
    print("=== 开始基础同伴互评模拟 ===")
    
    simulator = PeerAssessmentSimulator()
    
    # 运行模拟
    session = simulator.run_simulation(
        student_count=3,
        assignment_count=1,
        evaluations_per_work=2
    )
    
    print("=== 模拟完成 ===")
    print(f"会话ID: {session.session_id}")
    print(f"学生数量: {len(session.students)}")
    print(f"作业数量: {len(session.assignments)}")
    print(f"作品数量: {len(session.works)}")
    print(f"互评数量: {len(session.evaluations)}")
    
    return session

def run_large_scale_simulation():
    """运行大规模模拟实验"""
    print("=== 开始大规模同伴互评模拟 ===")
    
    simulator = PeerAssessmentSimulator()
    
    # 运行大规模模拟
    session = simulator.run_simulation(
        student_count=100,
        assignment_count=5,
        evaluations_per_work=4
    )
    
    print("\n=== 大规模模拟完成 ===")
    return session

def run_bias_analysis_simulation():
    """运行偏差分析模拟实验"""
    print("=== 开始偏差分析模拟 ===")
    
    # 修改学生类型配置以突出偏差
    original_config = Config.STUDENT_TYPES.copy()
    
    # 增加严格和宽松学生的比例
    Config.STUDENT_TYPES = {
        "excellent": {"ratio": 0.15, "score_bias": 0.1, "strictness": 0.8},
        "good": {"ratio": 0.15, "score_bias": 0.05, "strictness": 0.7},
        "average": {"ratio": 0.2, "score_bias": 0.0, "strictness": 0.6},
        "below_average": {"ratio": 0.1, "score_bias": -0.05, "strictness": 0.5},
        "strict": {"ratio": 0.15, "score_bias": -0.15, "strictness": 0.9},
        "lenient": {"ratio": 0.15, "score_bias": 0.2, "strictness": 0.3},
        "perfunctory": {"ratio": 0.1, "score_bias": 0.05, "strictness": 0.2}
    }
    
    simulator = PeerAssessmentSimulator()
    session = simulator.run_simulation(
        student_count=50,
        assignment_count=4,
        evaluations_per_work=5
    )
    
    # 恢复原始配置
    Config.STUDENT_TYPES = original_config
    
    print("\n=== 偏差分析模拟完成 ===")
    return session

def run_semester_teaching_simulation():
    """运行学期教学模拟"""
    print("=== 开始学期教学模拟 ===")
    
    semester_simulator = SemesterSimulator()
    
    # 运行学期模拟
    semester = semester_simulator.run_semester_simulation(
        course_name="Python程序设计",
        subject="计算机科学",
        student_count=25,
        duration_weeks=16,
        evaluations_per_assignment=3
    )
    
    print("\n=== 学期教学模拟完成 ===")
    return semester

def run_new_memory_simulation(args):
    """运行使用新记忆系统的模拟"""
    print("=== 开始新记忆系统模拟 ===")
    print(f"配置:")
    print(f"  - 每阶段轮次: {args.rounds_per_stage}")
    print(f"  - 每轮评价同伴数: {args.peers_per_round}")
    print(f"  - 记忆温度: {args.memory_temperature}")
    print(f"  - 使用新记忆: {args.use_new_memory}")
    print(f"  - 教师分析: {args.enable_teacher_analysis}")
    
    # 创建互评配置
    peer_review_config = PeerReviewConfig.create_custom(
        rounds_per_stage=args.rounds_per_stage,
        peers_per_round=args.peers_per_round,
        reviews_per_work=args.reviews_per_work,
        base_temperature=args.memory_temperature
    )
    
    # 创建模拟器并传入配置
    simulator = PeerAssessmentSimulator()
    
    # 使用新配置运行
    session = simulator.run_simulation(
        student_count=args.student_count or 10,
        assignment_count=args.assignment_count or 2,
        evaluations_per_work=args.reviews_per_work,
        use_new_memory=args.use_new_memory,
        enable_teacher_analysis=args.enable_teacher_analysis,
        peer_review_config=peer_review_config
    )
    
    print("\n=== 新记忆系统模拟完成 ===")
    print(f"会话ID: {session.session_id}")
    print(f"学生数: {len(session.students)}")
    print(f"作业数: {len(session.assignments)}")
    
    return session
    
    print("=== 学期教学模拟完成 ===")
    print(f"学期ID: {semester.id}")
    print(f"课程名称: {semester.course.name}")
    print(f"教学阶段: {len(semester.course.teaching_stages)}个")
    print(f"知识点: {len(semester.course.knowledge_points)}个")
    print(f"学生: {len(semester.students)}人")
    print(f"作业: {len(semester.assignments)}个")
    print(f"作品: {len(semester.works)}个")
    print(f"互评: {len(semester.evaluations)}次")
    
    return semester

def run_advanced_semester_simulation():
    """运行高级学期教学模拟（多课程）"""
    print("=== 开始高级学期教学模拟 ===")
    
    semester_simulator = SemesterSimulator()
    
    # 运行数据结构课程模拟
    semester1 = semester_simulator.run_semester_simulation(
        course_name="数据结构与算法",
        subject="计算机科学",
        student_count=30,
        duration_weeks=16,
        evaluations_per_assignment=4
    )
    
    print("\n" + "="*50)
    
    # 运行软件工程课程模拟
    semester2 = semester_simulator.run_semester_simulation(
        course_name="软件工程实践",
        subject="软件工程",
        student_count=28,
        duration_weeks=16,
        evaluations_per_assignment=3
    )
    
    print("=== 高级学期教学模拟完成 ===")
    return [semester1, semester2]

def analyze_existing_session(session_id: str):
    """分析已存在的模拟会话"""
    print(f"=== 查看会话 {session_id} ===")
    
    simulator = PeerAssessmentSimulator()
    try:
        session = simulator.load_simulation_session(session_id)
        
        print("会话信息:")
        print(f"  学生数量: {len(session.students)}")
        print(f"  作业数量: {len(session.assignments)}")
        print(f"  作品数量: {len(session.works)}")
        print(f"  互评数量: {len(session.evaluations)}")
        
        # 简单统计
        if session.evaluations:
            scores = []
            for eval in session.evaluations:
                weighted_score = eval.scores.get_weighted_score(Config.EVALUATION_WEIGHTS)
                scores.append(weighted_score)
            
            avg_score = sum(scores) / len(scores)
            print(f"  平均评分: {avg_score:.2f}")
        
        print("查看完成！")
        return session
    except FileNotFoundError:
        print(f"错误：找不到会话 {session_id}")
        return None

def list_available_sessions():
    """列出可用的模拟会话"""
    data_dir = Config.DATA_DIR
    if not os.path.exists(data_dir):
        print("没有找到数据目录")
        return
    
    sessions = []
    for item in os.listdir(data_dir):
        if item.startswith("session_"):
            session_id = item[8:]  # 移除"session_"前缀
            sessions.append(session_id)
    
    if sessions:
        print("可用的模拟会话:")
        for i, session_id in enumerate(sessions, 1):
            print(f"{i}. {session_id}")
    else:
        print("没有找到已保存的模拟会话")
    
    return sessions

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="同伴互评模拟系统")
    parser.add_argument("--experiment", "-e", 
                       choices=["basic", "large_scale", "bias_analysis", "semester", "advanced_semester", "new_memory"],
                       default="basic",
                       help="选择实验类型")
    parser.add_argument("--analyze", "-a",
                       type=str,
                       help="分析指定的会话ID")
    parser.add_argument("--list", "-l",
                       action="store_true",
                       help="列出所有可用的会话")
    parser.add_argument("--student-count", "-s",
                       type=int,
                       help="学生数量")
    parser.add_argument("--assignment-count", "-ac",
                       type=int,
                       help="作业数量")
    parser.add_argument("--evaluations-per-work", "-ev",
                       type=int,
                       help="每个作业的互评次数")
    # 新增学期教学相关参数
    parser.add_argument("--course-name", "-cn",
                       type=str,
                       default="Python程序设计",
                       help="课程名称")
    parser.add_argument("--subject", "-sub",
                       type=str,
                       default="计算机科学",
                       help="学科领域")
    parser.add_argument("--duration-weeks", "-dw",
                       type=int,
                       default=16,
                       help="课程周数")
    
    # 新增：互评轮次配置参数
    parser.add_argument("--rounds-per-stage", "-rps",
                       type=int,
                       default=3,
                       help="每个教学阶段的互评轮次数")
    parser.add_argument("--peers-per-round", "-ppr",
                       type=int,
                       default=2,
                       help="每轮评价的同伴数量")
    parser.add_argument("--reviews-per-work", "-rpw",
                       type=int,
                       default=2,
                       help="每份作业收到的评价数量")
    
    # 新增：记忆系统配置
    parser.add_argument("--use-new-memory", "-unm",
                       action="store_true",
                       default=True,
                       help="使用新的三维记忆系统")
    parser.add_argument("--memory-temperature", "-mt",
                       type=float,
                       default=1.0,
                       help="记忆检索温度参数")
    parser.add_argument("--enable-teacher-analysis", "-eta",
                       action="store_true",
                       default=True,
                       help="启用教师智能分析功能")
    
    args = parser.parse_args()
    
    # 确保必要的目录存在
    Config.ensure_directories()
    
    if args.list:
        list_available_sessions()
        return
    
    if args.analyze:
        analyze_existing_session(args.analyze)
        return
    
    # 运行模拟实验
    if args.experiment == "basic":
        session = run_basic_simulation()
    elif args.experiment == "large_scale":
        session = run_large_scale_simulation()
    elif args.experiment == "bias_analysis":
        session = run_bias_analysis_simulation()
    elif args.experiment == "new_memory":
        # 使用新记忆系统和配置
        session = run_new_memory_simulation(args)
    elif args.experiment == "semester":
        # 使用命令行参数运行学期教学模拟（集成新记忆系统）
        from config.peer_review_config import PeerReviewConfig
        
        # 创建配置
        peer_config = PeerReviewConfig(
            rounds_per_stage=args.rounds_per_stage,
            peers_per_round=args.peers_per_round,
            reviews_per_work=args.reviews_per_work,
            base_temperature=args.memory_temperature
        )
        
        semester_simulator = SemesterSimulator(
            use_new_memory=args.use_new_memory,
            peer_config=peer_config
        )
        semester = semester_simulator.run_semester_simulation(
            course_name=args.course_name,
            subject=args.subject,
            student_count=args.student_count or 25,
            duration_weeks=args.duration_weeks,
            evaluations_per_assignment=args.evaluations_per_work or 3
        )
    elif args.experiment == "advanced_semester":
        semesters = run_advanced_semester_simulation()
    else:
        print(f"未知的实验类型: {args.experiment}")
        return

if __name__ == "__main__":
    main()
