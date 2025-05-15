import json
import logging
import requests  # 使用同步请求库
from fastapi import HTTPException
from config import settings

logger = logging.getLogger(__name__)

# 缓存API响应（5分钟）
# cache = TTLCache(maxsize=1000, ttl=300)


class DeepSeekClassifier:
    def __init__(self):
        self.api_key = settings.deepseek_api_key
        self.base_url = "https://api.deepseek.com/v1"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

    def classify(self, bookmarks: list) -> list:
        """同步分类书签"""
        # 生成缓存key，通过排序和json化避免重复的bookmarks
        # cache_key = self._generate_cache_key(bookmarks)
        # if cache_key in cache:
        #     return cache[cache_key]

        try:
            # 使用requests库发送同步请求
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=self._build_payload(bookmarks),
                timeout=1000
            )
            response.raise_for_status()  # 检查响应是否成功

            result = self._parse_response(response.json())
            # cache[cache_key] = result
            return result

        except requests.exceptions.RequestException as e:
            logger.error(f"DeepSeek API request failed: {str(e)}")
            raise HTTPException(status_code=503, detail="AI service unavailable")
        except requests.exceptions.HTTPError as e:
            logger.error(f"DeepSeek API returned an error: {str(e)}")
            raise HTTPException(status_code=503, detail="AI service unavailable")

    def _generate_cache_key(self, bookmarks: list) -> str:
        """生成缓存的唯一key"""
        return hash(json.dumps(bookmarks, sort_keys=True))  # 通过JSON的排序来确保相同内容的书签有相同的key

    def _build_payload(self, bookmarks):
        """构建请求负载"""
        return {
            "model": "deepseek-chat",
            "messages": [{
                "role": "user",
                "content": f"Classify these bookmarks into JSON format with title, url and tags. "
                           f"Return only 1 most relevant tags per item. "
                           f"Input: {json.dumps(bookmarks)}"
            }],
            "stream": False
        }

    def _parse_response(self, response):
        """解析 DeepSeek API 的响应"""
        try:
            content = response["choices"][0]["message"]["content"]
            json_start = content.find('[')  # JSON 数据开始的位置
            json_end = content.rfind(']')  # JSON 数据结束的位置
            json_str = content[json_start:json_end + 1]

            # 将提取的 JSON 字符串转换为 Python 对象
            classified_data = json.loads(json_str)

            # 初始化分类后的书签数据
            categorized_bookmarks = []

            # 遍历 JSON 数据，组织每个书签的分类
            for item in classified_data:
                categorized_bookmarks.append({
                    'title': item.get('title', '').strip(),
                    'url': item.get('url', '').strip(),
                    'tags': item.get('tags', '').strip()
                })
            # 返回分类后的书签列表
            return categorized_bookmarks

        except (KeyError, json.JSONDecodeError, ValueError) as e:
            logger.error(f"Parsing DeepSeek response failed: {str(e)}")
            raise HTTPException(status_code=422, detail="AI response parsing failed")