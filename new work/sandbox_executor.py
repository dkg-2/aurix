import docker
import tempfile
import os
import shutil

class SandboxExecutor:
    """
    Safely executes AI-generated Validation scripts.
    Supports 'Stateful Wargaming' by allowing Read-Write access during verification.
    """

    def __init__(self, image="aurix-sandbox:latest"):
        try:
            self.client = docker.from_env()
            self.image = image
        except Exception as e:
            print(f"[ERROR] Docker not found or not running: {e}")
            self.client = None

    def execute_python_poc(self, script_content, workspace_path, timeout=30, read_only=True):
        """
        Runs a Python script with access to the target source code at /src.
        If read_only=False, the script can permanently modify the source code in workspace_path.
        """
        if not self.client:
            return {"error": "Docker client not initialized."}

        temp_dir = tempfile.mkdtemp(prefix="aurix_sandbox_")
        script_path = os.path.join(temp_dir, "exploit.py")
        
        try:
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(script_content)

            # Define volumes
            mode = 'ro' if read_only else 'rw'
            volumes = {
                temp_dir: {'bind': '/app', 'mode': 'ro'},
                os.path.abspath(workspace_path): {'bind': '/src', 'mode': mode}
            }

            container = self.client.containers.run(
                image=self.image,
                command=["python", "/app/exploit.py"],
                volumes=volumes,
                working_dir="/src",
                mem_limit="256m",
                nano_cpus=1000000000,
                detach=True
            )

            try:
                result = container.wait(timeout=timeout)
                exit_code = result.get("StatusCode", 1)
                stdout = container.logs(stdout=True, stderr=False).decode("utf-8")
                stderr = container.logs(stdout=False, stderr=True).decode("utf-8")
            except Exception:
                container.kill()
                return {"error": "Timeout triggered."}
            finally:
                container.remove(force=True)

            return {
                "exit_code": exit_code,
                "stdout": stdout.strip(),
                "stderr": stderr.strip(),
                "verified": exit_code == 0
            }

        except Exception as e:
            return {"error": f"Sandbox failure: {str(e)}"}
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
