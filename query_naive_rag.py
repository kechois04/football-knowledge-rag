"""
Module d'interrogation et de génération pour le Naive RAG.
1. Charge l'index FAISS et les métadonnées (naive_rag_index/).
2. Effectue la recherche vectorielle (Top-K chunks les plus proches sémantiquement).
3. Génère la réponse avec le LLM via Groq :
   - Principal : Qwen 3.8 27B (rapide, bon en français)
   - Fallback  : OpenAI GPT-OSS 120B (plus puissant)
   - Mode secours : Affiche les chunks récupérés même sans clé API !
"""

import os
import sys
import pickle
import faiss
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

# Charger automatiquement les clés depuis le fichier .env
load_dotenv()

# Sécuriser l'encodage du terminal Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ================= Configuration =================
INDEX_DIR = "naive_rag_index"
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_TOP_K = 4
FAISS_POOL_SIZE = 50          # Pool élargi de candidats FAISS pour le re-ranking hybride
KEYWORD_BOOST = 0.30          # Bonus de score pour les chunks dont l'entité apparaît dans la requête

# Clés d'API (lues depuis les variables d'environnement ou saisies ici)
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
# Modèles Groq disponibles (par ordre de préférence)
GROQ_MODEL_PRIMARY = "qwen/qwen3.8-27b"       # Rapide, bon en français
GROQ_MODEL_FALLBACK = "openai/gpt-oss-120b"   # Plus puissant, fallback
# =================================================


class NaiveRAG:
    def __init__(self, index_dir: str = INDEX_DIR):
        print("Chargement du modèle d'embedding et de l'index FAISS...")
        self.embedder = SentenceTransformer(EMBEDDING_MODEL_NAME)
        
        faiss_path = os.path.join(index_dir, "faiss_index.bin")
        meta_path = os.path.join(index_dir, "chunks_metadata.pkl")

        if not os.path.exists(faiss_path) or not os.path.exists(meta_path):
            raise FileNotFoundError(
                f"Index introuvable dans '{index_dir}'. Exécutez d'abord 'python index_naive_rag.py'."
            )

        self.index = faiss.read_index(faiss_path)
        with open(meta_path, "rb") as f:
            self.metadata = pickle.load(f)

        # Index inversé nom_entité → [indices de chunks] pour la recherche hybride
        self._entity_index = {}
        for idx, meta in enumerate(self.metadata):
            name = meta.get("entity_name", "").strip().lower()
            if name:
                self._entity_index.setdefault(name, []).append(idx)

        print(f"Naive RAG prêt : {self.index.ntotal} chunks indexés, "
              f"{len(self._entity_index)} entités distinctes.\n")

    def _find_keyword_matches(self, query: str) -> set[int]:
        """Trouve les indices de chunks dont le nom d'entité apparaît dans la requête."""
        query_lower = query.lower()
        query_words = [w for w in query_lower.split() if len(w) >= 4]
        matched = set()

        for name_lower, chunk_indices in self._entity_index.items():
            # 1. Le nom complet de l'entité est dans la requête
            #    Ex: "pedri" in "dans quel club joue pedri" → True
            if len(name_lower) > 3 and name_lower in query_lower:
                matched.update(chunk_indices)
                continue
            # 2. Un mot significatif de la requête est dans le nom de l'entité
            #    Ex: mot "messi" in "lionel messi" → True
            for word in query_words:
                if word in name_lower:
                    matched.update(chunk_indices)
                    break

        return matched

    def retrieve(self, query: str, top_k: int = DEFAULT_TOP_K) -> list[dict]:
        """Recherche hybride : FAISS (similarité sémantique) + mots-clés (noms d'entités)."""
        query_vector = self.embedder.encode([query], normalize_embeddings=True).astype("float32")

        # 1. Recherche FAISS dans un pool élargi
        scores, indices = self.index.search(query_vector, FAISS_POOL_SIZE)
        candidates = {}
        for rank, idx in enumerate(indices[0]):
            if idx != -1 and idx < len(self.metadata):
                candidates[int(idx)] = float(scores[0][rank])

        # 2. Trouver les chunks dont l'entité est mentionnée dans la requête
        keyword_hits = self._find_keyword_matches(query)

        # 3. Ajouter les chunks keyword-match absents du pool FAISS (calcul du score réel)
        for cid in keyword_hits:
            if cid not in candidates:
                vec = self.index.reconstruct(int(cid)).reshape(1, -1)
                score = float((query_vector @ vec.T)[0, 0])
                candidates[cid] = score

        # 4. Re-ranking hybride : score FAISS + bonus si l'entité est mentionnée
        ranked = []
        for idx, faiss_score in candidates.items():
            boost = KEYWORD_BOOST if idx in keyword_hits else 0.0
            ranked.append((idx, faiss_score + boost, faiss_score))
        ranked.sort(key=lambda x: x[1], reverse=True)

        # 5. Retourner les top_k résultats avec le score FAISS original
        results = []
        for idx, _hybrid_score, original_score in ranked[:top_k]:
            item = self.metadata[idx].copy()
            item["score"] = original_score
            results.append(item)
        return results

    def generate_with_groq(self, query: str, context: str, api_key: str, model: str = None) -> tuple[str, str]:
        """Appel à Groq avec le modèle spécifié. Essaie le modèle principal puis le fallback."""
        from groq import Groq
        client = Groq(api_key=api_key)

        prompt = f"""Tu es un assistant expert en football pour un projet universitaire.
Réponds à la question de manière précise, concise et factuelle en français en t'appuyant STRICTEMENT sur le CONTEXTE fourni ci-dessous.
Si le contexte ne contient pas l'information ou est incomplet, indique clairement les limites des données trouvées.

=== CONTEXTE RÉCUPÉRÉ (NAIVE RAG) ===
{context}

=== QUESTION DE L'UTILISATEUR ===
{query}

=== RÉPONSE STRUCTURÉE :"""

        # Essayer le modèle principal, puis le fallback
        models_to_try = [GROQ_MODEL_PRIMARY, GROQ_MODEL_FALLBACK]
        if model:
            models_to_try = [model]

        for m in models_to_try:
            try:
                completion = client.chat.completions.create(
                    model=m,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2,
                    max_tokens=600,
                )
                answer = completion.choices[0].message.content.strip()
                return answer, f"Groq ({m})"
            except Exception as e:
                last_error = f"[Erreur Groq ({m})] : {e}"
                continue

        return last_error, "Groq (Échec)"

    def ask(self, query: str, top_k: int = DEFAULT_TOP_K) -> dict:
        """Exécute le pipeline complet Naive RAG : Retrieval + Synthèse."""
        chunks = self.retrieve(query, top_k=top_k)

        # Construction du contexte assemblé
        context_parts = []
        for i, c in enumerate(chunks, start=1):
            context_parts.append(f"[Source {i} - {c['entity_name']} ({c['entity_type']}) - Score: {c['score']:.3f}]\n{c['raw_text']}")
        context_text = "\n\n".join(context_parts)

        # Génération LLM via Groq
        answer = ""
        api_used = "Aucun (Mode affichage des sources)"
        if GROQ_API_KEY:
            answer, api_used = self.generate_with_groq(query, context_text, GROQ_API_KEY)
        else:
            answer = (
                "[Information] Aucune clé API configurée (GROQ_API_KEY dans .env).\n"
                "Les chunks les plus pertinents ci-dessous ont bien été récupérés par le Vector Store."
            )

        return {
            "query": query,
            "answer": answer,
            "api_used": api_used,
            "retrieved_chunks": chunks,
        }


def main():
    rag = NaiveRAG()

    print("=" * 65)
    print("      ASSISTANT NAIVE RAG FOOTBALL (Mode Interactif)")
    print("      Posez directement vos questions (ou 'exit' pour quitter)")
    print("=" * 65)

    while True:
        try:
            user_q = input("\n⚽ Votre question : ").strip()
            if not user_q or user_q.lower() in ["exit", "quit", "q"]:
                print("\nFin de la session Naive RAG. À bientôt !")
                break

            print("\n🔍 Recherche vectorielle et génération en cours...")
            res = rag.ask(user_q, top_k=4)

            print(f"\n🤖 Réponse ({res['api_used']}) :\n{res['answer']}")
            print("\n📚 Sources Wikipédia extraites (Top-4) :")
            for idx, c in enumerate(res["retrieved_chunks"], 1):
                print(f"   [{idx}] {c['entity_name']} ({c['entity_type']}) | Score cosinus : {c['score']:.4f}")
                print(f"       Extrait : {c['raw_text'][:140].replace('\n', ' ')}...")
            print("-" * 65)
        except (KeyboardInterrupt, EOFError):
            print("\nInterruption.")
            break


if __name__ == "__main__":
    main()
