import os
import logging
import logging.handlers
import threading
import configparser
from tdl import run_tdl
from scheduler import scheduler_loop
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# 全局变量
IS_TASK_RUNNING = False
TASK_LOCK = threading.Lock()
CONFIG_PATH = "tdl.ini"

def load_global_config():
    """读取配置文件并更新到 Flask 的全局 app.config 中"""
    if not os.path.exists(CONFIG_PATH):
        print(f"警告：配置文件 {CONFIG_PATH} 不存在，跳过加载。")
        return

    config = configparser.ConfigParser()
    # 读取配置文件（注意编码，防止中文乱码）
    config.read(CONFIG_PATH, encoding='utf-8')

    # 将配置文件中的所有段(section)和键值(key-value)更新到 app.config
    # 为了避免冲突，我们可以在键名前加个前缀，比如 CONF_
    for section in config.sections():
        for key, value in config.items(section):
            # 统一转成大写，并加上前缀存入全局配置
            conf_key = f"{section}_{key}"
            app.config[conf_key] = value
            print(f"加载配置: {conf_key} = {value}")


# ================= 核心日志配置 =================
def setup_app_logger():
    logger = logging.getLogger('my_app')
    logger.setLevel(logging.INFO)
    logger.propagate = False
    if not logger.handlers:
        file_handler = logging.handlers.RotatingFileHandler(
            app.config.get('tdl_log_path'), maxBytes=10 * 1024 * 1024, backupCount=5, encoding='utf-8'
        )
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    return logger

# 程序启动时，先加载一次初始配置
load_global_config()
app_logger = setup_app_logger()

# ================= 新增：读取日志文件末尾 N 行 =================
def get_last_n_lines(filepath, n=1000):
    """读取文件的最后 n 行，如果文件不存在则返回空列表"""
    if not os.path.exists(filepath):
        return []
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            # 读取所有行并返回最后 n 行
            all_lines = f.readlines()
            return [line.strip() for line in all_lines[-n:]]
    except Exception as e:
        print(f"读取日志失败: {e}")
        return []


# ================= 业务逻辑 =================
def run_download_task():
    global IS_TASK_RUNNING
    try:
        # 任务开始前清空日志
        with open(app.config.get('tdl_log_path'), 'w', encoding='utf-8') as f:
            pass
        app_logger.info("========== 任务开始执行 ==========")

        # 运行你的核心任务
        run_tdl()

        app_logger.info("========== 任务执行成功 ==========")
    except Exception as e:
        app_logger.error(f"任务出错: {str(e)}")
    finally:
        IS_TASK_RUNNING = False


# ================= 路由接口 =================
@app.route('/')
def index():
    config_content = ""
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            config_content = f.read()
    # 页面加载时，直接读取最新的 1000 行日志传给前端
    recent_logs = get_last_n_lines(app.config.get('tdl_log_path'), 1000)
    return render_template('index.html', config_content=config_content, recent_logs=recent_logs)


@app.route('/execute', methods=['POST'])
def execute():
    global IS_TASK_RUNNING
    password = request.json.get('password')

    if password != app.config.get('SECRET_KEY'):
        return jsonify({"status": "error", "message": "密码错误！"})

    with TASK_LOCK:
        if IS_TASK_RUNNING:
            return jsonify({"status": "error", "message": "任务正在运行中！"})
        IS_TASK_RUNNING = True
        task_thread = threading.Thread(target=run_download_task)
        task_thread.daemon = True
        task_thread.start()

    return jsonify({"status": "success", "message": "任务已启动，请刷新页面查看最新日志"})


# 保留获取配置的接口（如果前端还需要动态保存配置的话）
@app.route('/get_config', methods=['GET'])
def get_config():
    content = ""
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            content = f.read()
    return jsonify({"content": content})


@app.route('/save_config', methods=['POST'])
def save_config():
    content = request.json.get('content', '')
    try:
        # 1. 将前端传来的内容写入配置文件
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            f.write(content)

        # 2. 【核心步骤】文件写入成功后，立刻重新加载全局配置
        load_global_config()

        return jsonify({"status": "success", "message": "配置已保存并生效"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/get_logs')
def get_logs():
    """专门给前端提供最新日志的接口"""
    logs = get_last_n_lines(app.config.get('tdl_log_path'), 1000)
    # 将日志列表拼接成一个长字符串返回，方便前端直接渲染
    return jsonify({"logs": "\n".join(logs)})


if __name__ == '__main__':
    # 创建并启动定时任务线程
    if app.config.get('tdl_scheduler', 'false').lower() == 'true':
        task_thread = threading.Thread(target=scheduler_loop, args=(1800,), daemon=True)
        task_thread.start()

    app.run(host='0.0.0.0', port=8888, debug=True)