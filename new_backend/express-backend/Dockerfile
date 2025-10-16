FROM node:18-alpine

# Install system dependencies for native modules and pnpm
RUN apk add --no-cache python3 py3-pip build-base curl && \
    npm install -g pnpm

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN pnpm install

# Copy Prisma schema
COPY prisma ./prisma

# Generate Prisma client
RUN npx prisma generate

# Copy rest of the source code
COPY . .

# Build TS
RUN pnpm run build

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Start the application
CMD ["pnpm", "run", "start"]