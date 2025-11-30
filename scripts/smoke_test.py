# scripts/smoke_test.py
import asyncio
import logging
from uroboros.arbiter.sandbox import E2BArbiter
from uroboros.core.types import FileArtifact, TestResult

# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("smoke_test")

async def test_infrastructure():
    logger.info("🔥 Starting Infrastructure Smoke Test...")
    
    arbiter = E2BArbiter()
    
    # 1. Create a dummy python file
    dummy_code = FileArtifact(
        file_path="hello.py", 
        content="print('Hello from inside the Firecracker MicroVM!')",
        language="python"
    )
    
    # 2. Create a dummy test file (just runs the code)
    # We use a simple command instead of full pytest for this smoke test
    # but the Arbiter expects files, so we pass them.
    
    logger.info("🚀 Spawning Sandbox...")
    
    # We hack the execute method slightly or just check connectivity
    # Ideally, we call execute() with valid inputs.
    
    # Let's create a valid pytest file to pass the strict checks
    test_code = FileArtifact(
        file_path="test_hello.py",
        content="def test_true(): assert True",
        language="python"
    )

    try:
        result = await arbiter.execute(files=[dummy_code], test_files=[test_code])
        
        logger.info(f"✅ Sandbox Result Status: {result.status}")
        logger.info(f"✅ Sandbox Output: {result.stdout}")
        
        if result.exit_code == 0:
            logger.info("🎉 Infrastructure is HEALTHY.")
        else:
            logger.error("❌ Infrastructure is UNHEALTHY.")
            
    except Exception as e:
        logger.error(f"❌ CRITICAL FAILURE: {e}")

if __name__ == "__main__":
    asyncio.run(test_infrastructure())
