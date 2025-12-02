import random
import uuid
from typing import List, Dict, Any
import numpy as np
from faker import Faker
from models.data_models import Student, StudentType
from config.settings import Config

class StudentGenerator:
    """学生生成器"""
    
    def __init__(self):
        self.fake = Faker('zh_CN')
        self.majors = [
            "计算机科学与技术", "软件工程", "网络工程", "信息安全",
            "数据科学与大数据技术", "人工智能", "物联网工程", "数字媒体技术"
        ]
        
        self.personality_traits = [
            "conscientiousness",  # 尽责性
            "openness",          # 开放性
            "agreeableness",     # 宜人性
            "extraversion",      # 外向性
            "neuroticism"        # 神经质
        ]
    
    def generate_students(self, count: int) -> List[Student]:
        """生成指定数量的学生"""
        students = []
        
        # 根据配置的比例分配学生类型
        type_counts = self._calculate_type_distribution(count)
        
        for student_type, type_count in type_counts.items():
            for _ in range(type_count):
                student = self._generate_single_student(StudentType(student_type))
                students.append(student)
        
        return students
    
    def _calculate_type_distribution(self, total_count: int) -> Dict[str, int]:
        """计算各学生类型的数量分布"""
        # 小样本优化：确保每种类型至少有机会被选中
        if total_count <= 10:
            return self._calculate_small_sample_distribution(total_count)
        
        distribution = {}
        remaining = total_count
        
        for student_type, config in Config.STUDENT_TYPES.items():
            if student_type == list(Config.STUDENT_TYPES.keys())[-1]:
                # 最后一个类型分配剩余的所有学生
                distribution[student_type] = remaining
            else:
                count = int(total_count * config["ratio"])
                distribution[student_type] = count
                remaining -= count
        
        return distribution
    
    def _calculate_small_sample_distribution(self, total_count: int) -> Dict[str, int]:
        """小样本分配策略：使用加权随机采样，确保多样性"""
        import numpy as np
        
        # 获取类型和权重
        types = list(Config.STUDENT_TYPES.keys())
        weights = [Config.STUDENT_TYPES[t]["ratio"] for t in types]
        
        # 使用加权随机采样（不放回）
        selected_types = np.random.choice(
            types, 
            size=total_count, 
            replace=True,  # 允许重复，但通过权重控制
            p=weights
        )
        
        # 统计各类型数量
        distribution = {t: 0 for t in types}
        for t in selected_types:
            distribution[t] += 1
        
        return distribution
    
    def _generate_single_student(self, student_type: StudentType) -> Student:
        """生成单个学生"""
        student_id = str(uuid.uuid4())
        name = self.fake.name()
        
        # 根据学生类型调整属性
        type_config = Config.STUDENT_TYPES[student_type.value]
        
        # 生成GPA（根据学生类型调整）
        base_gpa = self._generate_gpa_by_type(student_type)
        
        # 生成编程经验
        programming_exp = self._generate_programming_experience(student_type)
        
        # 生成性格特征
        personality = self._generate_personality_traits(student_type)
        
        return Student(
            id=student_id,
            name=name,
            student_type=student_type,
            academic_level=random.choice(["undergraduate", "graduate"]),
            major=random.choice(self.majors),
            gpa=base_gpa,
            programming_experience=programming_exp,
            personality_traits=personality
        )
    
    def _generate_gpa_by_type(self, student_type: StudentType) -> float:
        """根据学生类型生成GPA"""
        if student_type == StudentType.EXCELLENT:
            return round(random.uniform(3.7, 4.0), 2)
        elif student_type == StudentType.GOOD:
            return round(random.uniform(3.3, 3.8), 2)
        elif student_type == StudentType.AVERAGE:
            return round(random.uniform(2.8, 3.4), 2)
        elif student_type == StudentType.BELOW_AVERAGE:
            return round(random.uniform(2.0, 2.9), 2)
        elif student_type == StudentType.PERFUNCTORY:
            return round(random.uniform(2.5, 3.2), 2)
        else:  # STRICT or LENIENT
            return round(random.uniform(3.0, 3.6), 2)
    
    def _generate_programming_experience(self, student_type: StudentType) -> int:
        """根据学生类型生成编程经验年限"""
        if student_type == StudentType.EXCELLENT:
            return random.randint(3, 6)
        elif student_type == StudentType.GOOD:
            return random.randint(2, 4)
        elif student_type == StudentType.AVERAGE:
            return random.randint(1, 3)
        elif student_type == StudentType.BELOW_AVERAGE:
            return random.randint(0, 2)
        elif student_type == StudentType.PERFUNCTORY:
            return random.randint(1, 2)
        else:  # STRICT or LENIENT
            return random.randint(2, 4)
    
    def _generate_personality_traits(self, student_type: StudentType) -> Dict[str, float]:
        """生成性格特征（0-1之间的值）"""
        traits = {}
        
        for trait in self.personality_traits:
            if student_type == StudentType.EXCELLENT:
                # 优秀学生：高尽责性、高开放性
                if trait == "conscientiousness":
                    traits[trait] = round(random.uniform(0.7, 0.9), 2)
                elif trait == "openness":
                    traits[trait] = round(random.uniform(0.6, 0.8), 2)
                else:
                    traits[trait] = round(random.uniform(0.4, 0.7), 2)
            
            elif student_type == StudentType.STRICT:
                # 严格学生：高尽责性、低宜人性
                if trait == "conscientiousness":
                    traits[trait] = round(random.uniform(0.8, 0.9), 2)
                elif trait == "agreeableness":
                    traits[trait] = round(random.uniform(0.2, 0.4), 2)
                else:
                    traits[trait] = round(random.uniform(0.4, 0.7), 2)
            
            elif student_type == StudentType.LENIENT:
                # 宽松学生：高宜人性、低尽责性
                if trait == "agreeableness":
                    traits[trait] = round(random.uniform(0.7, 0.9), 2)
                elif trait == "conscientiousness":
                    traits[trait] = round(random.uniform(0.3, 0.5), 2)
                else:
                    traits[trait] = round(random.uniform(0.4, 0.7), 2)
            
            elif student_type == StudentType.PERFUNCTORY:
                # 敷衍学生：低尽责性、低开放性、高神经质
                if trait == "conscientiousness":
                    traits[trait] = round(random.uniform(0.2, 0.4), 2)
                elif trait == "openness":
                    traits[trait] = round(random.uniform(0.2, 0.4), 2)
                elif trait == "neuroticism":
                    traits[trait] = round(random.uniform(0.6, 0.8), 2)
                else:
                    traits[trait] = round(random.uniform(0.3, 0.6), 2)
            
            else:
                # 其他类型学生：随机分布
                traits[trait] = round(random.uniform(0.3, 0.7), 2)
        
        return traits
