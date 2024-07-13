from typing import Any, AsyncIterator
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.vectorstores import Chroma
import os
import vertexai
from langchain_community.document_loaders import S3DirectoryLoader
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.prompts.chat import MessagesPlaceholder
from langchain_google_vertexai import ChatVertexAI
from langchain_openai import ChatOpenAI
from langchain.chains import create_history_aware_retriever
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.chat_message_histories.redis import RedisChatMessageHistory
from chromadb.errors import InvalidDimensionException
from server.prompts import contextualize_q_system_prompt, system_prompt
import logging

logger = logging.getLogger("Langchain")

class LangchainHandler:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(LangchainHandler, cls).__new__(cls, *args, **kwargs)
        return cls._instance
    
    def __init__(self, *args, **kwargs):
        if not hasattr(self, '_initialized'):
            logger.info("Initializing model and embeddings")
            logger.debug(f"Loaded prompts: {contextualize_q_system_prompt} and \n\nSystem:{system_prompt}")
            self._load_model()
            self._load_pdfs()
            self._load_embedding()
            self._split_documents()
            self._create_retriever()
            self._initialize_prompt_context()
            self._initialized = True

    def _load_model(self):
        #vertexai.init(project=os.environ.get("PROJECT"), location=os.environ.get("LOCATION"))
        self.model = ChatOpenAI(model=os.environ.get("CHAT_MODEL"),
                temperature=0,
                max_tokens=4000)
        logger.debug(f"Created model {self.model}")

    def _load_pdfs(self):
        docs_pdf = S3DirectoryLoader(os.environ.get("S3_BUCKET", "sebampuerombucket"), prefix="doc")
        docs = docs_pdf.load()
        logger.debug(f"Read documents: {docs}")
        self.docs = docs

    def _load_embedding(self):
        self.embedding = OllamaEmbeddings(
            model=os.environ.get("EMBED_MODEL", "nomic-embed-text")
        )
    
    def _split_documents(self):
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=int(os.environ.get("CHUNK_SIZE", "3000")), 
            chunk_overlap=int(os.environ.get("CHUNK_OVERLAP", "2000")))
        self.splits = text_splitter.split_documents(self.docs)

    def _create_retriever(self):
        try:
            vector_store = Chroma.from_documents(documents=self.splits, embedding=self.embedding)
        except InvalidDimensionException:
            Chroma().delete_collection()
            vector_store = Chroma.from_documents(documents=self.splits, embedding=self.embedding)
        self.retriever = vector_store.as_retriever(search_type="mmr",
            search_kwargs={'k': 6, 'lambda_mult': 0.25})
        
    def _initialize_prompt_context(self):
        def get_session_history(session_id: str) -> RedisChatMessageHistory:
            return RedisChatMessageHistory(session_id, url=os.environ.get("REDIS_ADDR", "redis://192.168.0.21:6379/0"))
        contextualize_q_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", contextualize_q_system_prompt),
                MessagesPlaceholder("chat_history"),
                ("human", "{input}"),
            ]
        )
        history_aware_retriever = create_history_aware_retriever(
            self.model, self.retriever, contextualize_q_prompt
        )
        qa_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
                MessagesPlaceholder("chat_history"),
                ("human", "{input}"),
            ]
        )
        logger.debug(f"Created qa_prompt {qa_prompt}")
        question_answer_chain = create_stuff_documents_chain(self.model, qa_prompt)
        rag_chain = create_retrieval_chain(history_aware_retriever, question_answer_chain)
        self.conversational_rag_chain = RunnableWithMessageHistory(
            rag_chain,
            get_session_history,
            input_messages_key="input",
            history_messages_key="chat_history",
            output_messages_key="answer",
        )

    async def prompt(self, input: str, session_id: str) -> AsyncIterator[Any]:
        logger.debug(f"Calling rag with session_id {session_id}")
        return self.conversational_rag_chain.astream({"input": input},
                    config={
                        "configurable": {"session_id": session_id}
                    })
