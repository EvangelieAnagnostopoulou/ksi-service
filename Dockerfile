FROM ubuntu:18.04

ARG KSI_TOOL_TAG=2.9.1374
ARG EXTRA_CERT_DIR=/usr/local/share/ca-certificates/extra/

COPY globalsign.crt ${EXTRA_CERT_DIR}

# Install c build tools.
# Install certificate for publications file verification.
# Clone and build KSI tool ubuntu package.
# Install KSI tool.
# Clean build tools.
RUN apt-get update \
    && apt-get -y install git gcc make autoconf automake libtool openssl curl libcurl4-gnutls-dev libssl-dev debmake \
    && update-ca-certificates \
    \
    && git clone https://github.com/guardtime/ksi-tool.git \
    && cd /ksi-tool \
    && git checkout v${KSI_TOOL_TAG} \
    && ./rebuild.sh --get-dep-online --ign-dep-online-err --no-dep-check --link-static --build-deb \
    && dpkg -i ksi-tools_${KSI_TOOL_TAG}-*.deb \
    && cd .. \
    && rm -rf /ksi-tool \
    \
    && dpkg -r devscripts g++ libgit-wrapper-perl build-essential dpkg-dev git gcc make autoconf automake libtool debmake \
    \
    && apt -y autoremove

# Install python
RUN apt-get update \
  && apt-get install -y python3-pip python3-dev \
  && cd /usr/local/bin \
  && ln -s /usr/bin/python3 python \
  && pip3 install --upgrade pip

# Install api & run server
RUN mkdir /code
WORKDIR /code
COPY requirements.txt /code/
RUN pip install -r requirements.txt
COPY . /code/

ARG LANG=C.UTF-8
CMD ["uvicorn", "main:app"]
