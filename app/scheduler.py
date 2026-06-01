import subprocess
import time
import os
from datetime import datetime
from flask import current_app

def scheduler_loop(interval_seconds=1800):
    while True:
        # 执行任务
        my_scheduled_task()
        # 睡眠指定的时间
        # 使用 time.sleep 而不是 busy-waiting，不会占用 CPU
        time.sleep(interval_seconds)

def my_scheduled_task():
    """每半小时执行一次的业务逻辑"""
    print(f"[定时任务] 开始执行... {datetime.now()}")
    try:
        # 获取配置
        source_path = current_app.config.get('tdl_source_path')
        target_path = current_app.config.get('tdl_target_path')

        # 遍历 source_path 下的所有 channelid 文件夹
        if not os.path.exists(source_path):
            print(f"源目录 {source_path} 不存在！")
            return

        for channelid in os.listdir(source_path):
            source_channel_dir = os.path.join(source_path, channelid)
            target_channel_dir = os.path.join(target_path, channelid)

            # 确保当前遍历的是文件夹，而不是文件
            if os.path.isdir(source_channel_dir):
                # 如果目标 channelid 文件夹不存在，自动创建
                if not os.path.exists(target_channel_dir):
                    os.makedirs(target_channel_dir)
                    print(f"创建目标文件夹: {target_channel_dir}")

                # 遍历该频道文件夹下的所有文件
                for filename in os.listdir(source_channel_dir):
                    # 核心需求：排除后缀为 .tdl 的文件
                    if filename.endswith('.tdl'):
                        continue

                    source_file = os.path.join(source_channel_dir, filename)
                    # 确保 source_file 是个文件（防止嵌套文件夹报错）
                    if os.path.isfile(source_file):
                        try:
                            # subprocess 执行cp命令
                            subprocess.run(['cp', source_file, target_channel_dir], check=True)
                            print(f"成功复制: {channelid}/{filename}")
                        except Exception as e:
                            print(f"复制失败 {channelid}/{filename}: {e}")
    except Exception as e:
        print(f"[定时任务] 执行出错: {e}")