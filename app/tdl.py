import os
import json
import subprocess
import configparser
import logging

# 配置日志：写入 tdl_execution.log 文件，编码为 utf-8
# 格式：时间 - 日志级别 - 具体信息
logging.basicConfig(
    filename='tdl_execution.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    encoding='utf-8'
)


def load_config(config_file):
    """读取 py.properties 配置文件"""
    config = configparser.ConfigParser()
    # 兼容没有 section 的 properties 文件格式
    with open(config_file, encoding='utf-8') as f:
        config.read_string('[default]\n' + f.read())
    return config['default']


def get_existing_files(target_dir):
    """获取目标目录下所有已存在的文件名集合"""
    if not os.path.exists(target_dir):
        return set()
    return {f for f in os.listdir(target_dir) if os.path.isfile(os.path.join(target_dir, f))}


def process_channel(channel_id, source_path, target_path):
    """处理单个频道的下载逻辑"""
    channel_source_dir = os.path.join(source_path, str(channel_id))
    channel_target_dir = os.path.join(target_path, str(channel_id))

    # 确保源目录存在，用于存放临时的 json 文件
    os.makedirs(channel_source_dir, exist_ok=True)
    # 脚本目录
    script_dir = os.path.dirname(__file__)

    # 1. 导出 JSON 文件
    json_path = os.path.join(script_dir, f"{channel_id}.json")
    logging.info(f"正在导出频道 {channel_id} 的信息到 {json_path}...")
    # 假设 tdl 有导出命令，这里用 tdl export 举例，请替换为你实际使用的导出命令
    # tdl chat export -c CHAT -o /path/to/output.json
    subprocess.run(['tdl', 'chat', 'export', '-c', str(channel_id), '-o', json_path], check=True)

    # 2. 读取并过滤 JSON 数据
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 获取目标目录下已有的文件
    existing_files = get_existing_files(channel_target_dir)

    # 过滤掉已存在的文件
    # 规则：target_path 下存在 "messageId_filename" 格式的文件则跳过
    filtered_messages = []
    for msg in data.get('messages', []):
        msg_id = msg['id']
        file_name = msg['file']
        target_file_name = f"{msg_id}_{file_name}"

        if target_file_name not in existing_files:
            filtered_messages.append(msg)

    if not filtered_messages:
        logging.info(f"频道 {channel_id} 的所有文件均已下载，跳过。")
        return

    # 将过滤后的数据写到 channel_id_filtered.json
    data['messages'] = filtered_messages
    filtered_json_path = os.path.join(script_dir, f"{channel_id}_filtered.json")
    with open(filtered_json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    # 3. 执行下载命令
    # 例子: tdl dl -f channelid.json --template "{{ .MessageID }}_{{ .FileName }}" -d $source_path/channelId
    logging.info(f"开始下载频道 {channel_id} 的新文件...")
    cmd = [
        'tdl', 'dl',
        '-f', filtered_json_path,
        '--template', '{{ .MessageID }}_{{ .FileName }}',
        '-d', channel_source_dir
    ]
    subprocess.run(cmd, check=True)
    logging.info(f"频道 {channel_id} 下载完成。")


def process_urls(urls, source_path):
    """处理 URL 的下载逻辑"""
    # 修正：使用 target_path 下的 default 目录，与 channel 逻辑保持一致
    default_source_path = os.path.join(source_path, "default")
    os.makedirs(default_source_path, exist_ok=True)

    logging.info(f"开始下载 {len(urls)} 个 URL 到 {default_source_path}...")

    # 注意：这里根据你的需求描述，下载目录应为 target_path/default
    cmd = ['tdl', 'dl']

    # 遍历 urls 列表，为每个 url 前面添加 '-u' 参数
    for url in urls:
        cmd.extend(['-u', url.strip()])

    # 添加模板和下载目录参数
    cmd.extend([
        '--template', "{{ .DialogID }}_{{ .MessageID }}_{{ .FileName }}",
        '-d', default_source_path
    ])
    subprocess.run(cmd, check=True)
    logging.info("URL 下载完成。")


def run_download_task():
    """对外暴露的纯业务执行入口"""
    logging.info("开始执行下载任务...")

    # 加载配置
    config = load_config('tdl.conf')

    source_path = config['source_path']
    target_path = config['target_path']

    # 确保基础目录存在
    os.makedirs(source_path, exist_ok=True)
    os.makedirs(target_path, exist_ok=True)

    # 处理 Channel 下载
    channel_ids = [cid.strip() for cid in config['channel'].split(',')]
    for cid in channel_ids:
        process_channel(cid, source_path, target_path)

    # 处理 URL 下载
    urls = [url.strip() for url in config['url'].split(',')]
    process_urls(urls, source_path)

    # 处理收藏下载
    favorites = config['favorites']
    if favorites:
        process_channel('favorites', source_path, target_path)

    logging.info("所有下载任务执行完毕。")