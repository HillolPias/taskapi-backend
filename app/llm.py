from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

from app.config import settings

llm = ChatGoogleGenerativeAI(
    model="gemini-flash-latest", google_api_key=settings.google_api_key
)

embeddings = GoogleGenerativeAIEmbeddings(
    model="models/gemini-embedding-001",
    google_api_key=settings.google_api_key,
)
