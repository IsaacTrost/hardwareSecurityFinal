# Stage 1: Build the application
FROM node:24-bookworm AS builder 

WORKDIR /usr/src/app



# Install build-essential and python3 for node-gyp (sqlcipher dependency)
RUN apt-get update && apt-get install -y build-essential python3

COPY package*.json ./

# Install dependencies including devDependencies for building
RUN npm install

COPY . .

# Build TypeScript
RUN npm run build

FROM ubuntu:24.04 AS sgx_builder

WORKDIR /build

FROM ubuntu:24.04

# Install Node.js (replace with your required version)
RUN apt-get update && apt-get install -y curl
RUN curl -fsSL https://deb.nodesource.com/setup_24.x | bash -
RUN apt-get install -y nodejs build-essential python3

WORKDIR /usr/src/app

# Install only production dependencies
COPY package*.json ./
# Add openssl1.1-compat for libcrypto.so.1.1 and build tools for native modules
RUN apt-get update && apt-get -y install build-essential python3  # Needed for sqlcipher runtime and build
RUN npm install --omit=dev # This will create node_modules with production dependencies
# Copy built application from builder stage
COPY --from=builder /usr/src/app/dist ./dist
RUN apt-get update && apt-get install -y wget gnupg build-essential

RUN curl -fsSL https://packages.cloud.google.com/apt/doc/apt-key.gpg | gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] http://packages.cloud.google.com/apt cloud-sdk main" > /etc/apt/sources.list.d/google-cloud-sdk.list && \
    apt-get update && \
    apt-get install -y google-cloud-sdk

RUN apt-get update && \
    apt-get install -y wget && \
    wget https://launchpad.net/ubuntu/+archive/primary/+files/libssl1.1_1.1.1f-1ubuntu2.22_amd64.deb && \
    dpkg -i libssl1.1_1.1.1f-1ubuntu2.22_amd64.deb && \
    rm libssl1.1_1.1.1f-1ubuntu2.22_amd64.deb
# Expose port
EXPOSE 3000
COPY start_server.sh ./
# Command to run the application
CMD ["sh", "start_server.sh"]