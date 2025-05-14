import express from 'express';
import bodyParser from 'body-parser';
import { setRecordRoutes } from './routes/item.routes';
import { RecordController } from './controllers/record.controller';
import { Database } from 'sqlite';
import { initDb } from './services/database.service';
import http from 'http'; // <-- Add this import

const app = express();
const PORT = process.env.PORT || 3000;

app.use(bodyParser.json());

initDb().then((dbInstance: Database) => {
    console.log('Database initialized successfully.');

    const recordController = new RecordController(dbInstance);

    setRecordRoutes(app, recordController);

    // Create HTTP server and set keepAliveTimeout and headersTimeout
    const server = http.createServer(app);
    server.keepAliveTimeout = 65000; // 65 seconds
    server.headersTimeout = 66000;   // Should be greater than keepAliveTimeout

    server.listen(PORT, () => {
        console.log(`Server is running on port ${PORT}`);
    });
}).catch(error => {
    console.error("Failed to initialize database or start server:", error);
    process.exit(1);
});