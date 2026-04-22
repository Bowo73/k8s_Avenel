FROM python:3.14.2-alpine3.23

WORKDIR /tmp

# Build deps for pandas/numpy wheels when needed
RUN apk add --no-cache \
    build-base \
    libffi-dev \
    musl-dev

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir pandas==2.3.3 sqlalchemy==2.0.45 pymysql==1.1.2

# Script expects CSVs at /tmp/*.csv
COPY sky_map/data/hyg_v42.csv /tmp/hyg_v42.csv
COPY sky_map/data/worldcities.csv /tmp/worldcities.csv
COPY k8s_Avenel/data/populate_database_with_csv.py /tmp/populate_database_with_csv.py

CMD ["python3", "/tmp/populate_database_with_csv.py"]
