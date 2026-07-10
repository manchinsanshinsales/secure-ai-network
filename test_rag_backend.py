import os
import sys

# Ensure parent path resolution works
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import app.rag as rag
import app.database as db
from app.main import parse_thinking_and_answer

def run_integration_test():
    print("=== STARTING INTEGRATION TEST ===")
    
    # 1. Check database and document ingestion
    print("\n1. Checking indexed documents in SQLite...")
    docs = db.get_all_documents()
    if not docs:
        print("[-] Error: No indexed documents found. Expected test_document.txt.")
        sys.exit(1)
    
    for doc in docs:
        print(f"[+] Found Document ID: {doc[0]}, Name: {doc[1]}, Size: {doc[3]} bytes")
        
    # 2. Test Vector Similarity Retrieve
    query = "RAG Studioの秘密のコードワードは何ですか？"
    print(f"\n2. Testing vector retrieval for query: '{query}'...")
    sources = rag.retrieve_context_chunks(query, top_k=1)
    
    if not sources:
        print("[-] Error: No matching context chunks retrieved.")
        sys.exit(1)
        
    best_match = sources[0]
    print(f"[+] Best Match Document: {best_match['filename']}")
    print(f"[+] Similarity Score: {best_match['score']:.4f}")
    print(f"[+] Context Snippet:\n---\n{best_match['text']}\n---")
    
    if "test_document.txt" not in best_match['filename']:
        print("[-] Error: Retrieve did not match the expected test document.")
        sys.exit(1)
        
    # 3. Test LLM Generation with Retrieval (Streaming)
    print("\n3. Testing LLM query stream and thinking parsing...")
    try:
        stream = rag.query_rag_stream(query, top_k=1)
        accumulated_text = ""
        citations = []
        
        for item in stream:
            if item["type"] == "sources":
                citations = item["sources"]
            elif item["type"] == "token":
                # Print token-by-token to standard out for visual verification
                sys.stdout.write(item["content"])
                sys.stdout.flush()
                accumulated_text += item["content"]
                
        print("\n\n[+] Stream completed.")
        
        # 4. Parse the completed response
        thinking, final_answer = parse_thinking_and_answer(accumulated_text)
        
        print("\n=== PARSED RESULTS ===")
        if thinking:
            print(f"[+] Thinking Process:\n{thinking}\n")
        else:
            print("[*] No <thinking> block outputted by LLM (or thinking tags not found).")
            
        print(f"[+] Final Answer:\n{final_answer}\n")
        
        # 5. Validation Assertions
        assert "ONPREM_RAG_SUCCESS_999" in final_answer, "Secret codeword missing from final answer!"
        assert len(citations) > 0, "No cited sources returned!"
        print("[+++] ALL ASSERTIONS PASSED! RAG BACKEND INTEGRATION SUCCESSFUL!")
        
    except Exception as e:
        print(f"\n[-] Integration test failed with error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_integration_test()
