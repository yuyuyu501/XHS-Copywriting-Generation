class SystemPromptTemplate:
    def __init__(self, type):
        self.type = type

    def _generate_school_introduction_prompt(self, reference_text):
        # 使用AI生成学校介绍文案

        system_prompt = f"""请根据以下参考文案的风格和内容，生成一段新的学校介绍文案。

        参考文案: "{reference_text}"

        生成要求：
        1. 基于参考文案的风格和结构
        2. 突出学校的特色和优势
        3. 语言自然流畅，符合小红书平台风格
        4. 避免出现具体人名、联系方式等个人信息
        5. 保持积极正面的教育导向
        6. 使用第一人称视角，分享真实感受
        7. 适当使用emoji表情和分行格式
        8. 内容需涵盖小学、初中或高中阶段的教育特色
        9. 标题: "生成的标题在这里"
        10. 文案: "生成的文案内容"

        请直接输出完整的标题和文案内容，格式为：
        标题: 生成的标题内容
        文案: 生成的文案内容

        生成内容："""

        return system_prompt
    
    def _generate_admission_guidance_prompt(self, reference_text):
        # 使用AI生成升学指导文案

        system_prompt = f"""请根据以下参考文案的风格和内容，生成一段新的升学指导文案。

        参考文案: "{reference_text}"

        生成要求：
        1. 基于参考文案的风格和结构
        2. 突出升学的重要性和备考策略
        3. 语言自然流畅，符合小红书平台风格
        4. 避免出现具体人名、联系方式等个人信息
        5. 保持积极正面的教育导向
        6. 使用第一人称视角，分享真实感受
        7. 适当使用emoji表情和分行格式
        8. 内容需涵盖小学升初中、初中升高中阶段
        9. 标题: "生成的标题在这里"
        10. 文案: "生成的文案内容"

        请直接输出完整的标题和文案内容，格式为：
        标题: 生成的标题内容
        文案: 生成的文案内容

        生成内容："""

        return system_prompt
    
    def choice_system_prompt(self, **kwargs):
        reference_text = kwargs.get('reference_text', '')
        # 确保reference_text是字符串类型
        if not isinstance(reference_text, str):
            reference_text = ''
        if self.type == '学校介绍':
            return self._generate_school_introduction_prompt(reference_text)
        elif self.type == '升学指导':
            return self._generate_admission_guidance_prompt(reference_text)

