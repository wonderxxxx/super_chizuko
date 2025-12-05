#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从ModelScope下载模型的脚本
"""

import os
import argparse
from modelscope.hub.snapshot_download import snapshot_download

def download_model(model_name: str, save_dir: str, revision: str = None):
    """
    从ModelScope下载模型
    
    Args:
        model_name: 模型名称，例如：'Xorbits/bge-small-zh-v1.5'
        save_dir: 保存目录
        revision: 模型版本号，可选
    """
    try:
        print(f"正在下载模型 {model_name} 到 {save_dir}...")
        os.makedirs(save_dir, exist_ok=True)
        
        # 下载模型
        snapshot_download(
            model_id=model_name,
            cache_dir=save_dir,
            revision=revision,
            local_files_only=False,
            force_download=True
        )
        
        print(f"模型 {model_name} 下载完成！")
    except Exception as e:
        print(f"下载模型时出错: {e}")
        raise

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="从ModelScope下载模型")
    parser.add_argument(
        "--model-name",
        default="Xorbits/bge-small-zh-v1.5",
        help="模型名称，默认为'Xorbits/bge-small-zh-v1.5'"
    )
    parser.add_argument(
        "--save-dir",
        default=os.path.join(os.path.dirname(__file__), "models"),
        help="保存目录，默认为当前目录下的models文件夹"
    )
    parser.add_argument(
        "--revision",
        default=None,
        help="模型版本号，可选"
    )
    
    args = parser.parse_args()
    download_model(args.model_name, args.save_dir, args.revision)