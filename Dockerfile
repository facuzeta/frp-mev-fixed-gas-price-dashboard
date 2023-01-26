# base image  
FROM python:3.10.2-slim-bullseye

# Set environment variables
ENV PIP_DISABLE_PIP_VERSION_CHECK 1
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /code

# install dependencies  
COPY requirements.txt .

# install dependencies  
RUN pip install -r requirements.txt

# install psql
RUN apt update && apt install -y postgresql-client zip wget

# copy project
COPY dashboard_site .

# copy data 
COPY small_data .

