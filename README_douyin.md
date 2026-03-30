# 抖音热榜爬取工具

独立的抖音热榜爬取工具，可以单独运行，不依赖主项目。

## 功能特点

- 爬取抖音热榜前30条数据
- 自动保存为文本文件和HTML报告
- 支持重试机制，提高爬取成功率
- HTML报告支持保存为图片功能
- 独立运行，无需依赖主项目

## 使用方法

### 基本使用

直接运行脚本：

```bash
python douyin_fetcher.py
```

### 输出文件

脚本会在 `output` 目录下生成以下文件：

1. **文本文件**：`output/2026年03月26日/txt/20时52分_douyin.txt`
   - 包含抖音热榜的文本格式数据
   - 包含标题、排名和链接

2. **HTML报告**：`output/2026年03月26日/html/抖音热点榜.html`
   - 精美的HTML格式报告
   - 支持响应式设计
   - 可以保存为图片

### 输出示例

```
抖音热榜爬取工具
==================================================
正在获取抖音热榜...
获取抖音热榜成功（最新数据）
成功获取 30 条抖音热榜
正在保存到文本文件...
抖音热榜已保存到: output\2026年03月26日\txt\20时52分_douyin.txt
正在生成HTML报告...
抖音热榜HTML已生成: output\2026年03月26日\html\抖音热点榜.html

==================================================
抖音热榜爬取完成！
文本文件: output\2026年03月26日\txt\20时52分_douyin.txt
HTML报告: output\2026年03月26日\html\抖音热点榜.html
```

## 代码结构

### DouyinHotFetcher 类

主要的爬取类，包含以下方法：

- `__init__(proxy_url=None)`: 初始化爬取器，可选代理URL
- `fetch_douyin_hot(max_retries=2)`: 获取抖音热榜数据
- `_parse_douyin_data(data_json)`: 解析API返回的数据
- `save_to_txt(douyin_data, output_dir="output")`: 保存为文本文件
- `generate_html_report(douyin_data, output_dir="output")`: 生成HTML报告

### 数据格式

抖音热榜数据格式：

```python
{
    "标题": {
        "ranks": [排名],
        "url": "PC端链接",
        "mobileUrl": "移动端链接",
        "hotValue": "热度值"
    }
}
```

## 依赖项

- Python 3.6+
- requests
- pathlib (Python标准库)

## 安装依赖

```bash
pip install requests
```

## 注意事项

1. 脚本使用第三方API获取抖音热榜数据
2. 数据来源：`https://newsnow.busiyi.world/api/s?id=douyin&latest`
3. 默认请求间隔为3-5秒，避免频繁请求
4. 支持重试机制，默认最多重试2次
5. 如果需要使用代理，可以在初始化时传入 `proxy_url` 参数

## 自定义配置

### 使用代理

```python
fetcher = DouyinHotFetcher(proxy_url="http://your-proxy:port")
douyin_data = fetcher.fetch_douyin_hot()
```

### 修改输出目录

```python
fetcher = DouyinHotFetcher()
douyin_data = fetcher.fetch_douyin_hot()
txt_file = fetcher.save_to_txt(douyin_data, output_dir="custom_output")
html_file = fetcher.generate_html_report(douyin_data, output_dir="custom_output")
```

### 修改重试次数

```python
douyin_data = fetcher.fetch_douyin_hot(max_retries=5)
```

## 集成到其他项目

可以轻松集成到其他项目中：

```python
from douyin_fetcher import DouyinHotFetcher

fetcher = DouyinHotFetcher()
douyin_data = fetcher.fetch_douyin_hot()

if douyin_data:
    # 处理抖音热榜数据
    for title, data in douyin_data.items():
        print(f"{title}: {data['url']}")
```

## 许可证

本工具基于 TrendRadar 项目开发，遵循相同的许可证。

## 相关项目

- [TrendRadar](https://github.com/yourusername/TrendRadar) - 多平台热点聚合工具