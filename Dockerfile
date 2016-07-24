FROM python:3.5.2
COPY dist/godhand-*-py3-*.whl app.ini requirements.txt /target/
WORKDIR /target
RUN pip install godhand-*-py3-*.whl && \
  pip install -r requirements.txt && \
  mkdir -p var/books && \
  rm godhand-*-py3-*.whl
ENV GODHAND_BOOKS_PATH /target/var/books
VOLUME /target/var
EXPOSE 7764
CMD ["pserve", "app.ini"]
