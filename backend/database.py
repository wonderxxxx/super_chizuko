from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from config import Config

# 创建SQLAlchemy引擎
engine = create_engine(Config.DATABASE_URL, echo=True)  # 设置echo=True可以看到SQL语句

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建基类
Base = declarative_base()

class User(Base):
    """用户模型"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关联用户的记忆集合
    memory_collections = relationship("MemoryCollection", back_populates="user")

class MemoryCollection(Base):
    """记忆集合模型，关联用户和Chroma集合"""
    __tablename__ = "memory_collections"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    collection_name = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联用户
    user = relationship("User", back_populates="memory_collections")

# 创建数据库表
def init_db():
    """初始化数据库"""
    Base.metadata.create_all(bind=engine)

# 获取数据库会话
def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 用户相关操作
def get_user_by_email(db, email):
    """根据邮箱获取用户"""
    return db.query(User).filter(User.email == email).first()

def create_user(db, email):
    """创建新用户"""
    db_user = User(email=email)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_or_create_user(db, email):
    """获取或创建用户"""
    user = get_user_by_email(db, email)
    if not user:
        user = create_user(db, email)
    return user

# 记忆集合相关操作
def get_memory_collection_by_user(db, user_id):
    """根据用户ID获取记忆集合"""
    return db.query(MemoryCollection).filter(MemoryCollection.user_id == user_id).first()

def create_memory_collection(db, user_id, collection_name):
    """创建记忆集合"""
    db_collection = MemoryCollection(user_id=user_id, collection_name=collection_name)
    db.add(db_collection)
    db.commit()
    db.refresh(db_collection)
    return db_collection

def get_or_create_memory_collection(db, user_id, email):
    """获取或创建用户的记忆集合"""
    # 检查用户是否已有记忆集合
    collection = get_memory_collection_by_user(db, user_id)
    if collection:
        return collection
    
    # 为用户创建新的记忆集合，使用邮箱作为集合名的一部分
    collection_name = f"memory_{email.replace('@', '_').replace('.', '_')}"
    return create_memory_collection(db, user_id, collection_name)
