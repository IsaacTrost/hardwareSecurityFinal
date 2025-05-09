import { Request, Response } from 'express';
import { Database } from 'sqlite'; // Import Database type from sqlite
import { RecordEntry } from '../types/item.types'; // Assuming this type matches your table
import { Buffer } from 'buffer'; // For handling BLOB data

export class RecordController {
    private db: Database;

    constructor(db: Database) { // Constructor now accepts a Database instance
        this.db = db;
    }

    async insertRecord(req: Request, res: Response) {
        // Destructure expected fields from RecordEntry
        const { user_id, timestamp, heart_rate, blood_pressure, notes } = req.body as Partial<RecordEntry>;

        if (!user_id || timestamp === undefined || heart_rate === undefined || !blood_pressure) {
            return res.status(400).json({ message: 'Missing required fields: user_id, timestamp, heart_rate, blood_pressure' });
        }

        try {
            // Convert notes to Buffer if it's a string (example for BLOB)
            // If notes is already a Buffer (e.g., from a file upload parsed appropriately), it will be used as is.
            // If notes is undefined or null, it will be passed as null to the DB.
            const notesBuffer = notes ? (typeof notes === 'string' ? Buffer.from(notes, 'utf-8') : notes) : null;

            await this.db.run(
                'INSERT INTO records (user_id, timestamp, heart_rate, blood_pressure, notes) VALUES (?, ?, ?, ?, ?)',
                user_id,
                timestamp,
                heart_rate,
                blood_pressure,
                notesBuffer // Pass the Buffer or null
            );
            res.status(201).json({ message: 'Record inserted successfully', userId: user_id });
        } catch (error) {
            console.error('Error inserting record:', error);
            const err = error as Error & { code?: string }; // Type assertion for common error properties
            if (err.code === 'SQLITE_CONSTRAINT' && err.message.includes('UNIQUE constraint failed: records.user_id')) {
                return res.status(409).json({ message: 'Conflict: Record with this user_id already exists.' });
            }
            res.status(500).json({ message: 'Error inserting record', error: err.message });
        }
    }

    async getRecordByUserId(req: Request, res: Response) {
        const { user_id } = req.params; // Assuming user_id is passed as a URL parameter
        try {
            const record: RecordEntry | undefined = await this.db.get(
                'SELECT user_id, timestamp, heart_rate, blood_pressure, notes FROM records WHERE user_id = ?',
                user_id
            );

            if (record) {
                // The 'notes' field will be a Buffer if it was stored as a BLOB and is not null.
                // The client will need to handle this Buffer (e.g., convert to base64 for JSON, or process as binary).
                res.status(200).json(record);
            } else {
                res.status(404).json({ message: 'Record not found' });
            }
        } catch (error) {
            console.error('Error retrieving record:', error);
            const err = error as Error;
            res.status(500).json({ message: 'Error retrieving record', error: err.message });
        }
    }
}