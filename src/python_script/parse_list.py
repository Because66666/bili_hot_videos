import json
import os
import re
from datetime import datetime

# 文件路径
RESPONSE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'response')
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'content', 'posts')

# 读取txt文件
def read_data_dict(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    # 将字符串转换为Python对象
    data = eval(content)
    return data

# 获取所有整数命名的txt文件
def get_integer_txt_files():
    files = []
    for file_name in os.listdir(RESPONSE_DIR):
        if file_name.endswith('.txt') and file_name[:-4].isdigit():
            file_path = os.path.join(RESPONSE_DIR, file_name)
            files.append((int(file_name[:-4]), file_path))
    
    # 按照数字顺序排序
    files.sort(key=lambda x: x[0])
    return files

# 将时间戳转换为日期字符串
def timestamp_to_date(timestamp):
    # 将时间戳转换为datetime对象
    dt = datetime.fromtimestamp(timestamp)
    # 格式化为YYYY-MM-DD格式
    return dt.strftime('%Y-%m-%d')

# 生成每个视频的Markdown内容
def generate_video_md(video_data):
    title = video_data['title']
    author_name = video_data['owner']['name']
    author_mid = video_data['owner']['mid']
    bvid = video_data['bvid']
    desc = video_data.get('rcmd_reason', '').strip() or video_data.get('dynamic', '').strip() or video_data.get('desc', '').strip()
    
    # 生成Markdown格式
    md_content = f"# {title}\n"
    if desc:
        md_content += f"> {desc}\n\n"
    md_content += f"作者：[{author_name}](https://space.bilibili.com/{author_mid})\n"
    md_content += f"链接：https://www.bilibili.com/video/{bvid}\n\n"
    
    return md_content

# 生成完整的Markdown文件
def generate_full_md(videos_data, max_videos=10):
    # 获取第一个视频的发布时间作为文件名和发布日期
    if not videos_data:
        return None, None
    
    # 获取config信息
    config = videos_data.get('config', {})
    
    # 从name中提取日期，格式为：'2025第315期 03.28 - 04.03'
    # 跨年情形：2019第41期 12.27 - 01.02
    # 提取04.03作为发布日期（结束日期）
    published_date = ""
    if 'name' in config:
        name_parts = config['name'].split()
        year_add = False
        first = float(name_parts[-3])
        second = float(name_parts[-1])
        if first > second:
            year_add = True
        print(f"name_parts: {name_parts}")  # 打印name_parts，用于调试
        if len(name_parts) >= 2:
            date_parts = name_parts[-1].split()
            if len(date_parts) >= 2:
                # 将04.03格式转换为2025-04-03格式（使用结束日期）
                month_day = date_parts[-1].strip()
                if '.' in month_day:
                    month, day = month_day.split('.')
                    # 使用正则表达式提取年份，移除"第xxx期"格式的文本
                    year = re.sub(r'第\d+期', '', name_parts[0]).strip()
                    if year_add:
                        year = str(int(year) + 1)
                    published_date = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
            elif len(date_parts) >= 1:
                # 如果只有一个日期部分，使用它
                month_day = date_parts[0].strip()
                if '.' in month_day:
                    month, day = month_day.split('.')
                    # 使用正则表达式提取年份，移除"第xxx期"格式的文本
                    year = re.sub(r'第\d+期', '', name_parts[0]).strip()
                    if year_add:
                        year = str(int(year) + 1)
                    published_date = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
    
    # 如果无法从name中提取日期，则使用第一个视频的发布时间
    if not published_date and 'list' in videos_data and videos_data['list']:
        first_video = videos_data['list'][0]
        pubdate_timestamp = first_video['pubdate']
        published_date = timestamp_to_date(pubdate_timestamp)
    
    # 创建文件名
    file_name = f"{published_date}.md"
    
    # 打印提取的日期，用于调试
    print(f"提取的发布日期: {published_date}")
    
    # 创建Markdown头部信息
    header = f"---\n"
    header += f"title: {config.get('share_title', '每周必看')}\n"
    header += f"description: {config.get('share_subtitle', '精选B站热门视频，每周更新').replace('@','\@')}\n"
    header += f"published: {published_date}\n"
    header += f"tags: [视频, 每周精选]\n"
    header += f"category: 每周必看\n"
    header += f"draft: true\n"
    header += f"---\n\n"
    
    # 创建新的Markdown内容
    new_content = header
    
    # 添加每个视频的内容
    videos_list = videos_data.get('list', [])
    for i, video in enumerate(videos_list[:max_videos]):
        if i > 0:
            new_content += "---\n\n"  # 添加分隔线
        new_content += generate_video_md(video)
    
    return new_content, file_name

# 保存Markdown文件
def save_md_file(content, file_name):
    file_path = os.path.join(OUTPUT_DIR, file_name)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"已成功生成Markdown文件: {file_path}")

# 主函数
def main():
    # 获取所有整数命名的txt文件
    integer_files = get_integer_txt_files()
    
    if not integer_files:
        print("没有找到整数命名的txt文件")
        return
    
    # 依次处理每个文件
    for file_num, file_path in integer_files:
        print(f"正在处理文件: {file_path}")
        
        # 读取数据
        try:
            data_dict = read_data_dict(file_path)
            
            # 生成Markdown内容
            md_content, file_name = generate_full_md(data_dict)
            
            if md_content and file_name:
                # 保存文件
                save_md_file(md_content, file_name)
            else:
                print(f"无法为 {file_path} 生成Markdown文件：没有视频数据")
        except Exception as e:
            print(f"处理文件 {file_path} 时出错: {str(e)}")
            continue

if __name__ == "__main__":
    main()