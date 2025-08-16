import argparse
import subprocess
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Tuple, Optional

# Task class to store schema data
class Task:
    def __init__(self, name: str, duration: int, dependencies: List[str], task_type: str, parameters: Dict[str, str]):
        self.name = name
        self.duration = duration
        self.dependencies = dependencies
        self.task_type = task_type
        self.parameters = parameters

# Parse input file into lisstrt of Tasks
def parse_input(file_path: str) -> Tuple[Optional[List[Task]], Optional[str]]:
    tasks = []
    task_names = set()
    try:
        with open(file_path, 'r') as f:
            for line_nuem, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                parts = line.split(',')
                if len(parts) != 5:
                    return None, f"Line {line_num}: Expected 5 fields, got {len(parts)}"
                
                name, duration, deps, task_type, params = parts
                # Validate name
                if not name or name in task_names:
                    return None, f"Line {line_num}: Invalid or duplicate name '{name}'"
                task_names.add(name)
                
                # Validate duration
                try:
                    duration = int(duration)
                    if duration <= 0:
                        raise ValueError
                except ValueError:
                    return None, f"Line {line_num}: Invalid duration '{duration}'"
                
                # Parse dependencies
                dependencies = deps.split(';') if deps else []
                
                # Validate task_type
                if task_type not in ['resolve', 'traceroute', 'iperf3']:
                    return None, f"Line {line_num}: Invalid task_type '{task_type}'"
                
                # Parse parameters
                parameters = {}
                for param in params.split(';'):
                    if param:
                        if '=' not in param:
                            return None, f"Line {line_num}: Invalid parameter format '{param}'"
                        key, value = param.split('=', 1)
                        parameters[key] = value
                
                tasks.append(Task(name, duration, dependencies, task_type, parameters))
    
        # Validate dependencies exist
        for task in tasks:
            for dep in task.dependencies:
                if dep and dep not in task_names:
                    return None, f"Task {task.name}: Unknown dependency '{dep}'"
        
        return tasks, None
    except FileNotFoundError:
        return None, f"File {file_path} not found"
    except Exception as e:
        return None, f"Error parsing file: {str(e)}"

# Detect dependency cycles using DFS
def detect_cycles(tasks: List[Task]) -> Optional[str]:
    visited = set()
    rec_stack = set()
    
    def dfs(task: Task) -> bool:
        visited.add(task.name)
        rec_stack.add(task.name)
        for dep in task.dependencies:
            if dep:
                dep_task = next(t for t in tasks if t.name == dep)
                if dep not in visited:
                    if dfs(dep_task):
                        return True
                elif dep in rec_stack:
                    return True
        rec_stack.remove(task.name)
        return False
    
    for task in tasks:
        if task.name not in visited:
            if dfs(task):
                return "Dependency cycle detected"
    return None

# Calculate expected total runtime (critical path)
def calculate_expected_runtime(tasks: List[Task]) -> int:
    start_times = defaultdict(int)
    finish_times = {}
    for task in tasks:
        max_dep_finish = 0
        for dep in task.dependencies:
            if dep:
                max_dep_finish = max(max_dep_finish, finish_times[dep])
        start_times[task.name] = max_dep_finish
        finish_times[task.name] = max_dep_finish + task.duration
    return max(finish_times.values()) if finish_times else 0

# Build system command from task
def build_command(task: Task) -> str:
    if task.task_type == "resolve":
        return f"dig +short {task.parameters['fqdn']}"
    elif task.task_type == "traceroute":
        if task.parameters.get("tool") == "mtr":
            return f"mtr -nz -c {task.parameters['count']} {task.parameters['endpoint']} --report"
        else:
            return f"traceroute -q {task.parameters['count']} {task.parameters['endpoint']}"
    elif task.task_type == "iperf3":
        cmd = f"iperf3 -c {task.parameters['endpoint']} -p {task.parameters['port']} -t {task.parameters['duration']}"
        return cmd
    return ""

# Execute a task and capture output
def execute_task(task: Task) -> Tuple[bool, str, float]:
    command = build_command(task)
    start_time = time.time()
    try:
        # Run command with timeout (duration + buffer)
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=task.duration + 10
        )
        output = result.stdout if result.returncode == 0 else result.stderr
        success = result.returncode == 0
        if task.task_type == "resolve" and success and not output.strip():
            success = False
            output = "No DNS records found"
    except subprocess.TimeoutExpired:
        success = False
        output = f"Task {task.name} timed out"
    except Exception as e:
        success = False
        output = f"Task {task.name} error: {str(e)}"
    duration = time.time() - start_time
    return success, output, duration

# Validation mode
def validate_mode(file_path: str):
    tasks, error = parse_input(file_path)
    if error:
        print(f"Invalid input: {error}")
        return
    cycle_error = detect_cycles(tasks)
    if cycle_error:
        print(f"Invalid input: {cycle_error}")
        return
    expected_runtime = calculate_expected_runtime(tasks)
    print(f"Input valid. Expected total runtime: {expected_runtime} seconds")

# Execution mode with parallelism
def run_mode(file_path: str):
    tasks, error = parse_input(file_path)
    if error:
        print(f"Invalid input: {error}")
        return
    cycle_error = detect_cycles(tasks)
    if cycle_error:
        print(f"Invalid input: {cycle_error}")
        return
    expected_runtime = calculate_expected_runtime(tasks)
    
    completed = set()
    running = set()
    start_times = {}
    actual_durations = {}
    outputs = {}
    global_start = time.time()
    
    with ThreadPoolExecutor() as executor:
        futures = {}
        while len(completed) < len(tasks):
            for task in tasks:
                if task.name not in completed and task.name not in running:
                    if all(dep in completed for dep in task.dependencies if dep):
                        running.add(task.name)
                        start_times[task.name] = time.time()
                        print(f"Starting {task.name} at {start_times[task.name] - global_start:.1f}s...")
                        futures[task.name] = executor.submit(execute_task, task)
            
            # Check completed tasks
            done = [name for name, future in list(futures.items()) if future.done()]
            for name in done:
                success, output, duration = futures.pop(name).result()
                running.remove(name)
                completed.add(name)
                actual_durations[name] = duration
                outputs[name] = output
                print(f"Finished {name} at {time.time() - global_start:.1f}s")
                if not success:
                    print(f"Error in {name}: {output}")
                    # Skip dependent tasks
                    for t in tasks:
                        if name in t.dependencies and t.name not in completed:
                            completed.add(t.name)
                            outputs[t.name] = f"Skipped due to failure in {name}"
                            print(f"Skipped {t.name} due to failure in {name}")
    
    actual_runtime = time.time() - global_start
    print("\nTask Outputs:")
    for task in tasks:
        print(f"Task {task.name}: {outputs.get(task.name, 'No output')}")
    print(f"Actual runtime: {actual_runtime:.1f} seconds")
    print(f"Difference from expected: {actual_runtime - expected_runtime:.1f} seconds")

# Main function
def main():
    parser = argparse.ArgumentParser(description="Task scheduler for network diagnostics")
    parser.add_argument("file_path", help="Path to task list file")
    parser.add_argument("--validate", action="store_true", help="Validate input and compute expected runtime")
    parser.add_argument("--run", action="store_true", help="Run tasks and measure actual runtime")
    args = parser.parse_args()
    
    if args.validate == args.run:
        print("Specify exactly one of --validate or --run")
        return
    
    if args.validate:
        validate_mode(args.file_path)
    else:
        run_mode(args.file_path)

if __name__ == "__main__":
    main()
