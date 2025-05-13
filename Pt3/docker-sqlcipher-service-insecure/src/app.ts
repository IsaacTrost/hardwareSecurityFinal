import express from 'express';
import bodyParser from 'body-parser';
import { setRecordRoutes } from './routes/item.routes';
import { RecordController } from './controllers/record.controller';
// Import Database type from sqlite for type annotation
import { Database } from 'sqlite';
import { initDb } from './services/database.service'; // getDb is a function, not a type here

const app = express();
const PORT = process.env.PORT || 3000;

app.use(bodyParser.json());

// initDb() resolves with the Database instance from the 'sqlite' library
initDb().then((dbInstance: Database) => { // Correctly type the resolved value
    console.log('Database initialized successfully.');

    // Pass the initialized dbInstance to the RecordController
    // Ensure RecordController's constructor is set up to accept a Database instance
    const recordController = new RecordController(dbInstance);

    setRecordRoutes(app, recordController);

    app.listen(PORT, () => {
        console.log(`Server is running on port ${PORT}`);
    });
}).catch(error => {
    console.error("Failed to initialize database or start server:", error);
    process.exit(1);
});