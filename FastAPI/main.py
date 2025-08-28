# main.py
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import joinedload
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from datetime import datetime, timedelta
import hashlib
import jwt
import os
import asyncio
import threading
from typing import Optional, List, Dict, Any
import json
from pydantic import BaseModel
import PyPDF2
import io
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from crewai import Agent, Task, Crew, Process
from crewai.tools import BaseTool
import uuid
import uvicorn


# Database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./voiceflow.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Models
class Company(Base):
    __tablename__ = "companies"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    industry = Column(String)
    bucket_id = Column(String, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    users = relationship("User", back_populates="company")
    agents = relationship("AIAgent", back_populates="company")
    documents = relationship("Document", back_populates="company")

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    company_id = Column(Integer, ForeignKey("companies.id"))
    role = Column(String, default="admin")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    company = relationship("Company", back_populates="users")
    sessions = relationship("Session", back_populates="user")

class AIAgent(Base):
    __tablename__ = "agents"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    role = Column(String)
    company_id = Column(Integer, ForeignKey("companies.id"))
    voice_config = Column(JSON)
    personality_config = Column(JSON)
    channels = Column(JSON)
    is_active = Column(Boolean, default=True)
    phone_number = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    company = relationship("Company", back_populates="agents")
    conversations = relationship("Conversation", back_populates="agent")

class Document(Base):
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String)
    content = Column(Text)
    company_id = Column(Integer, ForeignKey("companies.id"))
    bucket_id = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    company = relationship("Company", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document")

class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"))
    content = Column(Text)
    chunk_index = Column(Integer)
    bucket_id = Column(String, index=True)
    
    document = relationship("Document", back_populates="chunks")

class Session(Base):
    __tablename__ = "sessions"
    
    id = Column(String, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    agent_instance_id = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    user = relationship("User", back_populates="sessions")
    conversations = relationship("Conversation", back_populates="session")

class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("sessions.id"))
    agent_id = Column(Integer, ForeignKey("agents.id"))
    message_type = Column(String)  # 'user' or 'agent'
    content = Column(Text)
    chunks_used = Column(JSON)
    prompt_used = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    session = relationship("Session", back_populates="conversations")
    agent = relationship("AIAgent", back_populates="conversations")

class CallLog(Base):
    __tablename__ = "call_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String)
    phone_number = Column(String)
    duration = Column(Integer)
    status = Column(String)
    transcript = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

# Create tables
Base.metadata.create_all(bind=engine)

# Pydantic models
class UserSignup(BaseModel):
    email: str
    password: str
    company_name: str
    industry: str

class UserLogin(BaseModel):
    email: str
    password: str

class CompanyProfile(BaseModel):
    name: str
    industry: str
    use_case: str

class AgentConfig(BaseModel):
    name: str
    role: str
    channels: List[str]
    voice_config: Optional[Dict] = None
    personality_config: Optional[Dict] = None

class KnowledgeUpload(BaseModel):
    urls: Optional[List[str]] = None
    text_content: Optional[str] = None

class VoiceConfig(BaseModel):
    voice_style: str
    personality_tone: str
    language: str

class ChannelConfig(BaseModel):
    phone_enabled: bool
    chat_enabled: bool
    whatsapp_enabled: bool

class MessageInput(BaseModel):
    content: str
    type: str = "text"

# FastAPI app
app = FastAPI(title="VoiceFlow AI Platform", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

# JWT settings
SECRET_KEY = "your-secret-key-here"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# In-memory storage for session agents and retrievers
session_agents = {}
company_retrievers = {}

# CrewAI Tools
class DocumentRetrieverTool(BaseTool):
    name: str = "document_retriever"
    description: str = "Retrieves relevant documents based on query"
    
    def __init__(self, bucket_id: str, db: Session):
        super().__init__()
        self.bucket_id = bucket_id
        self.db = db
    
    def _run(self, query: str) -> str:
        # Get retriever for this bucket
        if self.bucket_id in company_retrievers:
            retriever = company_retrievers[self.bucket_id]
            chunks = retriever.retrieve(query)
            return "\n".join([chunk['content'] for chunk in chunks])
        return "No relevant documents found."

class ActionExecutorTool(BaseTool):
    name: str = "action_executor"
    description: str = "Executes actions like API calls, CRM updates"
    
    def _run(self, action: str, parameters: dict) -> str:
        # Placeholder for actual action execution
        return f"Executed action: {action} with parameters: {parameters}"

class AuditLoggerTool(BaseTool):
    name: str = "audit_logger"
    description: str = "Logs decision rationale and audit trail"
    
    def __init__(self, db: Session):
        super().__init__()
        self.db = db
    
    def _run(self, rationale: str, chunks_used: List[str]) -> str:
        # Log audit information
        return f"Logged audit: {rationale}"

# Simple TF-IDF based retriever
class SimpleRetriever:
    def __init__(self, bucket_id: str, db: Session):
        self.bucket_id = bucket_id
        self.db = db
        self.vectorizer = TfidfVectorizer(stop_words='english', max_features=1000)
        self.tfidf_matrix = None
        self.chunks = []
        self._build_index()
    
    def _build_index(self):
        chunks = self.db.query(DocumentChunk).filter(DocumentChunk.bucket_id == self.bucket_id).all()
        if chunks:
            self.chunks = [{"id": chunk.id, "content": chunk.content} for chunk in chunks]
            contents = [chunk["content"] for chunk in self.chunks]
            self.tfidf_matrix = self.vectorizer.fit_transform(contents)
    
    def retrieve(self, query: str, top_k: int = 3):
        if not self.tfidf_matrix or not self.chunks:
            return []
        
        query_vec = self.vectorizer.transform([query])
        similarities = cosine_similarity(query_vec, self.tfidf_matrix).flatten()
        top_indices = similarities.argsort()[-top_k:][::-1]
        
        return [self.chunks[i] for i in top_indices if similarities[i] > 0.1]

# CrewAI Agent Setup
def create_session_agents(bucket_id: str, db: Session):
    try:
        # Tools
        retriever_tool = DocumentRetrieverTool(bucket_id, db)
        action_tool = ActionExecutorTool()
        audit_tool = AuditLoggerTool(db)
        
        # Agents
        frontline_agent = Agent(
            role="Frontline Assistant",
            goal="Handle customer interactions professionally and efficiently",
            backstory="Expert customer service agent with deep knowledge of company policies",
            tools=[retriever_tool],
            verbose=True,
            allow_delegation=True
        )
        
        retrieval_agent = Agent(
            role="Knowledge Retriever",
            goal="Find and provide relevant information from company documents",
            backstory="Information specialist who excels at finding relevant context",
            tools=[retriever_tool],
            verbose=True
        )
        
        action_agent = Agent(
            role="Action Executor",
            goal="Execute required actions and API calls",
            backstory="System integrator who handles technical operations",
            tools=[action_tool],
            verbose=True
        )
        
        audit_agent = Agent(
            role="Audit Specialist",
            goal="Log all interactions and maintain compliance",
            backstory="Compliance expert who ensures proper documentation",
            tools=[audit_tool],
            verbose=True
        )
        
        return {
            "frontline": frontline_agent,
            "retrieval": retrieval_agent,
            "action": action_agent,
            "audit": audit_agent
        }
    except Exception as e:
        print(f"Error creating CrewAI agents: {e}")
        # Return minimal agents that won't crash
        return {
            "frontline": None,
            "retrieval": None,
            "action": None,
            "audit": None
        }


# def create_session_agents(bucket_id: str, db: Session):
#     try:
#         frontline_agent = Agent(
#             role="Customer Support Agent",
#             goal="Help customers with their questions",
#             backstory="Friendly customer service representative",
#             verbose=False,
#             allow_delegation=False
#         )
#         return {"frontline": frontline_agent}
#     except Exception as e:
#         print(f"CrewAI error: {e}")
#         return {"frontline": None}
    
        
# Helper functions
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        user = db.query(User).filter(User.email == email).first()
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

def extract_text_from_pdf(file_content: bytes) -> str:
    pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text()
    return text

def chunk_text(text: str, chunk_size: int = 500) -> List[str]:
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)
    return chunks

def spawn_session_agent(user_id: int, bucket_id: str, db: Session) -> str:
    session_id = str(uuid.uuid4())
        
    # Create session record
    session = Session(
        id=session_id,
        user_id=user_id,
        agent_instance_id=f"agent_{session_id}"
    )
    db.add(session)
        
    try:
        db.commit()
            
        # Create CrewAI agents
        agents = create_session_agents(bucket_id, db)
        session_agents[session_id] = agents
            
        # Create retriever for bucket if not exists
        if bucket_id not in company_retrievers:
            company_retrievers[bucket_id] = SimpleRetriever(bucket_id, db)
            
        return session_id
    except Exception as e:
        db.rollback()
        print(f"Error creating session: {e}")
        raise

# def run_session_agent(session_id: str, message: str, db: Session) -> str:
#     if session_id not in session_agents:
#         return "Session not found"
        
#     agents = session_agents[session_id]
#     frontline_agent = agents.get("frontline")
        
#     if not frontline_agent:
#         return "I'm here to help! Could you please provide more details?"
        
#     try:
#         task = Task(
#             description=f"Respond professionally to this customer message: {message}",
#             agent=frontline_agent,
#             expected_output="A helpful, professional customer service response"
#         )
            
#         crew = Crew(
#             agents=[frontline_agent],
#             tasks=[task],
#             verbose=False
#         )
            
#         result = crew.kickoff()
#         return str(result)
#     except Exception as e:
#         print(f"CrewAI error: {e}")
#         return "I'm here to help! How can I assist you today?"


def run_session_agent(session_id: str, message: str, db: Session) -> str:
    if session_id not in session_agents:
        return "Session not found"
        
    agents = session_agents[session_id]
        
    # Create a simple task for the frontline agent
    task = Task(
        description=f"Respond to this user message: {message}",
        agent=agents["frontline"],
        expected_output="A helpful response to the user's query"
    )
        
    # Create crew and execute
    crew = Crew(
        agents=[agents["frontline"], agents["retrieval"]],
        tasks=[task],
        process=Process.sequential
    )
        
    try:
        result = crew.kickoff()
        return str(result)
    except Exception as e:
        return f"Error processing message: {str(e)}"



# Routes

# Auth endpoints
@app.post("/auth/signup")
async def signup(user_data: UserSignup, db: Session = Depends(get_db)):
    # Check if user exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create company
    bucket_id = f"bucket_{uuid.uuid4()}"
    company = Company(
        name=user_data.company_name,
        industry=user_data.industry,
        bucket_id=bucket_id
    )
    db.add(company)
    db.flush()
    
    # Create user
    password_hash = hashlib.sha256(user_data.password.encode()).hexdigest()
    user = User(
        email=user_data.email,
        password_hash=password_hash,
        company_id=company.id
    )
    db.add(user)
    db.commit()
    
    access_token = create_access_token({"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer", "user_id": user.id}

@app.post("/auth/login")
async def login(user_data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == user_data.email).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    password_hash = hashlib.sha256(user_data.password.encode()).hexdigest()
    if user.password_hash != password_hash:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Load company relationship explicitly
    company = db.query(Company).filter(Company.id == user.company_id).first()
    if not company:
        raise HTTPException(status_code=500, detail="Company not found")
    
    try:
        # Create session agent
        session_id = spawn_session_agent(user.id, company.bucket_id, db)
    except Exception as e:
        print(f"Session creation error: {e}")
        # Return token without session_id if session creation fails
        access_token = create_access_token({"sub": user.email})
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user_id": user.id,
            "session_id": None,
            "error": "Session creation failed"
        }
    
    access_token = create_access_token({"sub": user.email})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user.id,
        "session_id": session_id
    }
    
    
@app.post("/auth/logout")
async def logout(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Deactivate sessions
    db.query(Session).filter(Session.user_id == current_user.id).update({"is_active": False})
    db.commit()
    return {"message": "Logged out successfully"}

@app.get("/auth/me")
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "company_name": current_user.company.name,
        "role": current_user.role
    }

# Onboarding endpoints
@app.post("/onboarding/company")
async def save_company_profile(
    profile: CompanyProfile,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    company = current_user.company
    company.name = profile.name
    company.industry = profile.industry
    db.commit()
    return {"message": "Company profile updated", "company_id": company.id}

@app.post("/onboarding/agent")
async def create_agent(
    agent_config: AgentConfig,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    agent = AIAgent(
        name=agent_config.name,
        role=agent_config.role,
        company_id=current_user.company_id,
        voice_config=agent_config.voice_config or {},
        personality_config=agent_config.personality_config or {},
        channels=agent_config.channels,
        phone_number=f"+1555{uuid.uuid4().hex[:7]}"
    )
    db.add(agent)
    db.commit()
    return {"message": "Agent created", "agent_id": agent.id}

@app.post("/onboarding/knowledge")
async def upload_knowledge(
    background_tasks: BackgroundTasks,
    knowledge: KnowledgeUpload = None,
    files: List[UploadFile] = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    uploaded_docs = []
    
    try:
        print(f"DEBUG: knowledge object: {knowledge}")
        print(f"DEBUG: files: {files}")
        # Handle file uploads
        if files:
            for file in files:
                content = await file.read()
                
                if file.filename.endswith('.pdf'):
                    text_content = extract_text_from_pdf(content)
                else:
                    text_content = content.decode('utf-8')
                
                # Save document
                document = Document(
                    filename=file.filename,
                    content=text_content,
                    company_id=current_user.company_id,
                    bucket_id=current_user.company.bucket_id
                )
                db.add(document)
                db.commit()
                db.refresh(document)  # Ensure we have the ID
                
                # Chunk and save
                chunks = chunk_text(text_content)
                for i, chunk in enumerate(chunks):
                    doc_chunk = DocumentChunk(
                        document_id=document.id,
                        content=chunk,
                        chunk_index=i,
                        bucket_id=current_user.company.bucket_id
                    )
                    db.add(doc_chunk)
                
                # Commit chunks for this document
                db.commit()
                
                # Add to uploaded docs list after successful processing
                uploaded_docs.append({"id": document.id, "filename": file.filename})
        
        # Handle text content
        if knowledge and knowledge.text_content and knowledge.text_content.strip():
            document = Document(
                filename="text_input.txt",
                content=knowledge.text_content,
                company_id=current_user.company_id,
                bucket_id=current_user.company.bucket_id
            )
            db.add(document)
            db.commit()
            db.refresh(document)  # Ensure we have the ID
            
            chunks = chunk_text(knowledge.text_content)
            for i, chunk in enumerate(chunks):
                doc_chunk = DocumentChunk(
                    document_id=document.id,
                    content=chunk,
                    chunk_index=i,
                    bucket_id=current_user.company.bucket_id
                )
                db.add(doc_chunk)
            
            # Commit chunks for this document
            db.commit()
            
            # Add to uploaded docs list after successful processing
            uploaded_docs.append({"id": document.id, "filename": "text_input.txt"})
        
        # Rebuild retriever index
        if current_user.company.bucket_id in company_retrievers:
            company_retrievers[current_user.company.bucket_id]._build_index()
            
        print(f"DEBUG: uploaded_docs list: {uploaded_docs}")
        print(f"DEBUG: Processing text_content: {knowledge.text_content if knowledge else 'No knowledge object'}")

        return {"message": "Knowledge uploaded", "documents": uploaded_docs}
        
    except Exception as e:
        db.rollback()
        print(f"Knowledge upload error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to upload knowledge: {str(e)}")
    
    
@app.post("/onboarding/voice")
async def configure_voice(
    voice_config: VoiceConfig,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # This would integrate with actual TTS service
    return {"message": "Voice configured", "config": voice_config.dict()}

@app.post("/onboarding/channels")
async def setup_channels(
    channel_config: ChannelConfig,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Update agent with channel configuration
    agent = db.query(AIAgent).filter(AIAgent.company_id == current_user.company_id).first()
    if agent:
        channels = []
        if channel_config.phone_enabled:
            channels.append("phone")
        if channel_config.chat_enabled:
            channels.append("chat")
        if channel_config.whatsapp_enabled:
            channels.append("whatsapp")
        
        agent.channels = channels
        db.commit()
    
    return {"message": "Channels configured", "channels": channels}

@app.post("/onboarding/deploy")
async def deploy_agent(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    agent = db.query(AIAgent).filter(AIAgent.company_id == current_user.company_id).first()
    if agent:
        agent.is_active = True
        db.commit()
    
    return {"message": "Agent deployed successfully", "agent_id": agent.id if agent else None}

@app.get("/onboarding/status")
async def get_onboarding_status(current_user: User = Depends(get_current_user)):
    return {"status": "completed", "agent_active": True}

# Agent management
@app.get("/agents")
async def get_agents(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    agents = db.query(AIAgent).filter(AIAgent.company_id == current_user.company_id).all()
    return [
        {
            "id": agent.id,
            "name": agent.name,
            "role": agent.role,
            "is_active": agent.is_active,
            "phone_number": agent.phone_number,
            "channels": agent.channels,
            "created_at": agent.created_at
        }
        for agent in agents
    ]

@app.get("/agents/{agent_id}")
async def get_agent(agent_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    agent = db.query(AIAgent).filter(
        AIAgent.id == agent_id,
        AIAgent.company_id == current_user.company_id
    ).first()
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Get recent conversations
    conversations = db.query(Conversation).filter(Conversation.agent_id == agent_id).limit(10).all()
    
    return {
        "id": agent.id,
        "name": agent.name,
        "role": agent.role,
        "is_active": agent.is_active,
        "phone_number": agent.phone_number,
        "channels": agent.channels,
        "voice_config": agent.voice_config,
        "personality_config": agent.personality_config,
        "recent_conversations": [
            {
                "id": conv.id,
                "content": conv.content,
                "type": conv.message_type,
                "created_at": conv.created_at
            }
            for conv in conversations
        ]
    }

# Conversation endpoints
@app.post("/conversations/{session_id}/message")
async def send_message(
    session_id: str,
    message: MessageInput,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        # Verify session exists and belongs to user
        session = db.query(Session).filter(
            Session.id == session_id,
            Session.user_id == current_user.id,
            Session.is_active == True
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Save user message
        user_conv = Conversation(
            session_id=session_id,
            agent_id=None,
            message_type="user",
            content=message.content
        )
        db.add(user_conv)
        db.commit()
        
        # Get agent response
        response = run_session_agent(session_id, message.content, db)
        
        # Save agent response
        agent_conv = Conversation(
            session_id=session_id,
            agent_id=None,
            message_type="agent",
            content=response
        )
        db.add(agent_conv)
        db.commit()
        
        return {
            "response": response,
            "conversation_id": agent_conv.id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"Conversation error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process message: {str(e)}")
    
    
# Analytics endpoints
@app.get("/analytics/overview")
async def get_analytics_overview(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Basic analytics
    total_agents = db.query(AIAgent).filter(AIAgent.company_id == current_user.company_id).count()
    total_conversations = db.query(Conversation).join(Session).join(User).filter(
        User.company_id == current_user.company_id
    ).count()
    
    return {
        "total_agents": total_agents,
        "total_conversations": total_conversations,
        "active_sessions": 0,  # Placeholder
        "success_rate": 95.2  # Placeholder
    }

@app.get("/calls/logs")
async def get_call_logs(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conversations = db.query(Conversation).join(Session).join(User).filter(
        User.company_id == current_user.company_id
    ).order_by(Conversation.created_at.desc()).limit(50).all()
    
    return [
        {
            "id": conv.id,
            "session_id": conv.session_id,
            "content": conv.content,
            "type": conv.message_type,
            "created_at": conv.created_at
        }
        for conv in conversations
    ]

# Health check
@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow()}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)