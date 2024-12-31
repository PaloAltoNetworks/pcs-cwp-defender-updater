FROM --platform=linux/amd64 python:3.12-alpine

WORKDIR /app

ENV PYTHONUNBUFFERED=1

RUN mkdir twistlock
RUN mkdir init
RUN mkdir config
RUN adduser -D --uid 10001 python
RUN chown -R python:python /app

COPY requirements.txt requirements.txt
RUN pip3 install --upgrade pip
RUN pip3 install --no-cache-dir -r requirements.txt


RUN pip uninstall -y pip
RUN rm -rf /root/.cache/pip
RUN apk update && apk upgrade
RUN apk -v cache clean
RUN apk --purge del apk-tools
RUN rm -f /bin/sh

COPY checkDefenderUpdate.py .
COPY deleteJob.py .

USER python

ENTRYPOINT ["python"]
CMD ["checkDefenderUpdate.py"]