import faiss, numpy as np
from sentence_transformers import SentenceTransformer

class EmbedIndex:
    """
    A heper class to embed, store in flat index and perform nearest serach 
    this is highly effective and fast approach when working with huge dataset
    helps to find: 
    - antonyms 
    - synonyms to all homographs
    We've used 
    """
    def __init__(self, model_name="sentence-transformers/all-MiniLM-L6-v2"):
        """
        model_name: what sentence-transformer model to load and use for embedding (default: MiniLM)
        MiniLM - exaplin why it's good here! 
        init loads and creates a FAISS index to store the vectors and simplify working with them
        """
        self.model = SentenceTransformer(model_name)
        self.dim = self.model.get_sentence_embedding_dimension() # dimension for embeddings, depends on the model
        self.index = faiss.IndexHNSWFlat(self.dim, 32)  # switch to FlatIP for <=100k
        # if we have less than 100k words we can use IndexFlatIP - which is exact search -> more accurate.
        # IndexHNSWFlat is still very accurate but it's approx - graph based 
        # 32 responds for how many connections we want between the nodes,
        # meaning that each embedded vector connects to 32 nearest words
        # if we want to prepare for milion of words (IMO overkill) we can use index_factory("IVF4096,HNSW32,Flat") - clustering + grpah based
        self.items = []
        self.vecs = None

    # embeds all words in corpus and stores them in faiss index 
    def build(self, items):
        # items is a list of words 
        # note: we need to build the corpus (from topfreq, wikipedia etc.)
        self.items = items
        V = self.model.encode(items, normalize_embeddings=True, convert_to_numpy=True).astype("float32")
        self.vecs = V
        self.index.add(V)

    # performs a faiss search based on the architecture we'll decide to choose:) 
    def search(self, queries, k=200):
        # query is a "target" word, word we generate list of close words to
        Q = self.model.encode(queries, normalize_embeddings=True, convert_to_numpy=True).astype("float32")
        sims, idxs = self.index.search(Q, k)
        return sims, idxs  
