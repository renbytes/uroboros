import logging
import shutil
import tempfile
import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any, Optional

from uroboros.core.types import Patch
from uroboros.core.utils import safe_write_file, safe_read_file

logger = logging.getLogger(__name__)

class Patcher:
    """
    Handles safe application of code changes to the file system.
    """

    @staticmethod
    def apply_to_file(original_path: Path, patch: Patch) -> bool:
        """
        Applies a patch to a file on disk safely.
        
        Strategy:
        1. Create a backup.
        2. Write new content (assuming patch.diff is the new file content for MVP reliability).
        3. If write fails, restore backup.
        """
        backup_path = original_path.with_suffix(original_path.suffix + ".bak")
        
        try:
            # 1. Backup (if file exists)
            if original_path.exists():
                shutil.copy2(original_path, backup_path)
            
            # 2. Write New Content
            # Note: In a more advanced version, we would parse Unified Diffs here.
            # For strict LLM reliability, we prefer full-file context generation.
            safe_write_file(original_path, patch.diff)
            
            logger.info(f"Successfully patched {original_path}")
            
            # Cleanup backup on success
            if backup_path.exists():
                backup_path.unlink()
                
            return True

        except Exception as e:
            logger.error(f"Failed to patch {original_path}: {e}")
            
            # 3. Restore on Failure
            if backup_path.exists():
                logger.warning(f"Restoring backup for {original_path}")
                shutil.move(str(backup_path), str(original_path))
                
            return False

class RuntimePatcher:
    """
    The Gödel Mechanism Enabler.
    Allows the agent to hot-swap its own logic during execution.
    """

    @staticmethod
    def hot_swap_class(target_module_name: str, class_name: str, new_source_code: str) -> bool:
        """
        Dynamically redefines a class in a running module using 'exec'.
        
        Args:
            target_module_name: e.g. "uroboros.actor.agent"
            class_name: e.g. "UroborosActor"
            new_source_code: The full string of the new class definition.
            
        Returns:
            True if successful.
        """
        logger.warning(f"⚠️ ATTEMPTING RUNTIME HOT-SWAP: {target_module_name}.{class_name}")
        
        try:
            # 1. Get the module
            if target_module_name not in importlib.util.sys.modules:
                logger.error(f"Module {target_module_name} is not loaded.")
                return False
            
            module = importlib.util.sys.modules[target_module_name]
            
            # 2. Prepare the execution namespace
            # We need to ensure the new code has access to the module's existing imports/globals
            local_namespace: dict[str, Any] = {}
            global_namespace = module.__dict__
            
            # 3. Execute the new code
            # This compiles the string and creates the new class object in local_namespace
            exec(new_source_code, global_namespace, local_namespace)
            
            # 4. Verify the class was created
            if class_name not in local_namespace:
                logger.error(f"New source code did not define class '{class_name}'")
                return False
            
            new_class = local_namespace[class_name]
            
            # 5. Monkey Patch: Overwrite the class in the module
            setattr(module, class_name, new_class)
            
            logger.info(f"✅ Successfully hot-swapped {class_name}. New logic is active.")
            return True

        except Exception as e:
            logger.error(f"Runtime Hot-Swap Failed: {e}", exc_info=True)
            return False

    @staticmethod
    def hot_swap_method(target_object: Any, method_name: str, new_method_code: str) -> bool:
        """
        Replaces a single method on a specific object instance.
        """
        try:
            # Execute definition to get the function object
            local_ns: dict[str, Any] = {}
            exec(new_method_code, globals(), local_ns)
            
            func_name = list(local_ns.keys())[0] # Assume the first function defined is the target
            new_func = local_ns[func_name]
            
            # Bind the function to the object (creating a method)
            # This typically requires binding descriptors or simple assignment depending on the object
            setattr(target_object, method_name, new_func.__get__(target_object))
            
            logger.info(f"Hot-swapped method {method_name} on {target_object}")
            return True
        except Exception as e:
            logger.error(f"Method Hot-Swap Failed: {e}")
            return False