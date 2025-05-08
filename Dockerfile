# Use lightweight Node.js image
FROM node:18-alpine

# Set working directory
WORKDIR /app

# Install http-server to serve static files
RUN npm install -g http-server

# Copy all files from current directory to /app in container
COPY . .

# Expose port 8080 (default for http-server)
EXPOSE 8080

# Start the server
CMD ["http-server", "-p", "8080"]
