import os
import sys
import json
import importlib
import traceback
import sqlite3
import hashlib
from fastapi import FastAPI, APIRouter, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from threading import Thread
from time import sleep

# Correctly import the completion function from LiteLLM
from litellm import completion, supports_function_calling

# Configuration
MODEL_NAME = os.environ.get('LITELLM_MODEL', 'gpt-4o')  # Default model; can be swapped easily

# Initialize FastAPI app
app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates directory
templates = Jinja2Templates(directory="templates")

LOG_FILE = "logs/fastapi_app_builder_log.json"

# Directory paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'static')
ROUTES_DIR = os.path.join(BASE_DIR, 'routes')

# Initialize progress tracking
progress = {
    "status": "idle",
    "iteration": 0,
    "max_iterations": 50,
    "output": "",
    "completed": False
}

# Ensure directories exist and create __init__.py in routes
def create_directory(path):
    if not os.path.exists(path):
        os.makedirs(path)
        if path == ROUTES_DIR:
            create_file(os.path.join(ROUTES_DIR, '__init__.py'), '')
        return f"Created directory: {path}"
    return f"Directory already exists: {path}"

def create_file(path, content):
    try:
        with open(path, 'x') as f:
            f.write(content)
        return f"Created file: {path}"
    except FileExistsError:
        with open(path, 'w') as f:
            f.write(content)
        return f"Updated file: {path}"
    except Exception as e:
        return f"Error creating/updating file {path}: {e}"

def update_file(path, content):
    try:
        with open(path, 'w') as f:
            f.write(content)
        return f"Updated file: {path}"
    except Exception as e:
        return f"Error updating file {path}: {e}"

def fetch_code(file_path):
    try:
        with open(file_path, 'r') as f:
            code = f.read()
        return code
    except Exception as e:
        return f"Error fetching code from {file_path}: {e}"

def load_routes():
    try:
        if BASE_DIR not in sys.path:
            sys.path.append(BASE_DIR)
        for filename in os.listdir(ROUTES_DIR):
            if filename.endswith('.py') and filename != '__init__.py':
                module_name = filename[:-3]
                module_path = f'routes.{module_name}'
                try:
                    if module_path in sys.modules:
                        importlib.reload(sys.modules[module_path])
                    else:
                        importlib.import_module(module_path)
                    module = sys.modules.get(module_path)
                    if module:
                        for attr_name in dir(module):
                            attr = getattr(module, attr_name)
                            if isinstance(attr, APIRouter):
                                app.include_router(attr)
                except Exception as e:
                    print(f"Error importing module {module_path}: {e}")
                    continue
        print("Routes loaded successfully.")
        return "Routes loaded successfully."
    except Exception as e:
        print(f"Error in load_routes: {e}")
        return f"Error loading routes: {e}"

def task_completed():
    progress["status"] = "completed"
    progress["completed"] = True
    return "Task marked as completed."

# Initialize necessary directories
create_directory(TEMPLATES_DIR)
create_directory(STATIC_DIR)
create_directory(ROUTES_DIR)  # This will also create __init__.py in routes

# Load routes once at initiation
load_routes()

# Function to log history to file
def log_to_file(history_dict):
    try:
        with open(LOG_FILE, 'w') as log_file:
            json.dump(history_dict, log_file, indent=4)
    except Exception as e:
        pass  # Silent fail

# Default route to serve generated index.html or render a form
@app.get("/", response_class=HTMLResponse)
@app.post("/", response_class=HTMLResponse)
async def home(request: Request):
    index_file = os.path.join(TEMPLATES_DIR, 'index.html')
    if os.path.exists(index_file):
        return FileResponse(index_file)
    else:
        if request.method == 'POST':
            user_input = (await request.form())['user_input']
            progress["status"] = "running"
            progress["iteration"] = 0
            progress["output"] = ""
            progress["completed"] = False
            thread = Thread(target=run_main_loop, args=(user_input,))
            thread.start()
            return templates.TemplateResponse("progress.html", {"request": request, "progress_output": progress["output"]})
        else:
            return templates.TemplateResponse("form.html", {"request": request})

# Route to provide progress updates
@app.get("/progress", response_class=JSONResponse)
async def get_progress():
    return JSONResponse(content=progress)

# SQLite3 database setup
DATABASE_PATH = "codes.db"

def init_db():
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS codes (
            code_id TEXT PRIMARY KEY,
            code_content TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def store_code(code_content):
    # Generate a unique identifier using SHA-256 hash of the code content
    code_id = hashlib.sha256(code_content.encode()).hexdigest()
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('INSERT OR REPLACE INTO codes (code_id, code_content) VALUES (?, ?)', (code_id, code_content))
    conn.commit()
    conn.close()
    return f"Code stored with ID: {code_id}"

def retrieve_code(code_id):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT code_content FROM codes WHERE code_id = ?', (code_id,))
    result = cursor.fetchone()
    conn.close()
    if result:
        return result[0]
    else:
        return f"Code with ID {code_id} not found."

def list_all_functions():
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT code_id, code_content FROM codes')
    results = cursor.fetchall()
    conn.close()
    
    functions_list = []
    for code_id, code_content in results:
        try:
            # Parse the code content to extract function name and description
            function_name = "Unknown"
            function_description = "No description available"
            
            # Assuming the code content is a valid Python function definition
            # We can use ast (Abstract Syntax Trees) to parse the code and extract the function name and docstring
            import ast
            parsed_code = ast.parse(code_content)
            for node in ast.walk(parsed_code):
                if isinstance(node, ast.FunctionDef):
                    function_name = node.name
                    if node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Str):
                        function_description = node.body[0].value.s
                    break
            
            functions_list.append({
                "code_id": code_id,
                "function_name": function_name,
                "function_description": function_description
            })
        except Exception as e:
            # If parsing fails, just add the code_id and content without name and description
            functions_list.append({
                "code_id": code_id,
                "function_name": "Unknown",
                "function_description": "Parsing error: " + str(e)
            })
    
    return functions_list

# Available functions for the LLM
available_functions = {
    "create_directory": create_directory,
    "create_file": create_file,
    "update_file": update_file,
    "fetch_code": fetch_code,
    "task_completed": task_completed,
    "store_code": store_code,
    "retrieve_code": retrieve_code,
    "list_all_functions": list_all_functions
}

# Define the tools for function calling
tools = [
    {
        "type": "function",
        "function": {
            "name": "create_directory",
            "description": "Creates a new directory at the specified path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The directory path to create."
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_file",
            "description": "Creates or updates a file at the specified path with the given content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The file path to create or update."
                    },
                    "content": {
                        "type": "string",
                        "description": "The content to write into the file."
                    }
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_file",
            "description": "Updates an existing file at the specified path with the new content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The file path to update."
                    },
                    "content": {
                        "type": "string",
                        "description": "The new content to write into the file."
                    }
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_code",
            "description": "Retrieves the code from the specified file path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "The file path to fetch the code from."
                    }
                },
                "required": ["file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "task_completed",
            "description": "Indicates that the assistant has completed the task.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "store_code",
            "description": "Stores a code or function in the database with a unique identifier generated from the code content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "code_content": {
                        "type": "string",
                        "description": "The content of the code or function to store."
                    }
                },
                "required": ["code_content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "retrieve_code",
            "description": "Retrieves a code or function from the database using its unique identifier.",
            "parameters": {
                "type": "object",
                "properties": {
                    "code_id": {
                        "type": "string",
                        "description": "The unique identifier for the code."
                    }
                },
                "required": ["code_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_all_functions",
            "description": "Retrieves a list of all stored functions in the database with their IDs, names, and descriptions.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
]

def read_instructions():
    instructions_file = os.path.join(BASE_DIR, 'instructions.md')
    with open(instructions_file, 'r') as file:
        return file.read()

def run_main_loop(user_input):
    history_dict = {"iterations": []}

    if not supports_function_calling(MODEL_NAME):
        progress["status"] = "error"
        progress["output"] = "Model does not support function calling."
        progress["completed"] = True
        return "Model does not support function calling."

    max_iterations = progress["max_iterations"]
    iteration = 0

    instructions = read_instructions()

    messages = [
        {
            "role": "system",
            "content": instructions
        },
        {"role": "user", "content": user_input},
        {"role": "system", "content": f"History:\n{json.dumps(history_dict, indent=2)}"}
    ]

    output = ""

    while iteration < max_iterations:
        progress["iteration"] = iteration + 1
        current_iteration = {
            "iteration": iteration + 1,
            "actions": [],
            "llm_responses": [],
            "tool_results": [],
            "errors": []
        }
        history_dict['iterations'].append(current_iteration)

        try:
            response = completion(
                model=MODEL_NAME,
                messages=messages,
                tools=tools,
                tool_choice="auto"
            )

            if not response.choices[0].message:
                error = response.get('error', 'Unknown error')
                current_iteration['errors'].append({'action': 'llm_completion', 'error': error})
                log_to_file(history_dict)
                sleep(5)
                iteration += 1
                continue

            response_message = response.choices[0].message
            content = response_message.content or ""
            current_iteration['llm_responses'].append(content)

            output += f"\n<h2>Iteration {iteration + 1}:</h2>\n"

            tool_calls = response_message.tool_calls

            if tool_calls:
                output += "<strong>Tool Call:</strong>\n<p>" + content + "</p>\n"
                messages.append(response_message)

                for tool_call in tool_calls:
                    function_name = tool_call.function.name
                    function_to_call = available_functions.get(function_name)

                    if not function_to_call:
                        error_message = f"Tool '{function_name}' is not available."
                        current_iteration['errors'].append({
                            'action': f'tool_call_{function_name}',
                            'error': error_message,
                            'traceback': 'No traceback available.'
                        })
                        continue

                    try:
                        function_args = json.loads(tool_call.function.arguments)
                        function_response = function_to_call(**function_args)
                        current_iteration['tool_results'].append({
                            'tool': function_name,
                            'result': function_response
                        })
                        output += f"<strong>Tool Result ({function_name}):</strong>\n<p>{function_response}</p>\n"
                        messages.append(
                            {"tool_call_id": tool_call.id, "role": "tool", "name": function_name, "content": function_response}
                        )

                        if function_name == "task_completed":
                            progress["status"] = "completed"
                            progress["completed"] = True
                            output += "\n<h2>COMPLETE</h2>\n"
                            progress["output"] = output
                            log_to_file(history_dict)
                            return output

                    except Exception as tool_error:
                        error_message = f"Error executing {function_name}: {tool_error}"
                        current_iteration['errors'].append({
                            'action': f'tool_call_{function_name}',
                            'error': error_message,
                            'traceback': traceback.format_exc()
                        })

                second_response = completion(
                    model=MODEL_NAME,
                    messages=messages
                )
                if second_response.choices and second_response.choices[0].message:
                    second_response_message = second_response.choices[0].message
                    content = second_response_message.content or ""
                    current_iteration['llm_responses'].append(content)
                    output += "<strong>LLM Response:</strong>\n<p>" + content + "</p>\n"
                    messages.append(second_response_message)
                else:
                    error = second_response.get('error', 'Unknown error in second LLM response.')
                    current_iteration['errors'].append({'action': 'second_llm_completion', 'error': error})

            else:
                output += "<strong>LLM Response:</strong>\n<p>" + content + "</p>\n"
                messages.append(response_message)

            progress["output"] = output

        except Exception as e:
            error = str(e)
            current_iteration['errors'].append({
                'action': 'main_loop',
                'error': error,
                'traceback': traceback.format_exc()
            })

        iteration += 1
        log_to_file(history_dict)
        sleep(2)

    if iteration >= max_iterations:
        progress["status"] = "completed"

    progress["completed"] = True
    progress["status"] = "completed"

    return output

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8080)
