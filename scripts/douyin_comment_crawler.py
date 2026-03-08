"""
抖音视频评论爬取工具 - 强化版

功能：
1. 自动爬取指定抖音视频的全部评论数据
2. 使用多种滚动策略和加载方式确保获取所有评论
3. 按日期和时间命名CSV文件，避免覆盖历史数据
4. 智能检测评论加载完成

依赖：pip install DrissionPage
（需本机已安装 Chrome/Edge，用于浏览器自动化）

日期: 2024年
"""

import csv
import datetime
import json
import os
import random
import re
import threading
import time

try:
    import msvcrt
except ImportError:
    msvcrt = None  # 非 Windows 无 msvcrt，键盘中断不可用

from DrissionPage import ChromiumPage
from DrissionPage import ChromiumOptions


class DouyinCommentCrawler:
    """抖音评论爬虫类 - 强化版"""

    def __init__(
        self,
        video_url=None,
        video_id=None,
        max_pages=None,
        use_normal_mode=True,
        login_first=False,
    ):
        """
        初始化爬虫
        :param video_url: 视频URL，例如 https://www.douyin.com/video/7353500880198536457
        :param video_id: 视频ID，如果提供了video_url则可不提供
        :param max_pages: 最大爬取页数，默认为None表示爬取全部评论
        :param use_normal_mode: 是否使用正常模式启动浏览器(不使用无痕模式)
        :param login_first: 启动后是否需要先让用户登录
        """
        self.video_url = video_url
        self.video_id = video_id if video_id else self._extract_video_id(video_url)
        self.max_pages = max_pages
        self.comments = []
        self.comment_ids = set()
        self.driver = None
        self.processed_comments = 0
        self.use_normal_mode = use_normal_mode
        self.login_first = login_first

        self.comments_dir = "crawled_comments"
        if not os.path.exists(self.comments_dir):
            os.makedirs(self.comments_dir)

        current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_file = os.path.join(
            self.comments_dir, f"douyin_comments_{self.video_id}_{current_time}.csv"
        )

    def _extract_video_id(self, url):
        """从URL中提取视频ID"""
        if not url:
            raise ValueError("需要提供视频URL或视频ID")

        url = url.replace("：", ":").strip()
        if not url.startswith("http"):
            url = "https://" + url.lstrip(":/")

        if "v.douyin.com" in url:
            parts = url.split("/")
            for part in reversed(parts):
                if part.strip():
                    return part.strip()

        try:
            parts = url.split("/")
            for part in parts:
                if part.strip().isdigit():
                    return part.strip()
            return parts[-1].split("?")[0]
        except Exception:
            print(f"警告: 无法从URL {url} 提取标准视频ID")
            return url.split("/")[-1].split("?")[0]

    def _scroll_to_comments(self):
        """滚动到评论区域"""
        try:
            self.driver.run_js("window.scrollTo(0, document.body.scrollHeight/2);")
            time.sleep(1)
            try:
                comment_area = self.driver.find_element(
                    xpath='//div[contains(@class, "comment-mainContent") or contains(@class, "comment-list")]'
                )
                if comment_area:
                    self.driver.run_js("arguments[0].scrollIntoView();", comment_area)
                    time.sleep(1)
            except Exception as e:
                print(f"找不到评论区域，使用备用滚动方法: {str(e)}")
                self.driver.run_js("window.scrollBy(0, 400);")
        except Exception as e:
            print(f"滚动到评论区时出错: {str(e)}")
            try:
                self.driver.run_js("window.scrollBy(0, 500);")
            except Exception:
                pass

    def _try_load_more_comments(self):
        """尝试不同方法加载更多评论"""
        try:
            more_reply_btns = self.driver.find_elements(
                xpath='//span[contains(text(), "查看") and contains(text(), "回复")]'
            )
            if more_reply_btns:
                for btn in more_reply_btns[:5]:
                    try:
                        self.driver.run_js("arguments[0].scrollIntoView();", btn)
                        time.sleep(0.5)
                        try:
                            self.driver.run_js("arguments[0].click();", btn)
                        except Exception:
                            btn.click()
                        time.sleep(1)
                        return True
                    except Exception as e:
                        print(f"点击'查看回复'按钮失败: {str(e)}")
                        continue
        except Exception as e:
            print(f"查找'查看回复'按钮失败: {str(e)}")

        try:
            expand_btns = self.driver.find_elements(
                xpath='//span[contains(text(), "展开") or contains(text(), "更多")]'
            )
            if expand_btns:
                for btn in expand_btns[:3]:
                    try:
                        self.driver.run_js("arguments[0].scrollIntoView();", btn)
                        time.sleep(0.5)
                        try:
                            self.driver.run_js("arguments[0].click();", btn)
                        except Exception:
                            btn.click()
                        time.sleep(1)
                        return True
                    except Exception as e:
                        print(f"点击'展开'按钮失败: {str(e)}")
                        continue
        except Exception as e:
            print(f"查找'展开'按钮失败: {str(e)}")

        return False

    def _perform_scroll(self, method):
        """执行不同的滚动方法"""
        print(f"使用滚动策略 {method}")
        try:
            if method == 1:
                self.driver.run_js("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(0.5)
            elif method == 2:
                self.driver.run_js("window.scrollBy(0, 300);")
                time.sleep(0.5)
                self.driver.run_js("window.scrollTo(0, document.body.scrollHeight);")
            elif method == 3:
                self.driver.run_js("window.scrollBy(0, -200);")
                time.sleep(0.5)
                self.driver.run_js("window.scrollTo(0, document.body.scrollHeight);")
            elif method == 4:
                self.driver.run_js("window.scrollTo(0, document.body.scrollHeight/2);")
                time.sleep(0.5)
                self.driver.run_js("window.scrollTo(0, document.body.scrollHeight);")
            elif method == 5:
                self.driver.run_js("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(0.5)
                for _ in range(3):
                    self.driver.run_js("window.scrollBy(0, -100);")
                    time.sleep(0.3)
            elif method == 6:
                for i in range(5):
                    self.driver.run_js("window.scrollBy(0, 300);")
                    time.sleep(0.4)
            elif method == 7:
                for i in range(3):
                    self.driver.run_js("window.scrollBy(0, 300);")
                    time.sleep(0.3)
                    self.driver.run_js("window.scrollBy(0, -50);")
                    time.sleep(0.3)
                self.driver.run_js("window.scrollTo(0, document.body.scrollHeight);")
            elif method == 8:
                try:
                    load_more_btns = self.driver.find_elements(
                        xpath='//div[contains(text(), "加载") or contains(text(), "更多") or contains(text(), "展开")]'
                    )
                    if load_more_btns:
                        for btn in load_more_btns[:3]:
                            try:
                                try:
                                    self.driver.run_js("arguments[0].scrollIntoView();", btn)
                                except Exception:
                                    pass
                                time.sleep(0.5)
                                try:
                                    self.driver.run_js("arguments[0].click();", btn)
                                except Exception:
                                    btn.click()
                                print("找到并点击了'加载更多'按钮")
                                time.sleep(1.5)
                                return
                            except Exception:
                                pass
                except Exception as e:
                    print(f"寻找加载更多按钮时出错: {str(e)}")
                self.driver.run_js("window.scrollTo(0, document.body.scrollHeight);")
            elif method == 9:
                try:
                    comments = self.driver.find_elements(
                        xpath='//div[contains(@class, "comment-item") or contains(@class, "CommentItem")]'
                    )
                    if comments and len(comments) > 2:
                        target = comments[-2]
                        self.driver.run_js("arguments[0].scrollIntoView();", target)
                        time.sleep(0.5)
                        self.driver.run_js("window.scrollBy(0, 200);")
                        return
                except Exception as e:
                    print(f"基于评论元素滚动时出错: {str(e)}")
                self.driver.run_js("window.scrollTo(0, document.body.scrollHeight);")
            elif method == 10:
                self.driver.run_js("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(0.8)
                self.driver.run_js("window.scrollTo(0, document.body.scrollHeight - 100);")
                time.sleep(0.3)
                self.driver.run_js("window.scrollTo(0, document.body.scrollHeight);")
            else:
                self.driver.run_js("window.scrollTo(0, document.body.scrollHeight);")
        except Exception as e:
            print(f"执行滚动策略 {method} 时出错: {str(e)}")
            try:
                self.driver.run_js("window.scrollBy(0, 300);")
            except Exception:
                pass

    def start_crawler(self):
        """启动爬虫"""
        print(f"\n开始爬取视频 {self.video_id} 的评论...")

        f = open(self.output_file, mode="w", encoding="utf-8-sig", newline="")
        fieldnames = [
            "评论ID",
            "昵称",
            "用户ID",
            "用户sec_id",
            "头像",
            "地区",
            "时间",
            "评论",
            "点赞数",
            "回复数",
            "回复给用户",
            "回复给用户ID",
            "是否置顶",
            "是否热评",
            "包含话题",
            "提及用户",
        ]
        csv_writer = csv.DictWriter(f, fieldnames=fieldnames)
        csv_writer.writeheader()

        try:
            print("正在初始化浏览器...")
            try:
                if self.use_normal_mode:
                    self.driver = ChromiumPage()
                    print("已启用正常浏览模式，您可以登录账号查看评论")
                else:
                    try:
                        self.driver = ChromiumPage(
                            chromium_options={"headless": False, "incognito": True}
                        )
                    except Exception:
                        print("无法使用无痕模式，回退到默认模式")
                        self.driver = ChromiumPage()
                    print("使用无痕模式")
            except Exception as e:
                print(f"初始化浏览器失败，尝试使用备用方法: {e}")
                self.driver = ChromiumPage()
                print("使用默认浏览器模式")

            if self.login_first:
                print("\n请在打开的浏览器中登录抖音账号...")
                print("登录后程序将自动继续 (或按Enter键跳过等待)")
                self.driver.get("https://www.douyin.com/")

                wait_complete = False

                def wait_for_keypress():
                    nonlocal wait_complete
                    if msvcrt is None:
                        return
                    while not wait_complete:
                        if msvcrt.kbhit():
                            key = msvcrt.getch()
                            if key == b"\r":
                                print("\n用户跳过等待，继续执行...")
                                wait_complete = True
                                return
                        time.sleep(0.1)

                input_thread = threading.Thread(target=wait_for_keypress)
                input_thread.daemon = True
                input_thread.start()

                start_time = time.time()
                while not wait_complete and time.time() - start_time < 120:
                    elapsed = int(time.time() - start_time)
                    if elapsed > 0 and elapsed % 10 == 0:
                        remain = 120 - elapsed
                        print(f"请登录抖音账号，还剩 {remain} 秒... (按Enter跳过)")
                    try:
                        if self.driver.element_exists(
                            'xpath://div[contains(@class, "avatar")]'
                        ):
                            print("检测到已登录，继续执行...")
                            wait_complete = True
                            break
                    except Exception:
                        pass
                    time.sleep(1)

            self.driver.listen.start("aweme/v1/web/comment/list/")

            print("正在访问视频页面...")
            try:
                if self.video_url:
                    url = self.video_url.replace("：", ":").strip()
                    if not url.startswith("http"):
                        url = "https://" + url.lstrip(":/")
                    print(f"使用URL访问: {url}")
                    self.driver.get(url)
                else:
                    standard_url = f"https://www.douyin.com/video/{self.video_id}"
                    print(f"使用标准URL访问: {standard_url}")
                    self.driver.get(standard_url)

                time.sleep(5)
                if "页面不存在" in self.driver.page_source or "404" in self.driver.title:
                    print(f"警告: 页面加载异常: {self.video_id}")
                    if "v.douyin.com" in (self.video_url or ""):
                        print("检测到短链接，尝试直接访问...")
                        self.driver.get(self.video_url)
            except Exception as e:
                print(f"访问视频页面时出错: {str(e)}")

            time.sleep(5)

            try:
                more_comment_btn = self.driver.find_element(
                    xpath='//div[contains(text(), "查看更多评论")]'
                )
                if more_comment_btn:
                    print("点击'查看更多评论'按钮...")
                    more_comment_btn.click()
                    time.sleep(2)
            except Exception:
                print("没有找到'查看更多评论'按钮，继续使用滚动加载评论")

            self._scroll_to_comments()

            page = 0
            no_new_comments_count = 0
            max_no_new_attempts = 10
            total_attempts = 0
            is_crawling = True

            def monitor_for_interrupt():
                nonlocal is_crawling
                if msvcrt is None:
                    return
                print("\n爬取过程中，随时可以按Enter键停止爬取并保存已获取的评论")
                while is_crawling:
                    try:
                        if msvcrt.kbhit():
                            key = msvcrt.getch()
                            if key == b"\r":
                                print("\n用户中断爬取，即将保存当前评论...")
                                is_crawling = False
                                return
                    except Exception:
                        pass
                    time.sleep(0.1)

            interrupt_thread = threading.Thread(target=monitor_for_interrupt)
            interrupt_thread.daemon = True
            interrupt_thread.start()

            while (self.max_pages is None or page < self.max_pages) and is_crawling:
                try:
                    page += 1
                    print(f"正在爬取第 {page} 页评论...")

                    scroll_method = (page % 10) + 1
                    self._perform_scroll(scroll_method)
                    wait_time = 1 + random.random() * 2
                    time.sleep(wait_time)

                    resp = self.driver.listen.wait(timeout=5)

                    if not resp:
                        total_attempts += 1
                        print(f"未检测到新的评论数据，尝试使用其他方法... (尝试 {total_attempts})")
                        if self._try_load_more_comments():
                            continue
                        no_new_comments_count += 1
                        if no_new_comments_count >= max_no_new_attempts:
                            print(f"已连续 {max_no_new_attempts} 次未获取到新评论，可能已到达末页")
                            if no_new_comments_count == max_no_new_attempts:
                                print("尝试刷新页面后继续...")
                                self.driver.refresh()
                                time.sleep(5)
                                self._scroll_to_comments()
                                no_new_comments_count -= 1
                                continue
                            print("确认已加载全部评论，结束爬取")
                            break
                        continue

                    total_attempts = 0
                    json_data = resp.response.body

                    if not json_data or "comments" not in json_data:
                        no_new_comments_count += 1
                        print(
                            f"未获取到有效评论数据，尝试继续... (尝试 {no_new_comments_count}/{max_no_new_attempts})"
                        )
                        if no_new_comments_count >= max_no_new_attempts:
                            print("多次未获取到有效评论数据，可能已到达末页")
                            break
                        continue

                    comments = json_data["comments"]
                    if not comments:
                        no_new_comments_count += 1
                        print(
                            f"本页无评论数据，尝试继续... (尝试 {no_new_comments_count}/{max_no_new_attempts})"
                        )
                        if no_new_comments_count >= max_no_new_attempts:
                            print("多次获取到空评论列表，可能已到达末页")
                            break
                        continue

                    comment_id_count_before = len(self.comment_ids)

                    for comment in comments:
                        try:
                            comment_id = comment.get("cid", "") or str(
                                comment.get("id", "")
                            )
                            if comment_id in self.comment_ids:
                                continue
                            self.comment_ids.add(comment_id)
                            comment_data = self._parse_comment_details(comment)
                            self.comments.append(comment_data)
                            csv_writer.writerow(comment_data)
                            self.processed_comments += 1
                            if self.processed_comments % 10 == 0:
                                print(f"已爬取 {self.processed_comments} 条评论")
                            elif self.processed_comments % 5 == 0:
                                print(
                                    f"[{self.processed_comments}] {comment_data['昵称']}: {comment_data['评论'][:20]}..."
                                )
                        except Exception as e:
                            print(f"处理评论时出错: {str(e)}")

                    comment_id_added = len(self.comment_ids) - comment_id_count_before
                    if comment_id_added > 0:
                        print(
                            f"本次获取了 {comment_id_added} 条新评论，累计 {len(self.comments)} 条"
                        )
                        no_new_comments_count = 0
                    else:
                        no_new_comments_count += 1
                        print(
                            f"未获取到新评论，尝试继续... (尝试 {no_new_comments_count}/{max_no_new_attempts})"
                        )
                        if self._try_load_more_comments():
                            no_new_comments_count -= 1
                        if no_new_comments_count >= max_no_new_attempts:
                            print("多次未获取到新评论，可能已到达末页")
                            break

                except Exception as e:
                    print(f"爬取第 {page} 页时出错: {str(e)}")
                    no_new_comments_count += 1
                    if no_new_comments_count >= 3:
                        print("连续多次爬取出错，停止爬取")
                        break

            print(f"\n评论爬取完成！共获取 {len(self.comments)} 条评论")

            try:
                print("\n是否尝试提取评论回复？这可能需要额外的时间 (y/n):")
                extract_replies = input().strip().lower() == "y"
                if extract_replies and self.comments:
                    print("已保存主评论，开始提取回复评论...")
                    replies = self._try_extract_all_replies()
                    if replies:
                        print(f"\n成功提取 {len(replies)} 条回复评论！")
                        replies_file = self.output_file.replace(".csv", "_replies.csv")
                        with open(
                            replies_file, mode="w", encoding="utf-8-sig", newline=""
                        ) as rf:
                            reply_writer = csv.DictWriter(rf, fieldnames=fieldnames)
                            reply_writer.writeheader()
                            for reply in replies:
                                try:
                                    for field in fieldnames:
                                        if field not in reply:
                                            reply[field] = ""
                                    reply_writer.writerow(reply)
                                except Exception as e:
                                    print(f"写入回复时出错: {str(e)}")
                        print(f"回复评论已保存到文件: {replies_file}")
                        self.comments.extend(replies)
            except Exception as e:
                print(f"提取回复评论过程中出错: {str(e)}")

            print(f"\n全部评论爬取完成！共获取 {len(self.comments)} 条评论(含回复)")
            print(f"评论已保存到文件: {self.output_file}")
            return self.comments

        except Exception as e:
            print(f"爬虫运行出错: {str(e)}")
            return []

        finally:
            if "is_crawling" in locals():
                is_crawling = False
            f.close()
            if self.driver:
                self.driver.quit()

    def get_output_file(self):
        """获取输出文件路径"""
        return self.output_file

    def _parse_comment_details(self, comment):
        """解析评论详细信息"""
        try:
            comment_id = comment.get("cid", "") or str(comment.get("id", ""))
            text = comment.get("text", "").strip()
            create_time = comment.get("create_time", 0)
            date = str(datetime.datetime.fromtimestamp(create_time))
            digg_count = comment.get("digg_count", 0)

            user = comment.get("user", {})
            nickname = user.get("nickname", "未知用户")
            user_id = user.get("uid", "")
            sec_uid = user.get("sec_uid", "")
            avatar = user.get("avatar_thumb", {}).get("url_list", [""])[0]
            ip_label = comment.get("ip_label", "未知")
            reply_count = comment.get("reply_comment_total", 0)
            reply_to_userid = comment.get("reply_to_userid", "")
            reply_to_nickname = comment.get("reply_to_nickname", "")
            is_top = bool(comment.get("stick_position", 0))
            is_hot = bool(comment.get("is_hot_comment", 0))

            extra_info = {}
            if comment.get("text_extra"):
                extra_info["hashtags"] = [
                    item.get("hashtag_name")
                    for item in comment.get("text_extra", [])
                    if item.get("hashtag_name")
                ]
            at_users = []
            if comment.get("text_extra"):
                at_users = [
                    item.get("user_id")
                    for item in comment.get("text_extra", [])
                    if item.get("type") == 0
                ]

            comment_data = {
                "评论ID": comment_id,
                "昵称": nickname,
                "用户ID": user_id,
                "用户sec_id": sec_uid,
                "头像": avatar,
                "地区": ip_label,
                "时间": date,
                "评论": text,
                "点赞数": digg_count,
                "回复数": reply_count,
                "回复给用户": reply_to_nickname,
                "回复给用户ID": reply_to_userid,
                "是否置顶": "是" if is_top else "否",
                "是否热评": "是" if is_hot else "否",
                "包含话题": ",".join(extra_info.get("hashtags", [])),
                "提及用户": ",".join(at_users),
            }
            return comment_data
        except Exception as e:
            print(f"解析评论详情时出错: {str(e)}")
            return {
                "评论ID": comment.get("cid", "") or str(comment.get("id", "")),
                "昵称": comment.get("user", {}).get("nickname", "未知"),
                "地区": comment.get("ip_label", "未知"),
                "时间": str(
                    datetime.datetime.fromtimestamp(comment.get("create_time", 0))
                ),
                "评论": comment.get("text", ""),
                "点赞数": comment.get("digg_count", 0),
            }

    def _extract_reply_comments(self, comment_id):
        """尝试提取某条评论的回复评论"""
        try:
            comment_elem = self.driver.find_element(
                f'xpath://div[@data-comment-id="{comment_id}" or @id="{comment_id}"]'
            )
            if not comment_elem:
                return []
            self.driver.scroll.to_element(comment_elem)
            time.sleep(0.5)
            try:
                more_reply_btn = comment_elem.find_element(
                    'xpath:.//span[contains(text(), "查看") and contains(text(), "回复")]'
                )
                if more_reply_btn:
                    more_reply_btn.click()
                    time.sleep(1.5)
            except Exception:
                pass
            reply_elements = comment_elem.find_elements(
                xpath='.//div[contains(@class, "reply-item") or contains(@class, "ReplyItem")]'
            )
            replies = []
            for reply_elem in reply_elements:
                try:
                    reply_text = reply_elem.text
                    replier = reply_elem.find_element(
                        'xpath:.//span[contains(@class, "nickname") or contains(@class, "user-name")]'
                    ).text
                    reply_id = (
                        reply_elem.get_attribute("data-id")
                        or reply_elem.get_attribute("id")
                        or f"{comment_id}_reply_{len(replies)}"
                    )
                    like_count_elem = reply_elem.find_element(
                        'xpath:.//span[contains(@class, "like") or contains(@class, "digg")]'
                    )
                    like_count = like_count_elem.text if like_count_elem else "0"
                    reply = {
                        "评论ID": reply_id,
                        "昵称": replier,
                        "评论": reply_text,
                        "点赞数": like_count,
                        "回复给用户ID": comment_id,
                        "是否回复评论": "是",
                    }
                    replies.append(reply)
                except Exception as e:
                    print(f"提取单条回复时出错: {str(e)}")
            return replies
        except Exception as e:
            print(f"提取评论 {comment_id} 的回复时出错: {str(e)}")
            return []

    def _try_extract_all_replies(self):
        """尝试提取所有主评论的回复"""
        all_replies = []
        top_comments = list(self.comment_ids)[:50]
        print(f"\n尝试提取 {len(top_comments)} 条主评论的回复...")
        for i, comment_id in enumerate(top_comments):
            if i % 5 == 0:
                print(f"正在提取第 {i+1}/{len(top_comments)} 条评论的回复...")
            replies = self._extract_reply_comments(comment_id)
            if replies:
                print(f"评论 {comment_id} 获取到 {len(replies)} 条回复")
                all_replies.extend(replies)
        return all_replies


def main():
    """主函数"""
    print("=" * 60)
    print("抖音视频评论爬取工具 - 强化版")
    print("=" * 60)

    video_url = input(
        "请输入抖音视频URL (例如: https://www.douyin.com/video/7353500880198536457): "
    )
    try:
        pages_input = input("请输入最大爬取页数 (直接回车表示爬取全部评论): ")
        max_pages = int(pages_input) if pages_input.strip() else None
    except ValueError:
        max_pages = None

    if max_pages is None:
        print("将爬取全部评论，直到没有更多评论为止")
    else:
        print(f"将爬取最多 {max_pages} 页评论")

    use_normal_mode = (
        input("是否使用正常浏览器模式 (可以登录账号) [Y/n]: ").lower() != "n"
    )
    login_first = False
    if use_normal_mode:
        login_first = (
            input("是否需要在爬取前先登录抖音账号 [y/N]: ").lower() == "y"
        )

    crawler = DouyinCommentCrawler(
        video_url=video_url,
        max_pages=max_pages,
        use_normal_mode=use_normal_mode,
        login_first=login_first,
    )
    comments = crawler.start_crawler()

    if comments:
        print(f"\n成功爬取 {len(comments)} 条评论")
        print(f"评论已保存到文件: {crawler.get_output_file()}")
    else:
        print("\n爬取失败或未获取到评论")


if __name__ == "__main__":
    main()
