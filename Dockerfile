FROM alpine:3.4
COPY dist/godhand-*-py3-*.whl app.ini requirements.txt /target/
WORKDIR /target
RUN apk add --no-cache python3 unrar build-base python3-dev jpeg-dev zlib-dev && \
  LIBRARY_PATH=/lib:/usr/lib pip3 install --no-cache-dir godhand-*-py3-*.whl && \
  pip3 install --no-cache-dir -r requirements.txt && \
  pip3 install --no-cache-dir dumb-init && \
  apk del build-base python3-dev
EXPOSE 7764
ENTRYPOINT ["dumb-init", "--"]
CMD ["pserve", "app.ini"]
