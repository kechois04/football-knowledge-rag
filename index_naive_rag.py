"""
Indexation du Naive RAG (Vector Store FAISS + Sentence-Transformers).
1. Parcourt les articles de corpus_wikipedia/ (172 clubs + 1 351 joueurs).
2. Découpe chaque article en chunks de ~800 caractères avec recouvrement.
3. Préfixe chaque chunk avec son entité [Entité : Nom | Type] (Contextual Chunking).
4. Calcule les embeddings avec all-MiniLM-L6-v2 (local, rapide, 384 dimensions).
5. Construit et persiste l'index FAISS dans le dossier naive_rag_index/.
"""

import os
import sys
import glob
import pickle
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

# Sécuriser l'encodage du terminal Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ================= Configuration =================
CORPUS_DIR = "corpus_wikipedia"
INDEX_DIR = "naive_rag_index"
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

CHUNK_SIZE = 800       # Taille cible d'un chunk en caractères
CHUNK_OVERLAP = 120    # Recouvrement entre chunks consécutifs
BATCH_SIZE = 128       # Taille des lots pour l'encodage vectoriel
# =================================================


def parse_wikipedia_file(file_path: str) -> tuple[dict, str]:
    """Extrait les métadonnées de l'en-tête et le contenu textuel d'un fichier."""
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()

    parts = text.split("=== CONTENU", 1)
    header = parts[0]
    content = ""
    if len(parts) > 1:
        # Supprime le marqueur "=== CONTENU INTÉGRAL ===" ou "=== CONTENU ==="
        content = parts[1].split("===\n", 1)[-1].strip()

    metadata = {
        "id": "",
        "type": "Inconnu",
        "name": "",
        "url": "",
    }

    for line in header.split("\n"):
        line = line.strip()
        if ":" in line:
            key, val = line.split(":", 1)
            key = key.strip().lower()
            val = val.strip()
            if key == "id":
                metadata["id"] = val
            elif key == "type":
                metadata["type"] = val
            elif key == "nom":
                metadata["name"] = val
            elif key == "url":
                metadata["url"] = val

    return metadata, content


def recursive_split_text(text: str, chunk_size: int = 800, overlap: int = 120) -> list[str]:
    """
    Découpeur récursif de texte pur Python (paragraphes -> retours à la ligne -> phrases).
    Évite toute dépendance lourde externe.
    """
    if not text or len(text) <= chunk_size:
        return [text] if text else []

    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        if len(current_chunk) + len(para) + 2 <= chunk_size:
            current_chunk = f"{current_chunk}\n\n{para}" if current_chunk else para
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
                # Conserver un recouvrement de la fin du chunk précédent
                overlap_text = current_chunk[-overlap:] if len(current_chunk) > overlap else current_chunk
                current_chunk = f"{overlap_text}\n\n{para}"
            else:
                # Si le paragraphe seul est plus grand que chunk_size, découper par phrases
                sentences = para.split(". ")
                sub_chunk = ""
                for sent in sentences:
                    sent = sent.strip()
                    if not sent:
                        continue
                    if len(sub_chunk) + len(sent) + 2 <= chunk_size:
                        sub_chunk = f"{sub_chunk}. {sent}" if sub_chunk else sent
                    else:
                        if sub_chunk:
                            chunks.append(sub_chunk.strip() + ".")
                        sub_chunk = sent
                if sub_chunk:
                    current_chunk = sub_chunk

    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks


def build_naive_rag_index():
    os.makedirs(INDEX_DIR, exist_ok=True)

    print("=" * 65)
    print("      CONSTRUCTION DU VECTOR STORE (NAIVE RAG)")
    print("=" * 65)

    # 1. Chargement du modèle d'embedding
    print(f"\n[1/4] Chargement du modèle d'embedding : {EMBEDDING_MODEL_NAME}...")
    embedder = SentenceTransformer(EMBEDDING_MODEL_NAME)
    embedding_dim = embedder.get_sentence_embedding_dimension()
    print(f"      -> Modèle chargé. Dimension des vecteurs : {embedding_dim}")

    # 2. Lecture et chunking de tous les fichiers
    print("\n[2/4] Lecture du corpus et découpage en chunks...")
    file_patterns = [
        os.path.join(CORPUS_DIR, "clubs", "*.txt"),
        os.path.join(CORPUS_DIR, "players", "*.txt"),
    ]

    all_files = []
    for pat in file_patterns:
        all_files.extend(glob.glob(pat))

    print(f"      -> {len(all_files)} fichiers texte détectés dans {CORPUS_DIR}/.")

    all_chunks_text = []
    all_chunks_metadata = []

    for file_path in all_files:
        meta, content = parse_wikipedia_file(file_path)
        if not content or len(content) < 50:
            continue

        raw_chunks = recursive_split_text(content, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP)
        entity_name = meta["name"]
        entity_type = meta["type"]

        for idx, chunk in enumerate(raw_chunks):
            # Contextual chunking : on enrichit chaque chunk avec le nom de l'entité
            enriched_text = f"[Entité: {entity_name} | Type: {entity_type}]\n{chunk}"

            all_chunks_text.append(enriched_text)
            all_chunks_metadata.append({
                "chunk_id": len(all_chunks_metadata),
                "entity_id": meta["id"],
                "entity_name": entity_name,
                "entity_type": entity_type,
                "url": meta["url"],
                "text": enriched_text,
                "raw_text": chunk,
            })

    total_chunks = len(all_chunks_text)
    print(f"      -> {total_chunks} chunks générés au total (moyenne : {total_chunks / len(all_files):.1f} chunks/doc).")

    # 3. Vectorisation par lots (Batch Embedding)
    print(f"\n[3/4] Vectorisation de {total_chunks} chunks (par lots de {BATCH_SIZE})...")
    embeddings = embedder.encode(
        all_chunks_text,
        batch_size=BATCH_SIZE,
        show_progress_bar=True,
        normalize_embeddings=True,  # Normalisation L2 pour recherche par similarité Cosinus directe
        convert_to_numpy=True
    ).astype("float32")

    # 4. Création et sauvegarde de l'index FAISS
    print("\n[4/4] Construction de l'index FAISS (Similarité Cosinus / Inner Product)...")
    index = faiss.IndexFlatIP(embedding_dim)
    index.add(embeddings)

    faiss_path = os.path.join(INDEX_DIR, "faiss_index.bin")
    faiss.write_index(index, faiss_path)

    metadata_path = os.path.join(INDEX_DIR, "chunks_metadata.pkl")
    with open(metadata_path, "wb") as f:
        pickle.dump(all_chunks_metadata, f)

    print("\n" + "=" * 65)
    print("INDEXATION NAIVE RAG TERMINÉE AVEC SUCCÈS !")
    print(f"- Index FAISS : {faiss_path} ({os.path.getsize(faiss_path) / (1024*1024):.2f} Mo)")
    print(f"- Métadonnées : {metadata_path} ({os.path.getsize(metadata_path) / (1024*1024):.2f} Mo)")
    print(f"- Total chunks indexés : {index.ntotal}")
    print("=" * 65)


if __name__ == "__main__":
    build_naive_rag_index()
