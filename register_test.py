import os
import sys

# Ensure 'app' module can be loaded
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import app.rag as rag
import app.database as db

def main():
    print("Initializing Database...")
    db.initialize_db()
    
    test_file = "test_document.txt"
    if not os.path.exists(test_file):
        print(f"Error: {test_file} not found.")
        sys.exit(1)
        
    print(f"Registering '{test_file}' to local database...")
    try:
        chunks = rag.register_document_to_rag(test_file)
        print(f"Successfully registered. Generated {chunks} chunks.")
        
        # Verify db contents
        docs = db.get_all_documents()
        print("Current indexed documents:")
        for doc in docs:
            print(f" - ID: {doc[0]}, Name: {doc[1]}, Size: {doc[3]} bytes")
    except Exception as e:
        print(f"Failed to register: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
