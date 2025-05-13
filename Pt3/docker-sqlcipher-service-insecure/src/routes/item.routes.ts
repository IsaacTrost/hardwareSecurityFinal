import { Router, Application } from 'express'; // Import Application type for 'app'
import { RecordController } from '../controllers/record.controller';

const router = Router();

export function setRecordRoutes(app: Application, recordController: RecordController) {
    // POST endpoint to insert one or more records
    app.post('/records', async (req, res) => {
        // If the body is an array, treat as batch insert
        if (Array.isArray(req.body)) {
            await recordController.insertRecordsBatch(req, res);
        } else {
            await recordController.insertRecord(req, res);
        }
    });

    // GET endpoint to retrieve a record by its user_id
    app.get('/records/:user_id', recordController.getRecordByUserId.bind(recordController));
}