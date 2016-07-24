FROM ubuntu:trusty
COPY dist/ /target/dist
COPY app.ini /target/
COPY requirements.txt /target/
WORKDIR /target
RUN apt-get update && \
  apt-get install -y python3 python-virtualenv && \
  rm -rf /var/lib/apt/lists/* && \
  virtualenv --python=python3 env && \
  env/bin/pip install dist/godhand-*-py3-*.whl && \
  env/bin/pip install -r requirements.txt && \
  mkdir -p var/books
VOLUME /target/var
EXPOSE 7764
CMD ["env/bin/pserve", "app.ini"]
