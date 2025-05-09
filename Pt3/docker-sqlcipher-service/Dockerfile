# Stage 1: Build the application
FROM node:18-alpine3.18 AS builder 

WORKDIR /usr/src/app

# Install build-essential and python3 for node-gyp (sqlcipher dependency)
RUN apk add --no-cache build-base python3

COPY package*.json ./

# Install dependencies including devDependencies for building
RUN npm install

COPY . .

# Build TypeScript
RUN npm run build

# Stage 2: Production image
FROM node:18-alpine3.18 

WORKDIR /usr/src/app

# Install only production dependencies
COPY package*.json ./
# Add openssl1.1-compat for libcrypto.so.1.1 and build tools for native modules
RUN apk add --no-cache build-base python3 openssl1.1-compat # Needed for sqlcipher runtime and build
RUN npm install --omit=dev # This will create node_modules with production dependencies

# Copy built application from builder stage
COPY --from=builder /usr/src/app/dist ./dist

# Expose port
EXPOSE 3000

# Command to run the application
CMD ["node", "dist/server.js"]