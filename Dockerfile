# 第一阶段:构建依赖项
FROM python:3.9-alpine AS builder

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY ./requirements.txt .

# 安装依赖
RUN pip install --no-cache-dir -U -r requirements.txt

# 第二阶段:最终镜像
FROM python:3.9-alpine

# 设置工作目录
WORKDIR /app

# 从第一阶段复制依赖项到最终镜像
COPY --from=builder /usr/local /usr/local

# 复制应用程序代码
COPY . .

# 暴露端口
EXPOSE 6789

# 启动命令
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "6789"]