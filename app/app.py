import os
import logging
import logging.handlers
from flask import Flask, render_template, request, jsonify
from tdl import run_tdl
import threading

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'

# 全局变量
IS_TASK_RUNNING = False
TASK_LOCK = threading.Lock()
CONFIG_PATH = "tdl.conf"
LOG_PATH = "tdl.log"


# ================= 核心日志配置 =================
def setup_app_logger():
    logger = logging.getLogger('my_app')
    logger.setLevel(logging.INFO)
    logger.propagate = False
    if not logger.handlers:
        file_handler = logging.handlers.RotatingFileHandler(
            LOG_PATH, maxBytes=10 * 1024 * 1024, backupCount=5, encoding='utf-8'
        )
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    return logger


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
        with open(LOG_PATH, 'w', encoding='utf-8') as f:
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
    recent_logs = get_last_n_lines(LOG_PATH, 1000)
    return render_template('index.html', config_content=config_content, recent_logs=recent_logs)


@app.route('/execute', methods=['POST'])
def execute():
    global IS_TASK_RUNNING
    password = request.json.get('password')

    if password != "5952":
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
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        f.write(content)
    return jsonify({"status": "success"})

@app.route('/get_logs')
def get_logs():
    """专门给前端提供最新日志的接口"""
    logs = get_last_n_lines(LOG_PATH, 1000)
    # 将日志列表拼接成一个长字符串返回，方便前端直接渲染
    return jsonify({"logs": "\n".join(logs)})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8888, debug=True)