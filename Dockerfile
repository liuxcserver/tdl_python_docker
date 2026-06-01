FROM iyear/tdl:latest

RUN apk add --no-cache python3 py3-pip

# 3. 设置工作目录
WORKDIR /app

COPY app/requirements.txt /app/requirements.txt

RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt

COPY app/ /app/

CMD ["python3", "app.py"]

ENTRYPOINT ["top", "-b"]