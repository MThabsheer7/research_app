FROM node:22-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

# Expose frontend port
EXPOSE 5173

# Expose host to 0.0.0.0 so that it's accessible outside the container
CMD ["npm", "run", "dev", "--", "--host"]
