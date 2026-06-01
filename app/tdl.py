import os
import json
import subprocess
import configparser

# 配置基础日志（同时写入文件）
import logging
logger = logging.getLogger('my_app')

def push_log(message):
    """将日志同时写入文件、打印到控制台、推送到前端队列"""
    logger.info(message)

def load_config(config_file):
    """读取配置文件"""
    config = configparser.ConfigParser()
    with open(config_file, encoding='utf-8') as f:
        config.read_string('[default]\n' + f.read())
    return config['default']


def get_existing_files(target_dir):
    """获取目标目录下所有已存在的文件名集合"""
    if not os.path.exists(target_dir):
        return set()
    return {f for f in os.listdir(target_dir) if os.path.isfile(os.path.join(target_dir, f))}


def run_command_and_log(cmd):
    """执行 shell 命令，并实时将输出推送到日志队列"""
    push_log(f"🚀 正在执行命令: {' '.join(cmd)}")

    process = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, bufsize=1, encoding='utf-8'
    )

    with process.stdout:
        for line in process.stdout:
            line = line.strip()
            if line:
                push_log(line)  # 实时推送 tdl 的返回信息

    process.wait()
    if process.returncode != 0:
        error_msg = f"❌ 命令执行失败，退出码: {process.returncode}"
        push_log(error_msg)
        raise subprocess.CalledProcessError(process.returncode, cmd)

    push_log("✅ 命令执行完毕。")


def process_channel(channel_id, source_path, target_path, script_dir):
    """处理单个频道的下载逻辑"""
    channel_source_dir = os.path.join(source_path, str(channel_id))
    channel_target_dir = os.path.join(target_path, str(channel_id))

    os.makedirs(channel_source_dir, exist_ok=True)

    # 1. 导出 JSON 文件
    json_path = os.path.join(script_dir, f"{channel_id}.json")
    push_log(f"正在导出频道 {channel_id} 的信息到 {json_path}...")

    cmd_export = ['tdl', 'chat', 'export', '-c', str(channel_id), '-o', json_path]
    run_command_and_log(cmd_export)

    # 2. 读取并过滤 JSON 数据
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    existing_files = get_existing_files(channel_target_dir)
    filtered_messages = []
    for msg in data.get('messages', []):
        msg_id = msg['id']
        file_name = msg['file']
        target_file_name = f"{msg_id}_{file_name}"
        if target_file_name not in existing_files:
            filtered_messages.append(msg)

    if not filtered_messages:
        push_log(f"频道 {channel_id} 的所有文件均已下载，跳过。")
        return

    data['messages'] = filtered_messages
    filtered_json_path = os.path.join(script_dir, f"{channel_id}_filtered.json")
    with open(filtered_json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    # 3. 执行下载命令
    push_log(f"开始下载频道 {channel_id} 的新文件...")
    cmd_dl = [
        'tdl', 'dl',
        '-f', filtered_json_path,
        '--template', '{{ .MessageID }}_{{ .FileName }}',
        '-d', channel_source_dir
    ]
    run_command_and_log(cmd_dl)
    push_log(f"频道 {channel_id} 下载完成。")


def process_urls(urls,  source_path):
    """处理 URL 的下载逻辑"""
    default_source_path = os.path.join(source_path, "default")
    os.makedirs(default_source_path, exist_ok=True)

    push_log(f"开始下载 {len(urls)} 个 URL 到 {default_source_path}...")

    cmd = ['tdl', 'dl']
    for url in urls:
        cmd.extend(['-u', url.strip()])
    cmd.extend([
        '--template', "{{ .DialogID }}_{{ .MessageID }}_{{ .FileName }}",
        '-d', default_source_path
    ])
    run_command_and_log(cmd)
    push_log("URL 下载完成。")


def run_tdl():
    """对外暴露的纯业务执行入口"""
    push_log("📋 开始执行下载任务...")
    script_dir = os.path.dirname(os.path.abspath(__file__))

    try:
        config = load_config('tdl.ini')
        source_path = config['source_path']
        target_path = config['target_path']

        os.makedirs(source_path, exist_ok=True)
        os.makedirs(target_path, exist_ok=True)

        # 处理 Channel 下载
        channel_ids = [cid.strip() for cid in config['channel'].split(',')]
        for cid in channel_ids:
            if cid:  # 防止空字符串
                process_channel(cid, source_path, target_path, script_dir)

        # 处理 URL 下载
        urls = [url.strip() for url in config['url'].split(',')]
        if urls and urls[0]:  # 防止空字符串
            process_urls(urls, source_path)

        # 处理收藏下载
        favorites = config['favorites']
        if favorites:
            process_channel('favorites', source_path, target_path, script_dir)

        push_log("🎉 所有下载任务执行完毕！")
    except Exception as e:
        push_log(f"❌ 任务执行出错: {str(e)}")
        logging.exception("任务执行详细错误堆栈:")