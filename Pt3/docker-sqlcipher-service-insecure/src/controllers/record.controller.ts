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
            const notesBuffer = notes ? (typeof notes === 'string' ? Buffer.from(notes, 'utf-8') : notes) : null;

            // Try to insert, but if user_id exists, update the record instead
            const result = await this.db.run(
                `INSERT INTO records (user_id, timestamp, heart_rate, blood_pressure, notes)
                 VALUES (?, ?, ?, ?, ?)
                 ON CONFLICT(user_id) DO UPDATE SET
                    timestamp=excluded.timestamp,
                    heart_rate=excluded.heart_rate,
                    blood_pressure=excluded.blood_pressure,
                    notes=excluded.notes`,
                user_id,
                timestamp,
                heart_rate,
                blood_pressure,
                notesBuffer
            );
            res.status(201).json({ message: 'Record inserted or updated successfully', userId: user_id });
        } catch (error) {
            console.error('Error inserting/updating record:', error);
            res.status(500).json({ message: 'Error inserting/updating record', error: (error as Error).message });
        }
    }

    async getRecordByUserId(req: Request, res: Response) {
        const { user_id } = req.params;
        try {
            const record: RecordEntry | undefined = await this.db.get(
                'SELECT user_id, timestamp, heart_rate, blood_pressure, notes FROM records WHERE user_id = ?',
                user_id
            );

            if (record) {
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

    async insertRecordsBatch(req: Request, res: Response) {
        const records = req.body as RecordEntry[];
        if (!Array.isArray(records) || records.length === 0) {
            return res.status(400).json({ message: 'Request body must be a non-empty array of records.' });
        }
        const db = this.db;
        let transactionStarted = false;
        try {
            await db.run('BEGIN TRANSACTION');
            transactionStarted = true;
            for (const record of records) {
                const { user_id, timestamp, heart_rate, blood_pressure, notes } = record;
                const notesBuffer = notes ? (typeof notes === 'string' ? Buffer.from(notes, 'utf-8') : notes) : null;
                await db.run(
                    'INSERT INTO records (user_id, timestamp, heart_rate, blood_pressure, notes) VALUES (?, ?, ?, ?, ?)',
                    user_id, timestamp, heart_rate, blood_pressure, notesBuffer
                );
            }
            await db.run('COMMIT');
            res.status(201).json({ message: 'Batch insert successful', count: records.length });
        } catch (error) {
            if (transactionStarted) {
                try {
                    await db.run('ROLLBACK');
                } catch (rollbackError) {
                    console.error('Error during ROLLBACK:', rollbackError);
                }
            }
            const err = error as Error & { code?: string };
            if (err.code === 'SQLITE_CONSTRAINT' && err.message.includes('UNIQUE constraint failed: records.user_id')) {
                return res.status(409).json({ message: 'Conflict: One or more user_ids already exist.' });
            }
            res.status(500).json({ message: 'Batch insert failed', error: err.message });
        }
    }
}