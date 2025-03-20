FROM python:3.9
WORKDIR /app

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

CMD ["sh", "-c", "flask db upgrade && flask run --host=0.0.0.0"]