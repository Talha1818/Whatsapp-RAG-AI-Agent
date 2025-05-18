from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse

from langchain_community.document_loaders import PyPDFLoader
from langchain.embeddings import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.vectorstores import InMemoryVectorStore
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq

import os

# -------------------------------
# 1. Environment setup
# -------------------------------
os.environ["GROQ_API_KEY"] = "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"  # Replace with your real key

# -------------------------------
# 2. Load and split documents
# -------------------------------
def load_documents(file_path):
    loader = PyPDFLoader(file_path)
    pages = loader.lazy_load()
    return pages

def split_documents(pages):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    return text_splitter.split_documents(pages)

# -------------------------------
# 3. Build vectorstore
# -------------------------------
def build_vectorstore(documents):
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    return InMemoryVectorStore.from_documents(documents=documents, embedding=embeddings)

# -------------------------------
# 4. Create RAG chain
# -------------------------------
def create_rag_chain(vectorstore):
    retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 3})
    
    llm = ChatGroq(model="llama3-8b-8192")

    system_prompt = (
        "You are an assistant for question-answering tasks. "
        "Use the following pieces of retrieved context to answer "
        "the question. If you don't know the answer, say that you "
        "don't know. Use three sentences maximum and keep the "
        "answer concise.\n\n{context}"
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{input}")
    ])

    question_answer_chain = create_stuff_documents_chain(llm, prompt)
    return create_retrieval_chain(retriever, question_answer_chain)

# -------------------------------
# 5. Answer user questions
# -------------------------------
def answer_question(rag_chain, query):
    result = rag_chain.invoke({"input": query})
    return result.get("answer", "Sorry, I don't know the answer.")

# -------------------------------
# 6. Flask App Setup
# -------------------------------
app = Flask(__name__)

# Load documents and initialize everything once at startup
documents = split_documents(load_documents("LIst-of-countries-and-capitals-and-currency.pdf"))
vectorstore = build_vectorstore(documents)
rag_chain = create_rag_chain(vectorstore)

@app.route("/", methods=["POST"])
def bot():
    user_msg = request.values.get('Body', '').strip()
    response = MessagingResponse()

    answer = answer_question(rag_chain, user_msg)
    response.message(answer)

    return str(response)

# -------------------------------
# 7. Run the app
# -------------------------------
if __name__ == "__main__":
    app.run(debug=True)
