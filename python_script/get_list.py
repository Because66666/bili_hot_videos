import os
import json
import time
import ast
import asyncio
from playwright.async_api import async_playwright
# 设置响应文件保存路径
RESPONSE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'response')

# 设置是否无头浏览器
HEADLESS = False
# 确保响应目录存在
os.makedirs(RESPONSE_DIR, exist_ok=True)



async def get_series_list():
    user_responses = dict()
    response_received = asyncio.Event()
    # 获取数据
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=HEADLESS)
        context = await browser.new_context()

        # 监听所有响应事件
        async def handle_response(response):
            nonlocal user_responses
            # 获取响应所属页面的 URL
            page_url = response.request.url if response.request else ""
            # 检查当前页面的用户 ID
            if f"api.bilibili.com/x/web-interface/popular/series/list" in page_url:
                user_responses = await response.json()
                response_received.set()

        context.on("response", handle_response)

        page = await context.new_page()
        await page.goto(f"https://www.bilibili.com/v/popular/weekly?num=316")
        await page.wait_for_load_state("networkidle")
        await response_received.wait()
        await page.close()
        response_received.clear()
        await browser.close()

    """获取B站每周必看系列列表"""
    return user_responses

async def get_series_detail(number):
    """获取指定期号的详细信息"""

    user_responses = dict()
    response_received = asyncio.Event()
    # 获取数据
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=HEADLESS)
        context = await browser.new_context()

        # 监听所有响应事件
        async def handle_response(response):
            nonlocal user_responses
            # 获取响应所属页面的 URL
            page_url = response.request.url if response.request else ""
            # 检查当前页面的用户 ID
            if f"api.bilibili.com/x/web-interface/popular/series/one" in page_url:
                user_responses = await response.json()
                response_received.set()

        context.on("response", handle_response)

        page = await context.new_page()
        await page.goto(f"https://www.bilibili.com/v/popular/weekly?num={number}")
        await page.wait_for_load_state("networkidle")
        await response_received.wait()
        await page.close()
        response_received.clear()
        await browser.close()
    
    return user_responses

def save_data(data, filename):
    """保存数据到文件"""
    file_path = os.path.join(RESPONSE_DIR, filename)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(str(data))
    print(f"数据已保存到: {file_path}")
    
def load_data(filename):
    """从文件加载数据"""
    file_path = os.path.join(RESPONSE_DIR, filename)
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            try:
                # 使用ast.literal_eval安全地解析字符串为Python对象
                return ast.literal_eval(content)
            except (SyntaxError, ValueError) as e:
                print(f"解析文件 {filename} 时出错: {e}")
    return None

def main():
    # 尝试从现有文件加载数据
    data_dict = load_data('data_dict.txt')
    data_detail = load_data('data_detail.txt')
    
    # 获取新数据
    print("从API获取系列列表...")
    data0 = asyncio.run(get_series_list())
    if data0.get('code') == 0 and 'data' in data0:
        save_data(data0, 'data_dict.txt')
        data_dict = data0
    else:
        print(f"获取列表失败: {data0.get('message')}")
        return
    
    # 提取列表数据
    if data_dict and data_dict.get('code') == 0 and 'data' in data_dict and 'list' in data_dict['data']:
        # 获取所有期号的详细数据
        print("开始获取所有期号的详细数据...")
        
        # 遍历data_dict中的所有期号
        for series_item in data_dict['data']['list']:
            number = None
            
            # 尝试从config字段获取期号
            if 'config' in series_item:
                number = series_item['config'].get('number')
            
            # 如果config中没有期号，尝试从其他字段获取
            if not number:
                for field in ['number', 'id']:
                    if field in series_item:
                        number = series_item[field]
                        break
            
            if number:
                # 检查是否已存在对应文件
                detail_file = f"{number}.txt"
                detail_path = os.path.join(RESPONSE_DIR, detail_file)
                
                if not os.path.exists(detail_path):
                    print(f"获取第 {number} 期详细数据...")
                    try:
                        time.sleep(7)  # 延迟1秒以避免请求过于频繁
                        data2 = asyncio.run(get_series_detail(number))
                        
                        if data2.get('code') == 0 and 'data' in data2:
                            # 保存详细数据
                            save_data(data2['data'], detail_file)
                        else:
                            print(f"获取详细数据失败: {data2.get('message')}")
                            time.sleep(600)  # 延迟10秒以避免请求过于频繁
                            # 如果有现有的data_detail数据且期号匹配，尝试保存它
                            if (data_detail and 'data' in data_detail and 'config' in data_detail['data'] and 
                                data_detail['data']['config'].get('number') == number):
                                save_data(data_detail['data'], detail_file)
                                print(f"已保存现有的详细数据到 {detail_file}")
                    except Exception as e:
                        print(f"请求详细数据时出错: {e}")
                        # 如果有现有的data_detail数据且期号匹配，尝试保存它
                        if (data_detail and 'data' in data_detail and 'config' in data_detail['data'] and 
                            data_detail['data']['config'].get('number') == number):
                            save_data(data_detail['data'], detail_file)
                            print(f"已保存现有的详细数据到 {detail_file}")
                else:
                    print(f"文件 {detail_file} 已存在，跳过获取")
            else:
                print(f"无法获取期号，跳过当前项目: {series_item}")
        
        print("所有期号的详细数据获取完成")
    else:
        print("无法从数据中提取列表信息")

if __name__ == "__main__":
    main()