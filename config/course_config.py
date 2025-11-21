"""
课程配置管理器
提供动态获取课程评价维度的接口
"""

from typing import List, Dict, Optional
from config.course_templates import COURSE_TEMPLATES


class CourseConfig:
    """课程配置管理器"""
    
    def __init__(self):
        self.templates = COURSE_TEMPLATES
    
    def get_evaluation_dimensions(self, course_type: str) -> List[Dict[str, str]]:
        """
        获取课程类型的评价维度
        
        Args:
            course_type: 课程类型 (programming, writing, design, theory, experiment, mathematics, generic)
        
        Returns:
            评价维度列表，每个维度包含 key, name, name_en, description
            
        Examples:
            >>> config = CourseConfig()
            >>> dims = config.get_evaluation_dimensions("programming")
            >>> [d["name"] for d in dims]
            ['功能实现', '代码质量', '创新性', '文档完整性']
        """
        if course_type not in self.templates:
            course_type = "generic"
        
        return self.templates[course_type]["evaluation_dimensions"]
    
    def get_dimension_names(self, course_type: str, lang: str = "zh") -> List[str]:
        """
        获取维度名称列表
        
        Args:
            course_type: 课程类型
            lang: 语言 ("zh" 或 "en")
        
        Returns:
            维度名称列表
            
        Examples:
            >>> config = CourseConfig()
            >>> config.get_dimension_names("writing")
            ['内容质量', '结构组织', '语言表达', '原创性']
            >>> config.get_dimension_names("writing", lang="en")
            ['Content Quality', 'Structure', 'Language', 'Originality']
        """
        dimensions = self.get_evaluation_dimensions(course_type)
        name_key = "name" if lang == "zh" else "name_en"
        return [dim[name_key] for dim in dimensions]
    
    def get_dimension_keys(self, course_type: str) -> List[str]:
        """
        获取维度键列表
        
        Args:
            course_type: 课程类型
        
        Returns:
            维度键列表 (用于代码中的字段名)
            
        Examples:
            >>> config = CourseConfig()
            >>> config.get_dimension_keys("design")
            ['aesthetics', 'usability', 'creativity', 'completeness']
        """
        dimensions = self.get_evaluation_dimensions(course_type)
        return [dim["key"] for dim in dimensions]
    
    def get_dimension_descriptions(self, course_type: str) -> Dict[str, str]:
        """
        获取维度描述字典 {名称: 描述}
        
        Args:
            course_type: 课程类型
        
        Returns:
            维度描述字典
            
        Examples:
            >>> config = CourseConfig()
            >>> descs = config.get_dimension_descriptions("mathematics")
            >>> descs["正确性"]
            '推导过程和结果是否正确，计算是否准确'
        """
        dimensions = self.get_evaluation_dimensions(course_type)
        return {dim["name"]: dim["description"] for dim in dimensions}
    
    def get_dimension_mapping(self, course_type: str) -> Dict[str, str]:
        """
        获取维度键到名称的映射 {key: name}
        
        Args:
            course_type: 课程类型
        
        Returns:
            键到名称的映射字典
            
        Examples:
            >>> config = CourseConfig()
            >>> mapping = config.get_dimension_mapping("experiment")
            >>> mapping["procedure"]
            '实验步骤'
        """
        dimensions = self.get_evaluation_dimensions(course_type)
        return {dim["key"]: dim["name"] for dim in dimensions}
    
    def infer_course_type(self, subject: str) -> str:
        """
        根据科目名称推断课程类型
        
        Args:
            subject: 科目名称
        
        Returns:
            课程类型
            
        Examples:
            >>> config = CourseConfig()
            >>> config.infer_course_type("数据结构与算法")
            'programming'
            >>> config.infer_course_type("学术写作")
            'writing'
            >>> config.infer_course_type("未知课程")
            'generic'
        """
        for course_type, template in self.templates.items():
            if course_type == "generic":
                continue  # 最后考虑通用类型
            
            if subject in template["subjects"]:
                return course_type
        
        # 默认返回通用类型
        return "generic"
    
    def get_course_type_name(self, course_type: str, lang: str = "zh") -> str:
        """
        获取课程类型的显示名称
        
        Args:
            course_type: 课程类型
            lang: 语言
        
        Returns:
            课程类型显示名称
            
        Examples:
            >>> config = CourseConfig()
            >>> config.get_course_type_name("programming")
            '编程实践类'
            >>> config.get_course_type_name("programming", lang="en")
            'Programming'
        """
        if course_type not in self.templates:
            course_type = "generic"
        
        name_key = "name" if lang == "zh" else "name_en"
        return self.templates[course_type][name_key]
    
    def get_all_subjects(self) -> Dict[str, List[str]]:
        """
        获取所有课程类型及其对应的科目
        
        Returns:
            {课程类型: [科目列表]}
        """
        return {
            course_type: template["subjects"]
            for course_type, template in self.templates.items()
            if course_type != "generic"
        }
    
    def format_evaluation_criteria_prompt(self, course_type: str) -> str:
        """
        生成评价标准的提示词格式
        
        Args:
            course_type: 课程类型
        
        Returns:
            格式化的评价标准提示词
            
        Examples:
            >>> config = CourseConfig()
            >>> print(config.format_evaluation_criteria_prompt("writing"))
            请按以下维度评价：
            
            1. 内容质量: 论点是否清晰，论据是否充分，内容是否深入
               评分: [0-100分]
               评语: [具体评价]
            
            2. 结构组织: 文章结构是否合理，逻辑是否清晰，层次是否分明
               评分: [0-100分]
               评语: [具体评价]
            ...
        """
        dimensions = self.get_evaluation_dimensions(course_type)
        
        prompt = "请按以下维度评价：\n\n"
        for i, dim in enumerate(dimensions, 1):
            prompt += f"{i}. {dim['name']}: {dim['description']}\n"
            prompt += f"   评分: [0-100分]\n"
            prompt += f"   评语: [具体评价]\n\n"
        
        return prompt.strip()


# 全局单例
_course_config_instance = None

def get_course_config() -> CourseConfig:
    """获取课程配置管理器单例"""
    global _course_config_instance
    if _course_config_instance is None:
        _course_config_instance = CourseConfig()
    return _course_config_instance


if __name__ == "__main__":
    # 测试代码
    config = CourseConfig()
    
    print("=" * 80)
    print("课程配置管理器测试")
    print("=" * 80)
    
    # 测试不同课程类型
    test_types = ["programming", "writing", "design", "theory"]
    
    for course_type in test_types:
        print(f"\n课程类型: {config.get_course_type_name(course_type)}")
        print(f"评价维度: {config.get_dimension_names(course_type)}")
        print(f"维度键: {config.get_dimension_keys(course_type)}")
    
    # 测试科目推断
    print("\n" + "=" * 80)
    print("科目推断测试")
    print("=" * 80)
    test_subjects = [
        "数据结构与算法",
        "学术写作",
        "UI设计",
        "经济学",
        "物理实验",
        "高等数学",
        "未知课程"
    ]
    
    for subject in test_subjects:
        course_type = config.infer_course_type(subject)
        print(f"{subject:<15} -> {course_type:<15} ({config.get_course_type_name(course_type)})")
    
    print("\n测试完成！")
