FROM python:3.13-alpine

WORKDIR /app

ENV PYTHONUNBUFFERED=1

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
COPY prismaapi.py .

USER python

ENTRYPOINT ["python"]
CMD ["checkDefenderUpdate.py"]