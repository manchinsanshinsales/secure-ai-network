import os
import requests
import json
import numpy as np
from pypdf import PdfReader
import app.database as db

OLLAMA_URL = "http://127.0.0.1:11434"
DEFAULT_LLM = "gemma4:12b"
DEFAULT_EMBED = "nomic-embed-text"

def extract_text_from_file(file_path):
    """Extracts raw text from PDF, TXT, or MD files."""
    _, ext = os.path.splitext(file_path.lower())
    
    if ext == ".pdf":
        text = ""
        reader = PdfReader(file_path)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text
    elif ext in [".txt", ".md"]:
        # Try UTF-8 first, fallback to Shift-JIS (common in Windows Japanese environments)
        for encoding in ["utf-8", "shift_jis", "cp932"]:
            try:
                with open(file_path, "r", encoding=encoding) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue
        raise ValueError(f"Failed to decode text file: {file_path} with common encodings.")
    else:
        raise ValueError(f"Unsupported file type: {ext}")

def split_text_into_chunks(text, chunk_size=500, chunk_overlap=100):
    """Splits text into overlapping chunks recursively or character-wise."""
    chunks = []
    text = text.strip()
    if not text:
        return chunks
        
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start += chunk_size - chunk_overlap
        
        # Avoid infinite loops or empty chunks
        if chunk_size <= chunk_overlap:
            break
            
    return chunks

def get_ollama_embedding(text, model=DEFAULT_EMBED):
    """Fetches embedding vector from local Ollama API."""
    url = f"{OLLAMA_URL}/api/embed"
    payload = {
        "model": model,
        "input": text
    }
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        data = response.json()
        embeddings = data.get("embeddings", [])
        if embeddings:
            return embeddings[0]
    raise Exception(f"Failed to fetch embedding: {response.text}")

def register_document_to_rag(file_path):
    """Extracts, chunks, embeds, and saves document to the local SQLite database."""
    filename = os.path.basename(file_path)
    file_size = os.path.getsize(file_path)
    
    # 1. Extract text
    text = extract_text_from_file(file_path)
    
    # 2. Split into chunks
    chunks = split_text_into_chunks(text)
    if not chunks:
        return 0
        
    # 3. Add to documents table
    doc_id = db.add_document(filename, file_path, file_size)
    
    # 4. Generate embeddings and add to chunks table
    chunks_data = []
    for idx, chunk in enumerate(chunks):
        embedding = get_ollama_embedding(chunk)
        chunks_data.append((idx, chunk, embedding))
        
    db.add_chunks(doc_id, chunks_data)
    return len(chunks)

def calculate_cosine_similarity(vec_a, vec_b):
    """Helper to calculate cosine similarity between two numpy arrays."""
    norm_a = np.linalg.norm(vec_a)
    norm_b = np.linalg.norm(vec_b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return np.dot(vec_a, vec_b) / (norm_a * norm_b)

def retrieve_context_chunks(query, top_k=3, embed_model=DEFAULT_EMBED):
    """Retrieves top-K similar chunks from database for the query."""
    # 1. Fetch query vector
    query_vector = np.array(get_ollama_embedding(query, embed_model), dtype=np.float32)
    
    # 2. Fetch all candidates from database
    all_chunks = db.get_all_chunks_for_search()
    if not all_chunks:
        return []
        
    # 3. Score similarities
    scored_chunks = []
    for chunk_id, filename, text, emb_vec in all_chunks:
        similarity = calculate_cosine_similarity(query_vector, emb_vec)
        scored_chunks.append({
            "chunk_id": chunk_id,
            "filename": filename,
            "text": text,
            "score": float(similarity)
        })
        
    # 4. Sort and pick top K
    scored_chunks.sort(key=lambda x: x["score"], reverse=True)
    return scored_chunks[:top_k]

def query_rag_stream(query, system_prompt=None, top_k=3, llm_model=DEFAULT_LLM):
    """Generator yielding LLM tokens with context retrieval.
    Yields dicts with format: {'type': 'chunk'|'thinking'|'text', 'content': str} 
    or {'type': 'sources', 'sources': [...]}
    """
    # 1. Retrieve context
    sources = retrieve_context_chunks(query, top_k=top_k)
    yield {"type": "sources", "sources": sources}
    
    context_str = ""
    if sources:
        context_str = "\n---\n".join([f"[Source: {s['filename']}]\n{s['text']}" for s in sources])
        
    # 2. Construct prompt
    if not system_prompt:
        system_prompt = (
            "あなたはオンプレ環境で動作する優秀なAIアシスタントです。"
            "提供された[コンテキスト]情報を基に、ユーザーからの質問に正確かつ丁寧に回答してください。"
            "提供されたコンテキストに回答が含まれていない場合は、「提供されたドキュメントからは回答を見つけることができませんでした」という旨を伝えてください。"
            "外部のインターネット情報や不確実な知識を無条件に付け足すことは避けてください。"
        )
        
    user_prompt = f"""以下の[コンテキスト]情報を参照して、[質問]に答えてください。

[コンテキスト]
{context_str}

[質問]
{query}
"""

    # 3. Stream from Ollama
    url = f"{OLLAMA_URL}/api/chat"
    payload = {
        "model": llm_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "stream": True
    }
    
    response = requests.post(url, json=payload, stream=True)
    if response.status_code != 200:
        raise Exception(f"Failed to query LLM: {response.text}")
        
    # Gemma 4 streams tokens. It may output thinking block <thinking> ... </thinking>
    # We will yield tags and content so the frontend can isolate thinking processes.
    in_thinking = False
    
    for line in response.iter_lines():
        if not line:
            continue
            
        try:
            chunk_data = json.loads(line.decode("utf-8"))
            token = chunk_data.get("message", {}).get("content", "")
            
            # Simple token tracking for thinking block tags
            # We look for <thinking> or </thinking>
            # Note: Streaming tokens might split <thinking> into multiple tokens (e.g., '<', 'thinking', '>').
            # To handle this cleanly, we can yield tokens directly, and let the frontend do the buffer parsing,
            # OR we maintain a small token buffer here.
            # Let's keep it simple: we yield raw tokens, but also try to identify tags if they come in one piece or simple chunks.
            # Actually, parsing streaming XML-like tags is more robust on the frontend/ui side,
            # but we can yield the token and let UI parse it. 
            # To make it easiest for the UI, let's just pass the raw text token and the UI will parse '<thinking>' blocks.
            yield {"type": "token", "content": token}
            
        except Exception as e:
            # Skip invalid JSON or decoding errors
            continue

def check_ollama_status(llm_model=DEFAULT_LLM, embed_model=DEFAULT_EMBED):
    """Checks if Ollama is running and the required models are pulled.
    Returns:
        (connection_ok, missing_models) where:
        - connection_ok: bool
        - missing_models: list of missing model names
    """
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=3)
        if response.status_code != 200:
            return False, [llm_model, embed_model]
        
        data = response.json()
        available_models = []
        for m in data.get("models", []):
            name = m.get("name", "")
            available_models.append(name)
            
        def has_model(target):
            # Check for exact match or strip tag (e.g. nomic-embed-text:latest vs nomic-embed-text)
            target_base = target.split(":")[0]
            for am in available_models:
                am_base = am.split(":")[0]
                if am == target or am_base == target or am_base == target_base:
                    return True
            return False
            
        missing = []
        if not has_model(llm_model):
            missing.append(llm_model)
        if not has_model(embed_model):
            missing.append(embed_model)
            
        return True, missing
    except requests.exceptions.RequestException:
        return False, [llm_model, embed_model]
