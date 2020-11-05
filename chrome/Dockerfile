FROM zenika/alpine-chrome:with-node
USER root

ENV PUPPETEER_SKIP_CHROMIUM_DOWNLOAD 1
ENV PUPPETEER_EXECUTABLE_PATH /usr/bin/chromium-browser
WORKDIR /usr/src/app
COPY package.json package-lock.json ./
RUN npm install
COPY . ./
ENTRYPOINT ["tini", "--"]
CMD ["node", "chrome.js"]