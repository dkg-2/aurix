import docker
import os
import uuid
import shutil

class SandboxExecutor:
    """
    Safely executes AI-generated Validation scripts.
    Supports 'Stateful Wargaming' by allowing Read-Write access during verification.
    
    Docker-out-of-Docker Fix:
    When running inside a container, tempfile creates paths on the CONTAINER filesystem,
    but Docker daemon mounts from the HOST filesystem. So we write exploit scripts to the
    shared workspace volume (mounted as ./workspace on the host) which is accessible to both.
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

        # Create a sandbox subdirectory inside the workspace (which is a shared Docker volume)
        # This ensures the Docker daemon can access it from the host
        sandbox_id = str(uuid.uuid4())[:8]
        sandbox_dir = os.path.join(workspace_path, f".sandbox_{sandbox_id}")
        script_path = os.path.join(sandbox_dir, "exploit.py")

        try:
            os.makedirs(sandbox_dir, exist_ok=True)
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(script_content)

            # Resolve host paths for Docker-out-of-Docker
            host_workspace = os.getenv("HOST_WORKSPACE_DIR")
            if host_workspace:
                # Running inside a container — map to host paths
                folder_name = os.path.basename(workspace_path)
                clean_host = host_workspace.rstrip('/\\')
                host_src_path = f"{clean_host}/{folder_name}"
                host_sandbox_path = f"{host_src_path}/.sandbox_{sandbox_id}"
            else:
                # Running directly on host
                host_src_path = os.path.abspath(workspace_path)
                host_sandbox_path = os.path.abspath(sandbox_dir)

            # Define volumes
            mode = 'ro' if read_only else 'rw'
            volumes = {
                host_sandbox_path: {'bind': '/sandbox', 'mode': 'ro'},
                host_src_path: {'bind': '/src', 'mode': mode}
            }

            container = self.client.containers.run(
                image=self.image,
                command=["python", "/sandbox/exploit.py"],
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
            # Clean up the sandbox directory
            if os.path.exists(sandbox_dir):
                shutil.rmtree(sandbox_dir, ignore_errors=True)
