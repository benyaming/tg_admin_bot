FROM python:3.9-slim

RUN pip install pipenv
WORKDIR /home/app
COPY . .
WORKDIR /home/app/admin_bot
RUN pipenv install
ENV PYTHONPATH=/home/app
CMD ["pipenv", "run", "python", "bot.py"]
