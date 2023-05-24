FROM --platform=linux/amd64 gcr.io/deeplearning-platform-release/sklearn-cpu

# RUN apt-get -y update
# RUN apt-get install -y --no-install-recommends \
# python3-pip \
# pipx \
# git \
# make \
# jq

ADD ./requirements.txt requirements.txt
RUN pip install -r requirements.txt

RUN ln -s /usr/bin/python39 /usr/bin/python