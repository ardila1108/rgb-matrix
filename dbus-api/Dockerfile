FROM node:18-alpine

# Tell Puppeteer NOT to download its own Chrome binary
ENV PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true
# Tell Puppeteer WHERE to find the system-installed Chromium on Alpine
ENV PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium-browser

WORKDIR /app

# Install alpine-compatible chromium and its dependencies BEFORE npm install
RUN apk add --no-cache \
    chromium \
    nss \
    freetype \
    harfbuzz \
    ca-certificates \
    ttf-freefont

COPY package*.json ./

RUN npm install

COPY . .

CMD ["npm", "start"]