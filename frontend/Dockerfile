FROM node:18-alpine

WORKDIR /app
COPY frontend/package*.json ./
RUN npm install --silent

COPY frontend ./
EXPOSE 3000
CMD ["npm", "run", "dev"]
