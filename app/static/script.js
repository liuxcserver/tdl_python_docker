const socket = io();
const logBox = document.getElementById('log-box');
const autoScrollCheckbox = document.getElementById('auto-scroll');
const passwordModal = new bootstrap.Modal(document.getElementById('passwordModal'));
const editConfigModal = new bootstrap.Modal(document.getElementById('editConfigModal'));

// 页面加载完成后获取配置和历史日志
document.addEventListener('DOMContentLoaded', function() {
    // 1. 获取配置文件内容
    fetch('/get_config')
        .then(response => response.json())
        .then(data => {
            document.getElementById('config-display').value = data.content;
        });

    // 2. 获取历史日志 (新增部分)
    fetch('/get_history_logs')
        .then(response => response.json())
        .then(data => {
            if (data.logs && data.logs.length > 0) {
                data.logs.forEach(log => addHistoryLog(log));
                addToLog('--- 已加载历史日志，以下是实时监控 ---');
            }
        });
});

// 专门用来展示历史日志的方法（不再额外添加当前时间戳）
function addHistoryLog(message) {
    const logBox = document.getElementById('log-box');
    logBox.innerHTML += `${message}<br>`;
    if (autoScrollCheckbox.checked) {
        logBox.scrollTop = logBox.scrollHeight;
    }
}

// 展示实时日志的方法（带当前时间戳）
function addToLog(message) {
    const timestamp = new Date().toLocaleTimeString();
    const timeSpan = `<span class="log-time">[${timestamp}]</span>`;
    logBox.innerHTML += `${timeSpan}${message}<br>`;
    if (autoScrollCheckbox.checked) {
        logBox.scrollTop = logBox.scrollHeight;
    }
}

// 1. 提交密码并执行任务
function submitPassword() {
    const password = document.getElementById('inputPassword').value;
    if (!password.trim()) {
        showToast('密码不能为空！', 'danger');
        return;
    }

    fetch('/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password: password })
    })
    .then(response => response.json())
    .then(data => {
        passwordModal.hide();
        document.getElementById('inputPassword').value = '';
        if (data.status === 'success') {
            addToLog('✅ 任务已发送至后台执行...');
            showToast('任务启动成功！', 'success');
        } else {
            showToast(data.message, 'danger');
        }
    })
    .catch(() => {
        passwordModal.hide();
        showToast('网络请求失败，请检查服务状态。', 'danger');
    });
}

// 2. 从弹窗中保存配置
function saveConfigFromModal() {
    const content = document.getElementById('config-editor').value;
    fetch('/save_config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: content })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            // 保存成功后，同步更新左侧的只读展示框
            document.getElementById('config-display').value = content;
            editConfigModal.hide(); // 关闭弹窗
            showToast('配置文件保存成功！', 'success');
            addToLog('📝 配置文件已被修改并保存。');
        }
    });
}

// 3. 清空日志
function clearLogs() {
    logBox.innerHTML = '';
    addToLog('日志已手动清空。');
}

// 4. 显示轻提示 (Toast)
function showToast(message, type = 'primary') {
    const toastEl = document.getElementById('liveToast');
    const toastBody = document.getElementById('toastMessage');
    const icon = toastEl.querySelector('i');
    toastBody.innerText = message;
    icon.className = `bi me-2 ${type === 'success' ? 'bi-check-circle-fill text-success' : 'bi-exclamation-circle-fill text-danger'}`;
    const toast = new bootstrap.Toast(toastEl);
    toast.show();
}

// 监听 WebSocket 推送的实时日志
socket.on('log_update', function(msg) {
    addToLog(msg.data);
});

// 监听 WebSocket 连接状态
socket.on('connect', () => addToLog('🟢 WebSocket 实时通道已建立。'));
socket.on('disconnect', () => addToLog('🔴 WebSocket 连接已断开。'));

// 监听编辑配置弹窗打开，自动聚焦并填充当前内容
document.getElementById('editConfigModal').addEventListener('show.bs.modal', function () {
    const currentContent = document.getElementById('config-display').value;
    document.getElementById('config-editor').value = currentContent;
    setTimeout(() => document.getElementById('config-editor').focus(), 100);
});