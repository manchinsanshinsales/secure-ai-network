import sqlite3
import os
import numpy as np

DB_FILE = "rag_database.db"

def get_connection():
    """Returns a SQLite connection with foreign keys enabled."""
    conn = sqlite3.connect(DB_FILE)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def initialize_db():
    """Creates the tables if they do not exist."""
    with get_connection() as conn:
        # Create documents table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT UNIQUE,
                file_path TEXT,
                file_size INTEGER,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        # Create chunks table with embedding BLOB
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER,
                chunk_index INTEGER,
                text TEXT,
                embedding BLOB,
                FOREIGN KEY (document_id) REFERENCES documents (id) ON DELETE CASCADE
            );
        """)
        conn.commit()

def add_document(filename, file_path, file_size):
    """Inserts a document metadata and returns its ID."""
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO documents (filename, file_path, file_size) VALUES (?, ?, ?)",
                (filename, file_path, file_size)
            )
            conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            # If document already exists, we will overwrite it by deleting and re-inserting
            cursor.execute("DELETE FROM documents WHERE filename = ?", (filename,))
            cursor.execute(
                "INSERT INTO documents (filename, file_path, file_size) VALUES (?, ?, ?)",
                (filename, file_path, file_size)
            )
            conn.commit()
            return cursor.lastrowid

def add_chunks(document_id, chunks_data):
    """Inserts multiple chunks. 
    chunks_data is a list of tuples: (chunk_index, text, embedding_numpy_array)
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        insert_data = []
        for index, text, embedding in chunks_data:
            # Serialize embedding numpy array to bytes
            emb_bytes = np.array(embedding, dtype=np.float32).tobytes()
            insert_data.append((document_id, index, text, emb_bytes))
            
        cursor.executemany(
            "INSERT INTO chunks (document_id, chunk_index, text, embedding) VALUES (?, ?, ?, ?)",
            insert_data
        )
        conn.commit()

def get_all_documents():
    """Returns a list of all documents."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, filename, file_path, file_size, added_at FROM documents ORDER BY added_at DESC")
        return cursor.fetchall()

def delete_document(document_id):
    """Deletes a document and its chunks cascadingly."""
    with get_connection() as conn:
        conn.execute("DELETE FROM documents WHERE id = ?", (document_id,))
        conn.commit()

def get_all_chunks_for_search():
    """Returns a list of all chunks for vector comparison.
    Format: list of tuples (chunk_id, doc_filename, text, embedding_numpy_array)
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT c.id, d.filename, c.text, c.embedding 
            FROM chunks c
            JOIN documents d ON c.document_id = d.id
        """)
        results = []
        for chunk_id, filename, text, emb_bytes in cursor.fetchall():
            # Deserialize embedding bytes back to numpy array
            embedding = np.frombuffer(emb_bytes, dtype=np.float32)
            results.append((chunk_id, filename, text, embedding))
        return results
