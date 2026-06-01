# app.py
import os
from flask import Flask, request, jsonify, render_template_string, redirect, url_for, flash
from tdl import run_download_task

app = Flask(__name__)

app = Flask(__name__)
app.secret_key = 'some_secret_key_for_flash_messages'  # 用于在网页上显示提示信息

# 定义一个简单的 HTML 网页模板
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>下载任务执行器</title>
    <style>
        body { font-family: Arial, sans-serif; display: flex; justify-content: center; padding-top: 50px; }
        .container { width: 300px; padding: 20px; border: 1px solid #ccc; border-radius: 8px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
        input[type="password"] { width: 100%; padding: 10px; margin: 10px 0; box-sizing: border-box; }
        button { width: 100%; padding: 10px; background-color: #28a745; color: white; border: none; border-radius: 4px; cursor: pointer; }
        button:hover { background-color: #218838; }
        .message { color: red; margin-bottom: 10px; }
    </style>
</head>
<body>
    <div class="container">
        <h2>执行下载任务</h2>
        <!-- 显示执行后的提示信息 -->
        {% with messages = get_flashed_messages() %}
          {% if messages %}
            {% for message in messages %}
              <div class="message">{{ message }}</div>
            {% endfor %}
          {% endif %}
        {% endwith %}

        <!-- 密码输入表单 -->
        <form action="/execute" method="post">
            <label for="password">请输入执行密码：</label>
            <input type="password" id="password" name="password" required>
            <button type="submit">确认执行</button>
        </form>
    </div>
</body>
</html>
"""


# 1. 访问根目录时，展示带有密码输入框的网页
@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)


# 2. 处理网页表单提交的密码
@app.route('/execute', methods=['POST'])
def execute_task():
    # 获取网页表单中输入框（name="password"）的值
    input_password = request.form.get('password')

    # 从环境变量中获取真实的安全密码
    SAFE_PASSWORD = os.getenv('API_PASSWORD')

    if not SAFE_PASSWORD:
        flash("服务器未配置安全密码，请联系管理员！")
        return redirect(url_for('index'))

    # 验证密码
    if input_password != SAFE_PASSWORD:
        flash("密码错误，无权执行任务！")
        return redirect(url_for('index'))

    try:
        # 密码正确，调用业务层的下载函数
        run_download_task()
        flash("✅ 下载任务已成功触发并执行完毕！")
    except Exception as e:
        flash(f"❌ 任务执行出错: {str(e)}")

    # 执行完后跳回首页（并带上上面的提示信息）
    return redirect(url_for('index'))

if __name__ == '__main__':
    # 启动服务，默认访问地址为 http://127.0.0.1:8888
    app.run(host='0.0.0.0', port=8888)