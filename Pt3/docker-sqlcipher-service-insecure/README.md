# Docker SQLCipher Service

This project is a simple service that runs in a Docker container and utilizes an SQLCipher database for secure data storage. It provides two main endpoints for interacting with items: one for inserting an item and another for retrieving an item.

## Project Structure

```
docker-sqlcipher-service
├── src
│   ├── app.ts                # Main entry point of the application
│   ├── server.ts             # Server logic to start and listen on a port
│   ├── services
│   │   └── database.service.ts # Manages SQLCipher database connection
│   ├── controllers
│   │   └── item.controller.ts  # Handles item-related business logic
│   ├── routes
│   │   └── item.routes.ts      # Defines routes for item operations
│   └── types
│       └── item.types.ts       # Defines the structure of an item object
├── Dockerfile                  # Instructions to build the Docker image
├── package.json                # npm configuration file with dependencies
├── tsconfig.json               # TypeScript configuration file
└── README.md                   # Project documentation
```

## Setup Instructions

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd docker-sqlcipher-service
   ```

2. **Build the Docker image:**
   ```bash
   docker build -t docker-sqlcipher-service .
   ```

3. **Run the Docker container:**
   ```bash
   docker run -p 3000:3000 docker-sqlcipher-service
   ```

## Usage

Once the service is running, you can interact with the following API endpoints:

- **Insert Item**
  - **Endpoint:** `POST /items`
  - **Request Body:** 
    ```json
    {
      "id": "1",
      "name": "Item Name",
      "description": "Item Description"
    }
    ```

- **Retrieve Item**
  - **Endpoint:** `GET /items/:id`
  - **Response:** 
    ```json
    {
      "id": "1",
      "name": "Item Name",
      "description": "Item Description"
    }
    ```

## Dependencies

This project uses the following key dependencies:
- Express: A web framework for Node.js
- SQLCipher: An extension to SQLite for encrypting database files

## License

This project is licensed under the MIT License.