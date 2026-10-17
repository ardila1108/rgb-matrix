FROM node:18-alpine

# Set environment variable to skip chromium download during npm install
ENV PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true

WORKDIR /app

COPY package*.json ./

# Install alpine-compatible chromium and its dependencies
RUN apk add --no-cache \
    chromium \
    nss \
    freetype \
    harfbuzz \
    ca-certificates \
    ttf-freefont

RUN npm install

COPY . .

CMD ["npm", "start"]