# Frontend Service Dockerfile
FROM node:18

# Set working directory
WORKDIR /app

# Copy package files
COPY package.json package-lock.json ./

# Install dependencies
RUN npm install --frozen-lockfile

# Copy application files
COPY . .

# Expose frontend port
EXPOSE 3000

# Start the Next.js application
CMD ["npm", "run", "dev"]
