FROM ubuntu:16.04
COPY dist/godhand-*-py3-*.whl app.ini requirements.txt /target/
WORKDIR /target
RUN apt-get update && \
  apt-get install -y software-properties-common python-software-properties && \
  apt-add-repository multiverse && \
  apt-get update && \
  apt-get install -y python3 python3-pip unrar && \
  rm -rf /var/lib/apt/lists/* && \
  pip3 install godhand-*-py3-*.whl && \
  pip3 install -r requirements.txt && \
  mkdir -p var/books && \
  rm godhand-*-py3-*.whl
ENV GODHAND_BOOKS_PATH /target/var/books
VOLUME /target/var
EXPOSE 7764
CMD ["pserve", "app.ini"]
