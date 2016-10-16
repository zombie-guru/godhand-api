FROM alpine:3.4
EXPOSE 7764
COPY . /target/
RUN apk add --no-cache python3 unrar build-base python3-dev jpeg-dev zlib-dev \
  && cd target \
  && LIBRARY_PATH=/lib:/usr/lib pip3 install --no-cache-dir -r requirements.txt \
  && pip3 install dumb-init==1.1.3 \
  && pip3 install . \
  && apk del build-base python3-dev \
  && mv /target/app.ini / \
  && cd / \
  && rm -r /target
COPY ./build/docs /docs/
ENTRYPOINT ["dumb-init", "--"]
CMD ["pserve", "app.ini"]
