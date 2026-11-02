import os
from typing import List
from langchain_core.documents import Document
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

PDF_FILE_PATH = "preferences.md"
CHROMA_PERSIST_DIR = "chroma_db"
COLLECTION_NAME = "commute_preferences"
MODEL_LOCAL_PATH = "./models/all-MiniLM-L6-v2"

class PreferenceRetriever:
    def __init__(self, file_path : str = PDF_FILE_PATH, persist_dir : str = CHROMA_PERSIST_DIR) :
        self.file_path = file_path
        self.persist_dir = persist_dir
        self.embeddings = HuggingFaceEmbeddings(model_name = MODEL_LOCAL_PATH)
        self.vector_store = self._init_vector_store()
        
    def _init_vector_store(self) -> Chroma : 
        if os.path.exists(self.persist_dir) and os.listdir(self.persist_dir):
            return Chroma(
                collection_name=COLLECTION_NAME,
                embedding_function=self.embeddings,
                persist_directory=self.persist_dir
            )
        if not os.path.exists(self.file_path):
            raise FileNotFoundError()
        
        loader = TextLoader(self.file_path)
        raw_documents = loader.load()
        
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size = 150, chunk_overlap = 30
        )
        
        split_docs = text_splitter.split_documents(raw_documents)
        return Chroma.from_documents(
            documents=split_docs,
            embedding=self.embeddings,
            collection_name=COLLECTION_NAME,
            persist_directory=self.persist_dir
        )
        
    def retrieve(self, query : str, top_k : int = 2) -> List[Document] :
        retriever = self.vector_store.as_retriever(
            search_type = "similarity",
            search_kwargs = {"k" : top_k}
        )
        return retriever.invoke(query)
    
if __name__ == "__main__" :
    retriever = PreferenceRetriever()
    query = "Heavy rain is expected during exam time, what transport to take?"
    results = retriever.retrieve(query, top_k = 3)
    
    for idx, doc in enumerate(results) :
        print(doc.page_content)