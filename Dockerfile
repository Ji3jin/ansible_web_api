FROM python:3.6
RUN mkdir /ansible_api
COPY requirements.txt ./
COPY app/ ./ansible_api/app
COPY config.py ./ansible_api/config.py
COPY manage.py ./ansible_api/manage.py
COPY gunicorn.conf.py ./ansible_api/gunicorn.conf.py
RUN pip install --no-cache-dir -r requirements.txt
WORKDIR /ansible_api
CMD ["gunicorn","manage:app","-c","gunicorn.conf.py"]