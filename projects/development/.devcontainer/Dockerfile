FROM mcr.microsoft.com/devcontainers/base:bullseye
LABEL org.opencontainers.image.source https://github.com/natb1/CommunityDashboard

RUN apt-get update && apt-get install -y build-essential libssl-dev chromium
RUN curl -L https://raw.githubusercontent.com/tj/n/master/bin/n -o n
RUN bash n hydrogen
RUN bash -i -c 'npm i -g @angular/cli'

RUN apt-get update && apt-get install -y python3-pip python3-dev
RUN pip install -U pip

USER vscode
RUN echo "export CHROME_BIN=/usr/bin/chromium" >> ~/.bashrc