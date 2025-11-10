from openai import OpenAI



class DouBaoModel:
    def __init__(self):
        # 初始化AI客户端
        self.client = OpenAI(
            base_url="https://ark.cn-beijing.volces.com/api/v3",
            api_key="baea195a-fe33-4be1-9c68-9292a4a66a5c",
        )
        
        # 违禁词列表
        self.prohibited_words = [
            "国家级", "世界级", "最高级", "第一", "唯一", "首个", "首选", "顶级",
            "金牌", "名牌", "优秀", "顶级", "独家", "全网销量第一", "全球首发", "全国首家", "全网首发", "世界领先",
            "顶级工艺", "销量冠军", "第一品牌", "极致", "永久", "王牌",
            "领袖品牌", "独一无二", "绝无仅有", "史无前例", "万能", "最高", "最低", "最具", "最便宜",
            "最新", "最先进", "最大程度", "最新技术", "最先进科学",
            "最佳", "最大", "最好", "最新科学", "最新技术", "最先进加工工艺",
            "最时尚", "最受欢迎", "最先", "绝对值", "绝对", "大牌", "精确", "超赚",
        ]

    

    def generate_text(self, system_prompt):
        # 生成文本
        response = self.client.chat.completions.create(
            model="doubao-seed-1-6-250615",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "请根据参考文案生成学校介绍文案"},
            ],
            temperature=0.7,
        )
        # 安全地获取响应内容
        content = ""
        if response and response.choices and len(response.choices) > 0:
            choice = response.choices[0]
            if choice and hasattr(choice, 'message'):
                message = choice.message
                if message and hasattr(message, 'content') and message.content is not None:
                    content = message.content
        return content
