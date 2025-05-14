import sqlite3 from 'sqlite3';
import { open, Database } from 'sqlite';

const DB_FILE = process.env.DB_FILE || 'secure.db';
const DB_KEY = process.env.DB_KEY; // IMPORTANT: Use a strong, unique key and manage it securely

let db: Database;

export const initDb = async (): Promise<Database> => {
  if (db) {
    return db;
  }

  // Use the custom SQLCipher-enabled sqlite3
  const sqlcipher = sqlite3.verbose();

  db = await open({
    filename: `./${DB_FILE}`,
    driver: sqlcipher.Database
  });

  // Set the encryption key
  await db.run(`PRAGMA key = '${DB_KEY}';`);
  await db.run('PRAGMA journal_mode = WAL;');
  // Test the key (optional, but good for verification)
  await db.run('PRAGMA cipher_version;');
  console.log('SQLCipher database initialized and key set.');

  // Create table if it doesn't exist
  await db.exec(`
    CREATE TABLE IF NOT EXISTS records (
      user_id TEXT NOT NULL,
      timestamp INTEGER NOT NULL,
      heart_rate INTEGER NOT NULL,
      blood_pressure TEXT NOT NULL,
      notes BLOB,
      PRIMARY KEY(user_id)
    );
  `);
  console.log('Table "records" ensured.');

  return db;
};

export const getDb = (): Database => {
  if (!db) {
    throw new Error('Database not initialized. Call initDb first.');
  }
  return db;
};