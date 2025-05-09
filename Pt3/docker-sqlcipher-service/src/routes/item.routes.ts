import { Router, Application } from 'express'; // Import Application type for 'app'
// Assuming you will create/rename ItemController to RecordController
// and its methods to insertRecord and getRecordByUserId
import { RecordController } from '../controllers/record.controller';

const router = Router(); // This router instance is not directly used by setRecordRoutes in this snippet
                        // but can be useful if you expand routing logic within this file.

// We'll assume RecordController will be instantiated and its methods bound.

// Updated function to accept a RecordController instance
export function setRecordRoutes(app: Application, recordController: RecordController) {
    // POST endpoint to insert a new record
    // The request body should contain the record data (user_id, timestamp, heart_rate, etc.)
    app.post('/records', recordController.insertRecord.bind(recordController));

    // GET endpoint to retrieve a record by its user_id
    // The user_id will be available as a route parameter
    app.get('/records/:user_id', recordController.getRecordByUserId.bind(recordController));
}