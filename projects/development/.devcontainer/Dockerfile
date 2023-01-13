FROM mcr.microsoft.com/devcontainers/base:bullseye
LABEL org.opencontainers.image.source https://github.com/natb1/CommunityDashboard

RUN apt-get update && apt-get install -y build-essential libssl-dev chromium
RUN curl -L https://raw.githubusercontent.com/tj/n/master/bin/n -o n
RUN bash n hydrogen
RUN corepack enable

RUN apt-get update && apt-get install -y python3-pip python3-dev
RUN pip install -U pip

RUN type -p curl >/dev/null || sudo apt install curl -y
RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg \
  && sudo chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg \
  && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
  && sudo apt update \
  && sudo apt install gh -y

USER vscode
RUN echo "export CHROME_BIN=/usr/bin/chromium" >> ~/.bashrc