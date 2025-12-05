# backend/memory_manager_wrapper.py
"""
MemoryManager Wrapper
- 优先使用 MemoryManagerV2 (backend/memory_manager_v2.py)
- 若 V2 出现异常，则自动 fallback 到原始 V1 (backend/memory_manager.py)
- 动态从文件路径加载 V1，避免导入循环/模块命名冲突
- 提供 health_check() 与手动强制切换接口
"""

import importlib
import importlib.util
import logging
import os
import threading
import traceback
from types import ModuleType
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter(
        '%(asctime)s %(levelname)s [%(name)s] %(message)s'
    )
    ch.setFormatter(formatter)
    logger.addHandler(ch)


class MemoryManagerWrapper:
    def __init__(
        self,
        backend_dir: Optional[str] = None,
        v2_module_name: str = "backend.memory_manager_v2",
        v1_filename: str = "memory_manager.py",
        **v2_init_kwargs
    ):
        """
        Args:
            backend_dir: 如果 None，则自动取当前文件的父目录 backend/
            v2_module_name: Python 导入路径（点号路径）用于加载 v2（如果已作为模块可用）
            v1_filename: 原始 v1 文件名（相对于 backend_dir）
            v2_init_kwargs: 传入给 MemoryManagerV2 的构造参数
        """
        # 控制优先级标志：默认优先使用 v2
        self._force_v1 = False
        self._force_v2 = False
        self._lock = threading.RLock()

        # 1) load v2 via normal import (prefer installed module or file in path)
        self._v2 = None
        try:
            v2_mod = importlib.import_module(v2_module_name)
            # MemoryManagerV2 class expected in module
            v2_cls = getattr(v2_mod, "MemoryManagerV2", None)
            if v2_cls is None:
                raise ImportError(f"{v2_module_name} does not expose MemoryManagerV2")
            self._v2 = v2_cls(**v2_init_kwargs)
            logger.info("Loaded MemoryManagerV2 via import %s", v2_module_name)
        except Exception as e:
            logger.warning("Cannot import MemoryManagerV2 via module '%s': %s", v2_module_name, e)
            logger.debug(traceback.format_exc())
            self._v2 = None

        # 2) Dynamically load original memory_manager.py (v1) by file path
        # Determine backend dir
        if backend_dir is None:
            # file is located in backend/ relative to this wrapper file
            wrapper_dir = os.path.dirname(os.path.abspath(__file__))
            backend_dir = wrapper_dir  # wrapper is already in backend/
        v1_path = os.path.join(backend_dir, v1_filename)
        self._v1_mod: Optional[ModuleType] = None
        self._v1 = None
        if os.path.exists(v1_path):
            try:
                spec = importlib.util.spec_from_file_location("memory_manager_v1_dynamic", v1_path)
                m = importlib.util.module_from_spec(spec)
                loader = spec.loader
                if loader is None:
                    raise ImportError("spec.loader is None while loading v1")
                loader.exec_module(m)  # type: ignore
                self._v1_mod = m
                # try to find common class name or factory
                v1_cls = getattr(m, "MemoryManager", None) or getattr(m, "MemoryManagerV1", None) or None
                if v1_cls is None:
                    # If v1 exposes functions rather than class, keep module only
                    logger.info("Loaded v1 module but no MemoryManager class detected; will use module-level functions if present.")
                else:
                    # instantiate if it has a constructor signature
                    try:
                        self._v1 = v1_cls()
                        logger.info("Instantiated MemoryManagerV1 from %s", v1_path)
                    except Exception:
                        logger.info("MemoryManagerV1 class exists but failed to instantiate without args; keeping module for calling functions.")
                        self._v1 = None
                logger.info("Loaded original memory manager module from %s", v1_path)
            except Exception as e:
                logger.error("Failed to dynamically load v1 memory manager from %s: %s", v1_path, e)
                logger.debug(traceback.format_exc())
                self._v1_mod = None
                self._v1 = None
        else:
            logger.warning("v1 memory manager file not found at %s", v1_path)

        # If v2 was not importable, but v1 exists and exposes a class, use v1 as default
        if self._v2 is None and self._v1 is not None:
            logger.info("No v2 available; defaulting to v1 instance.")
        elif self._v2 is None and self._v1 is None:
            logger.error("Neither v2 nor v1 memory managers are available. Wrapper will be non-functional until one is provided.")

    # ---------------------------
    # Helper: choose active backend
    # ---------------------------
    def _use_v2(self) -> bool:
        if self._force_v1:
            return False
        if self._force_v2:
            return True
        return self._v2 is not None

    def force_use_v1(self, enable: bool = True):
        with self._lock:
            self._force_v1 = enable
            if enable:
                self._force_v2 = False
            logger.info("force_use_v1 set to %s", enable)

    def force_use_v2(self, enable: bool = True):
        with self._lock:
            self._force_v2 = enable
            if enable:
                self._force_v1 = False
            logger.info("force_use_v2 set to %s", enable)

    # ---------------------------
    # Public API (mirror v2/v1)
    # ---------------------------
    def add_memory(self, *args, **kwargs) -> Optional[str]:
        """Add memory. Returns memory_id or None."""
        with self._lock:
            # Try V2 first
            if self._use_v2():
                try:
                    return self._v2.add_memory(*args, **kwargs)
                except Exception as e:
                    logger.error("MemoryManagerV2.add_memory failed: %s", e)
                    logger.debug(traceback.format_exc())
                    # fallback to v1 if available
            # Try V1
            try:
                # If v1 was instantiated as an object with same API
                if self._v1 is not None and hasattr(self._v1, "add_memory"):
                    return self._v1.add_memory(*args, **kwargs)
                # else module-level function?
                if self._v1_mod is not None and hasattr(self._v1_mod, "add_memory"):
                    return getattr(self._v1_mod, "add_memory")(*args, **kwargs)
                logger.error("No suitable add_memory implementation found in v1.")
            except Exception as e:
                logger.error("Fallback v1.add_memory also failed: %s", e)
                logger.debug(traceback.format_exc())
            return None

    def retrieve_relevant_memories(self, *args, **kwargs) -> List[Dict[str, Any]]:
        """Return list of memories (try v2 first, fallback to v1)"""
        with self._lock:
            if self._use_v2():
                try:
                    return self._v2.retrieve_relevant_memories(*args, **kwargs)
                except Exception as e:
                    logger.error("MemoryManagerV2.retrieve_relevant_memories failed: %s", e)
                    logger.debug(traceback.format_exc())

            # fallback
            try:
                if self._v1 is not None and hasattr(self._v1, "retrieve_relevant_memories"):
                    return self._v1.retrieve_relevant_memories(*args, **kwargs)
                if self._v1_mod is not None and hasattr(self._v1_mod, "retrieve_relevant_memories"):
                    return getattr(self._v1_mod, "retrieve_relevant_memories")(*args, **kwargs)
                logger.error("No suitable retrieve_relevant_memories in v1.")
            except Exception as e:
                logger.error("Fallback v1.retrieve_relevant_memories failed: %s", e)
                logger.debug(traceback.format_exc())
            return []

    def clear_user_memory(self, *args, **kwargs) -> bool:
        with self._lock:
            if self._use_v2():
                try:
                    return self._v2.clear_user_memory(*args, **kwargs)
                except Exception as e:
                    logger.error("MemoryManagerV2.clear_user_memory failed: %s", e)
                    logger.debug(traceback.format_exc())

            try:
                if self._v1 is not None and hasattr(self._v1, "clear_user_memory"):
                    return self._v1.clear_user_memory(*args, **kwargs)
                if self._v1_mod is not None and hasattr(self._v1_mod, "clear_user_memory"):
                    return getattr(self._v1_mod, "clear_user_memory")(*args, **kwargs)
                logger.error("No suitable clear_user_memory in v1.")
            except Exception as e:
                logger.error("Fallback v1.clear_user_memory failed: %s", e)
                logger.debug(traceback.format_exc())
            return False

    # Utility: delete single memory id
    def delete_memory(self, memory_id: str) -> bool:
        with self._lock:
            if self._use_v2():
                try:
                    if hasattr(self._v2, "delete_memory"):
                        return self._v2.delete_memory(memory_id)
                except Exception as e:
                    logger.error("MemoryManagerV2.delete_memory failed: %s", e)
                    logger.debug(traceback.format_exc())
            # fallback
            try:
                if self._v1 is not None and hasattr(self._v1, "delete_memory"):
                    return self._v1.delete_memory(memory_id)
                if self._v1_mod is not None and hasattr(self._v1_mod, "delete_memory"):
                    return getattr(self._v1_mod, "delete_memory")(memory_id)
            except Exception as e:
                logger.error("Fallback v1.delete_memory failed: %s", e)
                logger.debug(traceback.format_exc())
            return False

    # Health check (try simple op on active backend)
    def health_check(self) -> Dict[str, Any]:
        res = {"v2": False, "v1": False, "active": None, "errors": []}
        # Check v2
        if self._v2 is not None:
            try:
                # call a light-weight op (non-destructive)
                if hasattr(self._v2, "collection"):
                    # try to get collection info if accessible
                    _ = getattr(self._v2, "collection")
                res["v2"] = True
            except Exception as e:
                res["errors"].append(f"v2: {e}")
                logger.debug(traceback.format_exc())

        # Check v1
        if self._v1 is not None or self._v1_mod is not None:
            try:
                # if instantiated object, check it's callable methods
                if self._v1 is not None and hasattr(self._v1, "retrieve_relevant_memories"):
                    res["v1"] = True
                elif self._v1_mod is not None and hasattr(self._v1_mod, "retrieve_relevant_memories"):
                    res["v1"] = True
            except Exception as e:
                res["errors"].append(f"v1: {e}")
                logger.debug(traceback.format_exc())

        res["active"] = "v2" if self._use_v2() else "v1"
        return res

    # Generic passthrough for methods not explicitly wrapped (use with caution)
    def __getattr__(self, item):
        """
        If an attribute isn't found on the wrapper, try dispatching to the active backend.
        This makes the wrapper more tolerant to API additions in v1/v2.
        """
        if item.startswith("_"):
            raise AttributeError(item)

        # prefer v2
        if self._use_v2() and self._v2 is not None and hasattr(self._v2, item):
            return getattr(self._v2, item)
        # fallback v1 instance
        if self._v1 is not None and hasattr(self._v1, item):
            return getattr(self._v1, item)
        # fallback v1 module-level
        if self._v1_mod is not None and hasattr(self._v1_mod, item):
            return getattr(self._v1_mod, item)

        raise AttributeError(item)
