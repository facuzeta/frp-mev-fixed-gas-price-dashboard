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
RUN apt update && apt install -y build-essential make postgresql-client zip wget cron nano htop

# COPY code for decode osmosis
COPY tools_decoder_tx_osmosis tools_decoder_tx_osmosis

# compile osmosis decoder
RUN /code/tools_decoder_tx_osmosis/script_install_go_decoder.sh 

# copy project
COPY dashboard_site dashboard_site

# add to crontab the script that get osmosis data every hour
COPY run_script_per_hour_cron.sh .
RUN /code/run_script_per_hour_cron.sh
CMD ["service", "cron", "start"]