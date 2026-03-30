@echo off
chcp 65001 >nul
echo ============================================================
echo 抖音热榜评论定时爬取器
echo ============================================================
echo.
echo 功能：每 2 小时自动爬取热榜视频评论
echo 输出：downloads/hot_comments/
echo 日志：logs/hot_comment_YYYY-MM-DD.log
echo.
echo 按 Ctrl+C 停止
echo ============================================================
echo.

cd /d "%~dp0"

python scheduler_hot_comment.py --interval 2 --video-count 10 --comments-per-video 100

pause
