"""
Shell command execution utilities for BigLinux Calamares Configuration Tool
Safe wrapper for executing system commands with proper error handling
"""

import logging
import os
import shlex
import signal
import subprocess
import threading
from typing import Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class CommandResult:
    """Container for command execution results"""

    def __init__(self, returncode: int, stdout: str, stderr: str, command: str):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.command = command
        self.success = returncode == 0

    def __str__(self):
        return f"CommandResult(returncode={self.returncode}, success={self.success})"

    def __bool__(self):
        return self.success


class ShellExecutor:
    """Safe shell command executor with timeout and logging"""

    def __init__(self, timeout: int = 30, log_commands: bool = True):
        self.timeout = timeout
        self.log_commands = log_commands
        self.running_processes: Dict[int, subprocess.Popen] = {}
        self._lock = threading.Lock()

    def execute(
        self,
        command: str,
        timeout: Optional[int] = None,
        shell: bool = False,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        check_output: bool = True,
    ) -> CommandResult:
        """
        Execute a shell command safely

        Args:
            command: Command to execute
            timeout: Timeout in seconds (None uses default)
            shell: Whether to use shell=True
            cwd: Working directory
            env: Environment variables
            check_output: Whether to capture output

        Returns:
            CommandResult with execution details
        """
        if timeout is None:
            timeout = self.timeout

        if self.log_commands:
            logger.info(f"Executing command: {command}")

        try:
            # Prepare command
            if shell:
                cmd = command
            else:
                cmd = shlex.split(command)

            # Prepare environment
            exec_env = os.environ.copy()
            if env:
                exec_env.update(env)

            # Start process
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE if check_output else None,
                stderr=subprocess.PIPE if check_output else None,
                shell=shell,
                cwd=cwd,
                env=exec_env,
                text=True,
                preexec_fn=os.setsid if os.name != "nt" else None,
            )

            # Track running process
            with self._lock:
                self.running_processes[process.pid] = process

            try:
                # Wait for completion with timeout
                stdout, stderr = process.communicate(timeout=timeout)

                # Create result
                result = CommandResult(
                    returncode=process.returncode,
                    stdout=stdout or "",
                    stderr=stderr or "",
                    command=command,
                )

                if self.log_commands:
                    if result.success:
                        logger.debug(f"Command completed successfully: {command}")
                    else:
                        logger.warning(
                            f"Command failed (code {result.returncode}): {command}"
                        )
                        if result.stderr:
                            logger.warning(f"Command stderr: {result.stderr}")

                return result

            except subprocess.TimeoutExpired:
                logger.error(f"Command timed out after {timeout}s: {command}")

                # Kill process group
                try:
                    if os.name != "nt":
                        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                    else:
                        process.terminate()

                    # Wait a bit for graceful termination
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        # Force kill if still running
                        if os.name != "nt":
                            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                        else:
                            process.kill()
                        process.wait()

                except Exception as e:
                    logger.error(f"Failed to kill timed out process: {e}")

                return CommandResult(
                    returncode=-1,
                    stdout="",
                    stderr=f"Command timed out after {timeout} seconds",
                    command=command,
                )

            finally:
                # Remove from tracking
                with self._lock:
                    self.running_processes.pop(process.pid, None)

        except Exception as e:
            logger.error(f"Exception executing command '{command}': {e}")
            return CommandResult(
                returncode=-1, stdout="", stderr=str(e), command=command
            )

    def execute_async(
        self,
        command: str,
        callback: Callable[[CommandResult], None],
        timeout: Optional[int] = None,
        **kwargs,
    ) -> threading.Thread:
        """
        Execute command asynchronously with callback

        Args:
            command: Command to execute
            callback: Function to call with result
            timeout: Timeout in seconds
            **kwargs: Additional arguments for execute()

        Returns:
            Thread object
        """

        def run_command():
            result = self.execute(command, timeout=timeout, **kwargs)
            if callback:
                callback(result)

        thread = threading.Thread(target=run_command)
        thread.daemon = True
        thread.start()
        return thread

    def check_command_exists(self, command: str) -> bool:
        """
        Check if a command exists in PATH

        Args:
            command: Command name to check

        Returns:
            True if command exists
        """
        result = self.execute(f"command -v {shlex.quote(command)}", shell=True)
        return result.success

    def kill_all_processes(self):
        """Kill all running processes started by this executor"""
        with self._lock:
            for pid, process in list(self.running_processes.items()):
                try:
                    if process.poll() is None:  # Still running
                        logger.info(f"Killing process {pid}")
                        if os.name != "nt":
                            os.killpg(os.getpgid(pid), signal.SIGTERM)
                        else:
                            process.terminate()
                except Exception as e:
                    logger.error(f"Failed to kill process {pid}: {e}")

            self.running_processes.clear()


# Global executor instance
_default_executor = ShellExecutor()


def execute_command(command: str, **kwargs) -> CommandResult:
    """
    Execute a command using the default executor

    Args:
        command: Command to execute
        **kwargs: Additional arguments

    Returns:
        CommandResult
    """
    return _default_executor.execute(command, **kwargs)


def execute_command_async(
    command: str, callback: Callable[[CommandResult], None], **kwargs
) -> threading.Thread:
    """
    Execute a command asynchronously using the default executor

    Args:
        command: Command to execute
        callback: Callback function
        **kwargs: Additional arguments

    Returns:
        Thread object
    """
    return _default_executor.execute_async(command, callback, **kwargs)


def check_command_exists(command: str) -> bool:
    """
    Check if a command exists in PATH

    Args:
        command: Command name

    Returns:
        True if command exists
    """
    return _default_executor.check_command_exists(command)


def get_command_output(command: str, **kwargs) -> Optional[str]:
    """
    Get command output or None if failed

    Args:
        command: Command to execute
        **kwargs: Additional arguments

    Returns:
        Command output or None
    """
    result = execute_command(command, **kwargs)
    return result.stdout.strip() if result.success else None


def run_command_simple(command: str, **kwargs) -> bool:
    """
    Run command and return success status

    Args:
        command: Command to execute
        **kwargs: Additional arguments

    Returns:
        True if command succeeded
    """
    result = execute_command(command, **kwargs)
    return result.success


def cleanup_shell_resources():
    """Cleanup shell executor resources"""
    _default_executor.kill_all_processes()


# Convenience functions for common shell operations
def pacman_query_installed() -> List[str]:
    """Get list of installed packages"""
    result = execute_command("pacman -Qq")
    if result.success:
        return [pkg.strip() for pkg in result.stdout.split("\n") if pkg.strip()]
    return []


def check_package_installed(package: str) -> bool:
    """Check if a specific package is installed"""
    result = execute_command(f"pacman -Q {shlex.quote(package)}")
    return result.success


def get_system_info() -> Dict[str, str]:
    """Get basic system information"""
    info = {}

    # Kernel version
    result = execute_command("uname -r")
    if result.success:
        info["kernel"] = result.stdout.strip().split("-")[0]

    # Boot mode
    result = execute_command("[ -d /sys/firmware/efi ]")
    info["boot_mode"] = "UEFI" if result.success else "BIOS (Legacy)"

    # Session type
    session_type = os.environ.get("XDG_SESSION_TYPE", "unknown")
    info["session_type"] = (
        session_type.title() if session_type != "unknown" else "Unknown"
    )

    return info


def get_package_icon(package: str, size: int = 48) -> Optional[str]:
    """Get icon path for a package using multiple methods.

    Tries in order:
    1. geticons command (returns full path)
    2. Direct file search in common icon locations
    3. Returns package name for GTK IconTheme lookup
    """
    # Try geticons command first
    result = execute_command(f"geticons -s {size} {shlex.quote(package)}")
    if result.success and result.stdout.strip():
        icon_path = result.stdout.strip()
        if os.path.exists(icon_path):
            logger.debug(f"Found icon via geticons for {package}: {icon_path}")
            return icon_path

    # Try common icon locations
    icon_dirs = [
        f"/usr/share/icons/hicolor/{size}x{size}/apps",
        "/usr/share/icons/hicolor/scalable/apps",
        "/usr/share/pixmaps",
    ]
    extensions = [".png", ".svg", ".xpm"]

    for icon_dir in icon_dirs:
        for ext in extensions:
            icon_path = os.path.join(icon_dir, f"{package}{ext}")
            if os.path.exists(icon_path):
                logger.debug(f"Found icon in {icon_dir} for {package}: {icon_path}")
                return icon_path

    # Return package name for GTK IconTheme fallback
    logger.debug(f"No icon file found for {package}, returning name for GTK lookup")
    return package
