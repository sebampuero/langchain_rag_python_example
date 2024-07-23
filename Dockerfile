FROM python:3.11

RUN apt-get update && apt-get install -y libgl1 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip install --upgrade pip && pip install virtualenv

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"


COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
COPY langchain/libs/community/langchain_community /opt/venv/lib/python3.11/site-packages/langchain_community

RUN useradd -m myuser
RUN chown -R myuser:myuser /app
USER myuser

ENV OLLAMA_HOST=http://192.168.0.7:11434

CMD ["python3", "src/main.py"]