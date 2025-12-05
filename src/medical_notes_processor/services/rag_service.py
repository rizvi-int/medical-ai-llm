from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import Qdrant
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.messages import HumanMessage, SystemMessage
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from typing import List, Dict, Any
import logging

from ..core.config import settings

logger = logging.getLogger(__name__)


class RAGService:
    def __init__(self):
        self.embeddings = OpenAIEmbeddings(api_key=settings.openai_api_key)
        self.llm = ChatOpenAI(
            model=settings.openai_model,
            api_key=settings.openai_api_key,
            temperature=0.0,
        )
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )
        self.qdrant_client = QdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
        )
        self.collection_name = settings.qdrant_collection_name
        self._ensure_collection()

    def _ensure_collection(self):
        try:
            collections = self.qdrant_client.get_collections().collections
            if not any(c.name == self.collection_name for c in collections):
                self.qdrant_client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
                )
                logger.info(f"Created collection: {self.collection_name}")
        except Exception as e:
            logger.error(f"Error ensuring collection: {str(e)}")
            raise

    async def index_documents(self, documents: List[Dict[str, Any]]) -> None:
        try:
            all_chunks = []
            metadatas = []

            for doc in documents:
                chunks = self.text_splitter.split_text(doc["content"])
                all_chunks.extend(chunks)
                for i in range(len(chunks)):
                    metadatas.append({
                        "document_id": doc["id"],
                        "title": doc["title"],
                        "chunk_index": i,
                    })

            if all_chunks:
                vectorstore = Qdrant(
                    client=self.qdrant_client,
                    collection_name=self.collection_name,
                    embeddings=self.embeddings,
                )
                await vectorstore.aadd_texts(texts=all_chunks, metadatas=metadatas)
                logger.info(f"Indexed {len(all_chunks)} chunks from {len(documents)} documents")
        except Exception as e:
            logger.error(f"Error indexing documents: {str(e)}")
            raise

    async def answer_question(self, question: str, top_k: int = 3) -> Dict[str, Any]:
        try:
            vectorstore = Qdrant(
                client=self.qdrant_client,
                collection_name=self.collection_name,
                embeddings=self.embeddings,
            )

            # Retrieve relevant documents
            docs = await vectorstore.asimilarity_search_with_score(question, k=top_k)

            if not docs:
                return {
                    "answer": "No relevant information found in the knowledge base.",
                    "sources": []
                }

            # Prepare context from retrieved documents
            context = "\n\n".join([doc.page_content for doc, _ in docs])

            # Generate answer using LLM
            system_prompt = """You are a helpful medical information assistant.
Answer the question based ONLY on the provided context from medical documents.
If the context doesn't contain enough information to answer, say so clearly.
Be precise and cite specific information from the context."""

            user_prompt = f"""Context from medical documents:
{context}

Question: {question}

Answer:"""

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]

            response = await self.llm.ainvoke(messages)

            # Prepare sources
            sources = [
                {
                    "document_id": doc.metadata.get("document_id"),
                    "title": doc.metadata.get("title"),
                    "chunk_index": doc.metadata.get("chunk_index"),
                    "content_preview": doc.page_content[:200] + "...",
                    "relevance_score": float(score),
                }
                for doc, score in docs
            ]

            return {
                "answer": response.content,
                "sources": sources
            }
        except Exception as e:
            logger.error(f"Error answering question: {str(e)}")
            raise


# Lazy initialization to avoid connection errors on import
rag_service = None


def get_rag_service() -> RAGService:
    global rag_service
    if rag_service is None:
        rag_service = RAGService()
    return rag_service
