import { Buffer } from 'buffer';

export interface RecordEntry {
    user_id: string;
    timestamp: number;
    heart_rate: number;
    blood_pressure: string;
    notes?: Buffer | string; // notes can be a Buffer (BLOB) or string for input
}