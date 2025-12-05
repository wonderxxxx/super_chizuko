#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
初始化脚本，用于在其他机器上生成chroma文件和数据库文件
"""

import os
import sys
import chromadb
from sentence_transformers import SentenceTransformer
from config import Config
from database import init_db, get_db, get_or_create_user, get_or_create_memory_collection

def init_database():
    """
    初始化数据库
    """
    print("正在初始化SQLite数据库...")
    try:
        init_db()
        print("数据库初始化完成！")
        
        # 创建默认用户和记忆集合
        db = next(get_db())
        try:
            user = get_or_create_user(db, "default@example.com")
            collection = get_or_create_memory_collection(db, user.id, "default@example.com")
            print(f"已创建默认用户和记忆集合: {collection.collection_name}")
        finally:
            db.close()
            
    except Exception as e:
        print(f"初始化数据库时出错: {e}")
        raise

def init_chroma_db():
    """
    初始化Chroma数据库
    """
    print("正在初始化Chroma数据库...")
    try:
        # 创建Chroma客户端
        chroma_client = chromadb.PersistentClient(path=Config.CHROMA_DB_PATH)
        
        # 创建默认集合
        default_collection = chroma_client.get_or_create_collection(name="memory_default_example_com")
        print(f"已创建默认Chroma集合: {default_collection.name}")
        
        print("Chroma数据库初始化完成！")
        return chroma_client
    except Exception as e:
        print(f"初始化Chroma数据库时出错: {e}")
        raise

def main():
    """
    主函数，执行所有初始化操作
    """
    try:
        print("开始初始化数据...")
        
        # 初始化数据库
        init_database()
        
        # 初始化Chroma数据库
        init_chroma_db()
        
        print("\n所有数据初始化完成！")
        print("您可以通过以下命令启动应用:")
        print("python app.py")
        
    except Exception as e:
        print(f"初始化失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()