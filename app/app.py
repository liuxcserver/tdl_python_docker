import os
import threading
import time
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
from tdl import run_tdl
import configparser

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'
socketio = SocketIO(app, cors_allowed_origins="*")

# 全局变量
IS_TASK_RUNNING = False
TASK_LOCK = threading.Lock()
CONFIG_PATH = "tdl.conf"
LOG_PATH = "tdl_execution.log"


# 读取配置文件
def read_config():
    if not os.path.exists(CONFIG_PATH):
        return ""
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return f.read()


# 写入配置文件
def write_config(content):
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        f.write(content)


# 模拟执行任务的函数 (你需要将这里替换为你 downloader.py 中的逻辑)
def run_download_task():
    global IS_TASK_RUNNING

    try:
        run_tdl()
    except Exception as e:
        socketio.emit('log_update', {'data': f"[Error] {str(e)}"})
    finally:
        IS_TASK_RUNNING = False


@app.route('/')
def index():
    config_content = read_config()
    return render_template('index.html', config_content=config_content)


# 接口：获取配置
@app.route('/get_config', methods=['GET'])
def get_config():
    return jsonify({"content": read_config()})


# 接口：保存配置
@app.route('/save_config', methods=['POST'])
def save_config():
    content = request.json.get('content', '')
    write_config(content)
    return jsonify({"status": "success"})


# 接口：执行任务
@app.route('/execute', methods=['POST'])
def execute():
    global IS_TASK_RUNNING
    password = request.json.get('password')

    # 这里替换为你的实际密码验证逻辑
    if password != "123456":
        return jsonify({"status": "error", "message": "密码错误！"})

    with TASK_LOCK:
        if IS_TASK_RUNNING:
            return jsonify({"status": "error", "message": "任务正在运行中，请勿重复提交！"})

        IS_TASK_RUNNING = True
        # 在后台线程运行任务
        thread = threading.Thread(target=run_download_task)
        thread.start()

    return jsonify({"status": "success", "message": "任务已启动"})


@app.route('/get_history_logs', methods=['GET'])
def get_history_logs():
    log_path = "tdl_execution.log"
    if not os.path.exists(log_path):
        return jsonify({"logs": []})

    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            all_logs = f.readlines()
            last_logs = all_logs[-200:]  # 只返回最后200行
            return jsonify({"logs": [log.strip() for log in last_logs]})
    except Exception as e:
        return jsonify({"logs": [], "error": str(e)})

# WebSocket：实时日志推送
@socketio.on('connect')
def handle_connect():
    emit('log_update', {'data': '[系统] 已连接到服务器'})


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)