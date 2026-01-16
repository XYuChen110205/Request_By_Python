import requests
import re
from lxml import etree
from datetime import datetime
import os
import json
import time


def extract_articles_from_12371(url):
    """
    专门针对12371.cn网站的JavaScript动态内容提取
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = 'utf-8'

        # 使用正则直接提取
        pattern = r"'link_add':'([^']+)','title':'([^']+)'"
        matches = re.findall(pattern, response.text)

        articles = []
        for link, title in matches:
            articles.append({
                'title': title,
                'url': link
            })

        # 去重
        unique_articles = []
        seen_titles = set()
        for article in articles:
            if article['title'] not in seen_titles:
                seen_titles.add(article['title'])
                unique_articles.append(article)

        return unique_articles
    except Exception as e:
        print(f"提取文章列表失败 {url}: {e}")
        return []


def get_article_content(article_url):
    """
    获取单篇文章的详细内容（优化版）
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    try:
        response = requests.get(article_url, headers=headers, timeout=10)
        response.encoding = 'utf-8'
        tree = etree.HTML(response.text)

        # 提取文章标题
        title = tree.xpath('//h1/text() | //title/text()')
        title = title[0].strip() if title else "无标题"

        # 更精确的内容提取（排除导航、页脚等）
        content_elements = tree.xpath('''
            //div[contains(@class, "content")]//text() |
            //div[contains(@class, "article")]//text() |
            //div[contains(@class, "text")]//text() |
            //p[not(ancestor::div[contains(@class, "nav")])]//text()
        ''')

        # 过滤掉无关内容
        filtered_content = []
        for text in content_elements:
            text = text.strip()
            if (text and
                    len(text) > 5 and  # 过滤过短的文本
                    '欢迎使用手机浏览' not in text and
                    '热搜' not in text and
                    '关于我们' not in text and
                    '联系我们' not in text and
                    '网站地图' not in text and
                    '用户调查' not in text and
                    '共产党员网' not in text and
                    '京ICP备' not in text):
                filtered_content.append(text)

        content = '\n'.join(filtered_content)

        if not content.strip():
            content = "未能获取到文章内容"

        return {
            'title': title,
            'content': content,
            'url': article_url
        }
    except Exception as e:
        return {
            'title': '获取失败',
            'content': f'获取文章内容时出错: {str(e)}',
            'url': article_url
        }


def save_chunked_files(data, base_filename, chunk_size=100, file_type="json"):
    """
    将数据分块保存
    """
    os.makedirs(os.path.dirname(base_filename), exist_ok=True)

    for i in range(0, len(data), chunk_size):
        chunk = data[i:i + chunk_size]
        chunk_num = i // chunk_size + 1
        start_num = i + 1
        end_num = i + len(chunk)

        if file_type == "json":
            filename = f"{base_filename}_{start_num}-{end_num}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(chunk, f, ensure_ascii=False, indent=2)
        else:  # txt格式
            filename = f"{base_filename}_{start_num}-{end_num}.txt"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"=== {os.path.basename(base_filename)} {start_num}-{end_num} ===\n")
                f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 60 + "\n\n")

                for j, item in enumerate(chunk, 1):
                    f.write(f"【第{j}条】{item['title']}\n")
                    f.write(f"链接: {item['url']}\n")
                    if 'content' in item:
                        f.write("-" * 40 + "\n")
                        f.write(f"{item['content']}\n")
                    f.write("\n" + "=" * 50 + "\n\n")

        print(f"已保存: {filename} (共{len(chunk)}条)")


def crawl_and_save_data():
    """
    主爬取和保存函数
    """
    print("开始爬取党务文章...")

    categories = {
        '党章': 'https://www.12371.cn/special/dnfg/',
        '条例': 'https://www.12371.cn/special/dnfg/tl/',
        '准则': 'https://www.12371.cn/special/dnfg/zz/',
        '规定': 'https://www.12371.cn/special/dnfg/gd/',
        '办法': 'https://www.12371.cn/special/dnfg/bf/',
        '规则': 'https://www.12371.cn/special/dnfg/gz/',
        '细则': 'https://www.12371.cn/special/dnfg/xz/',
        '规范性文件': 'https://www.12371.cn/special/zcwj/'
    }

    # 创建主文件夹
    os.makedirs("党务链接文件夹", exist_ok=True)
    os.makedirs("党务文章内容文件夹", exist_ok=True)

    # 收集所有文章数据
    all_articles_data = {}

    print("正在获取各分类文章链接...")
    for name, url in categories.items():
        print(f"正在处理 {name} 分类...")
        articles = extract_articles_from_12371(url)
        all_articles_data[name] = articles
        print(f"  {name}: 找到 {len(articles)} 篇文章")

        # 合理的延迟
        time.sleep(1)

    print("\n开始保存链接文件...")

    # 保存链接文件
    for category, articles in all_articles_data.items():
        if category == "规范性文件":
            # 规范性文件分块保存
            save_chunked_files(
                articles,
                f"党务链接文件夹/规范性文件链接",
                chunk_size=100,
                file_type="json"
            )
        else:
            # 其他分类单个文件保存
            filename = f"党务链接文件夹/{category}链接文件.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(articles, f, ensure_ascii=False, indent=2)
            print(f"已保存: {filename}")

    print("\n开始爬取和保存文章内容...")

    # 爬取和保存文章内容
    for category, articles in all_articles_data.items():
        print(f"\n正在处理 {category} 内容...")

        contents = []
        total_articles = len(articles)

        for i, article in enumerate(articles, 1):
            print(f"  爬取进度: {i}/{total_articles} - {article['title'][:30]}...")

            content_data = get_article_content(article['url'])
            contents.append(content_data)

            # 合理的爬取速度：每2篇文章暂停1秒
            if i % 2 == 0:
                time.sleep(1)

            # 每10篇显示一次进度
            if i % 10 == 0:
                print(f"   已完成 {i}/{total_articles}")

        # 保存内容文件
        if category == "规范性文件":
            # 规范性文件分块保存
            save_chunked_files(
                contents,
                f"党务文章内容文件夹/规范性文件正文",
                chunk_size=100,
                file_type="txt"
            )
        else:
            # 其他分类单个文件保存
            filename = f"党务文章内容文件夹/{category}内容文件.txt"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"=== {category}内容汇总 ===\n")
                f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 60 + "\n\n")

                for i, content in enumerate(contents, 1):
                    f.write(f"【第{i}篇】{content['title']}\n")
                    f.write(f"链接: {content['url']}\n")
                    f.write("-" * 40 + "\n")
                    f.write(f"{content['content']}\n")
                    f.write("\n" + "=" * 50 + "\n\n")

            print(f"已保存: {filename}")

    # 生成报告
    generate_final_report(all_articles_data)


def generate_final_report(articles_data):
    """
    生成最终报告
    """
    report_filename = "党务文章爬取报告.txt"

    with open(report_filename, 'w', encoding='utf-8') as f:
        f.write("=== 党务文章爬取完成报告 ===\n")
        f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 80 + "\n\n")

        total_articles = 0
        total_content_success = 0

        f.write("【分类统计】\n")
        f.write("-" * 50 + "\n")
        f.write(f"{'分类名称':<10} {'文章数量':<8} {'文件类型':<15}\n")
        f.write("-" * 50 + "\n")

        for category, articles in articles_data.items():
            article_count = len(articles)
            total_articles += article_count

            if category == "规范性文件":
                file_type = "分块文件"
                # 计算分块数量
                chunk_count = (article_count + 99) // 100
                file_info = f"{chunk_count}个分块文件"
            else:
                file_type = "单个文件"
                file_info = "1个文件"

            f.write(f"{category:<10} {article_count:<8} {file_type:<15} {file_info}\n")

        f.write(f"\n【总体统计】\n")
        f.write("-" * 50 + "\n")
        f.write(f"总文章数: {total_articles}\n")
        f.write(f"分类数量: {len(articles_data)}\n")

        f.write(f"\n【文件结构】\n")
        f.write("-" * 50 + "\n")
        f.write("党务链接文件夹/\n")
        for category in articles_data.keys():
            if category == "规范性文件":
                f.write("  ├── 规范性文件链接_1-100.json\n")
                f.write("  ├── 规范性文件链接_101-200.json\n")
                f.write("  └── ... (以此类推)\n")
            else:
                f.write(f"  ├── {category}链接文件.json\n")

        f.write("\n党务文章内容文件夹/\n")
        for category in articles_data.keys():
            if category == "规范性文件":
                f.write("  ├── 规范性文件正文_1-100.txt\n")
                f.write("  ├── 规范性文件正文_101-200.txt\n")
                f.write("  └── ... (以此类推)\n")
            else:
                f.write(f"  ├── {category}内容文件.txt\n")

        f.write(f"\n【说明】\n")
        f.write("-" * 50 + "\n")
        f.write("1. 规范性文件由于数量较多，已按每100条进行分块保存\n")
        f.write("2. 其他分类文件单独保存为一个文件\n")
        f.write("3. 爬取速度已优化，避免对服务器造成压力\n")
        f.write("4. 所有文件均采用UTF-8编码保存\n")

    print(f"\n已生成报告: {report_filename}")


def main():
    """
    主程序
    """
    print("开始执行党务文章爬取任务...")
    print("注意：爬取过程可能需要一些时间，请耐心等待")
    print("爬取速度已优化，避免对服务器造成压力\n")

    try:
        crawl_and_save_data()

        print("\n" + "=" * 60)
        print("✅ 爬取任务完成！")
        print("=" * 60)
        print("\n生成的文件结构：")
        print("党务链接文件夹/")
        print("  ├── 党章链接文件.json")
        print("  ├── 准则链接文件.json")
        print("  ├── 条例链接文件.json")
        print("  ├── 规定链接文件.json")
        print("  ├── 办法链接文件.json")
        print("  ├── 规则链接文件.json")
        print("  ├── 细则链接文件.json")
        print("  └── 规范性文件链接_1-100.json (等分块文件)")
        print("党务文章内容文件夹/")
        print("  ├── 党章内容文件.txt")
        print("  ├── 准则内容文件.txt")
        print("  ├── 条例内容文件.txt")
        print("  ├── 规定内容文件.txt")
        print("  ├── 办法内容文件.txt")
        print("  ├── 规则内容文件.txt")
        print("  ├── 细则内容文件.txt")
        print("  └── 规范性文件正文_1-100.txt (等分块文件)")
        print("\n党务文章爬取报告.txt")
        # print("\n可以安心睡觉了！😊")

    except Exception as e:
        print(f"爬取过程中出现错误: {e}")
        print("建议检查网络连接后重试")


if __name__ == "__main__":
    main()