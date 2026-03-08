# -*- encoding: utf-8 -*-
"""
目标识别和信息获取模块

负责解析用户输入的目标（URL或ID），识别目标类型，并获取目标的基本信息
"""

import os
import re
from urllib.parse import parse_qs, quote, unquote, urlparse

import ujson as json
from loguru import logger

from ...utils.text import quit, sanitize_filename, url_redirect
from .request import Request
from .types import USER_ID_PREFIX, DouyinURL

# 从粘贴文本中提取抖音链接（如分享文案中含 https://v.douyin.com/xxx）
DOUYIN_URL_PATTERN = re.compile(
    r"https?://(?:v\.|www\.)?douyin\.com/[^\s\]\)\"'\u4e00-\u9fff]+",
    re.IGNORECASE,
)
# 无协议短链：v.douyin.com/xxx
DOUYIN_SHORT_PATTERN = re.compile(
    r"(?:^|(?<![/.]))v\.douyin\.com/[A-Za-z0-9_-]+",
    re.IGNORECASE,
)


def _extract_douyin_url(text: str) -> str | None:
    """从整段粘贴内容中提取第一个抖音链接，若无则返回 None"""
    if not text or not text.strip():
        return None
    text = text.strip()
    # 先匹配完整 URL
    match = DOUYIN_URL_PATTERN.search(text)
    if match:
        url = match.group(0).rstrip("，。！？、,;!")
        return url
    # 再匹配无协议的 v.douyin.com/xxx
    match = DOUYIN_SHORT_PATTERN.search(text)
    if match:
        return "https://" + match.group(0).strip()
    return None


class TargetHandler:
    """目标处理器：负责目标识别和信息获取"""

    def __init__(self, request: Request, target: str, type: str, down_path: str):
        """
        初始化目标处理器

        Args:
            request: Request实例
            target: 目标URL或ID
            type: 目标类型
            down_path: 下载路径
        """
        self.request = request
        self.target = target
        self.type = type
        self.down_path = down_path
        self.id = ""
        self.url = ""
        self.title = ""
        self.info = {}
        self.render_data = {}

    def parse_target_id(self):
        """解析目标ID和URL"""
        if self.target:
            target = self.target.strip()
            # 若整段粘贴（含标题+链接），先尝试从中提取抖音链接
            extracted = _extract_douyin_url(target)
            if extracted:
                target = extracted
            hostname = urlparse(target).hostname

            # 输入链接
            if hostname and hostname.endswith("douyin.com"):
                self._parse_url(target, hostname)
            # 输入非链接
            else:
                self._parse_non_url(target)
        else:
            # 未输入目标，直接采集本账号数据
            self.id = self._get_self_uid()
            self.url = DouyinURL.USER_SELF

    def _parse_url(self, target: str, hostname: str):
        """解析URL类型的目标"""
        if hostname == "v.douyin.com":
            target = url_redirect(target)

        path = unquote(urlparse(target).path.strip("/"))
        path_parts = path.split("/")

        # 确保路径至少有两个部分
        if len(path_parts) < 2:
            self.type = "aweme"
            self.id = path_parts[-1] if path_parts else ""
            self.url = target
        else:
            _type = path_parts[-2]
            self.id = path_parts[-1]
            self.url = target

            # 自动识别：单个作品、搜索、音乐、合集、话题
            if _type in ["video", "note"]:
                self.type = "aweme"
                self.url = f"{DouyinURL.AWEME}/{self.id}"
            elif _type in ["music", "hashtag"]:
                self.type = _type
            elif _type == "collection":
                self.type = "mix"
            elif _type == "search":
                self.id = unquote(self.id)
                search_type = parse_qs(urlparse(target).query).get("type")
                if search_type is None or search_type[0] in ["video", "general"]:
                    self.type = "search"
                else:
                    self.type = search_type[0]

    def _parse_non_url(self, target: str):
        """解析非URL类型的目标"""
        self.id = target

        if self.type in ["search"]:
            self.url = f"{DouyinURL.SEARCH}/{quote(self.id)}"
        elif self.type in ["aweme", "music", "hashtag", "mix"] and self.id.isdigit():
            if self.type == "aweme":
                self.url = f"{DouyinURL.AWEME}/{self.id}"
            elif self.type == "mix":
                self.url = f"{DouyinURL.MIX}/{self.id}"
            else:
                self.url = f"{DouyinURL.BASE}/{self.type}/{self.id}"
        elif self.type in [
            "post",
            "favorite",
            "collection",
            "following",
            "follower",
        ] and self.id.startswith(USER_ID_PREFIX):
            self.url = f"{DouyinURL.USER}/{self.id}"
        else:
            quit(f"[{self.id}]目标输入错误，请检查参数")

    def _get_self_uid(self) -> str:
        """获取当前登录用户的UID"""
        url = DouyinURL.USER_SELF
        text = self.request.getHTML(url)
        if text == "":
            quit(f"获取UID请求失败, url: {url}")

        pattern = r'secUid\\":\\"([-\w]+)\\"'
        match = re.search(pattern, text)
        if match:
            return match.group(1)
        else:
            quit(f"获取UID请求失败, url: {url}")

    def fetch_target_info(self) -> tuple[str, str]:
        """
        获取目标信息

        Returns:
            tuple: (title, aria2_conf_path)
        """
        # 目标信息（单条视频也走 HTML，避免 API 返回空 body 导致失败）
        if self.type == "search":
            self.title = self.id
        elif self.type == "aweme":
            self._fetch_from_html(optional=True)
            if self.render_data:
                self.info = self.render_data.get("aweme", {}).get("detail", {})
            self.title = self.id
        else:
            self._fetch_from_html()

        # 构建下载路径
        down_path = os.path.join(
            self.down_path, sanitize_filename(f"{self.type}_{self.title}")
        )
        aria2_conf = f"{down_path}.txt"

        return self.title, down_path, aria2_conf, self.info, self.render_data

    def _fetch_from_html(self, optional: bool = False):
        """从HTML页面获取目标信息。optional=True 时失败不 quit，仅留空 render_data（供单条视频回退 API）。"""
        text = self.request.getHTML(self.url)
        pattern = r'self\.__pace_f\.push\(\[1,"\d:\[\S+?({[\s\S]*?)\]\\n"\]\)</script>'
        render_data_list = re.findall(pattern, text)

        if not render_data_list:
            if optional:
                return
            quit(f"提取目标信息失败，可能是cookie无效。url: {self.url}")

        render_data = render_data_list[-1].replace('\\"', '"').replace("\\\\", "\\")
        self.render_data = json.loads(render_data)

        # 根据类型提取信息
        if self.type == "mix":
            self.info = self.render_data["aweme"]["detail"]["mixInfo"]
            self.title = self.info["mixName"]
        elif self.type == "music":
            self.info = self.render_data["musicDetail"]
            self.title = self.info["title"]
        elif self.type == "hashtag":
            self.info = self.render_data["topicDetail"]
            self.title = self.info["chaName"]
        elif self.type == "aweme":
            self.info = self.render_data["aweme"]["detail"]
            self.title = self.id
        elif self.type in ["post", "favorite", "collection", "following", "follower"]:
            self.info = self.render_data["user"]["user"]
            self.title = self.info["nickname"]
        else:
            quit(f"获取目标信息请求失败, type: {self.type}")
