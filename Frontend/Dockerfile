# Frontend/Dockerfile
FROM node:18

WORKDIR /app

COPY dist/package*.json ./

# 👇 Skip peer dependency conflicts
RUN npm install --legacy-peer-deps

COPY dist ./

EXPOSE 3000

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
