import asyncio
import websockets
import json
import uuid
import platform
import psutil
import os
import re
from datetime import datetime

class LocalAgent: 
    def __init__(self, server_url: str, agent_name: str = None):
        self.server_url = server_url
        self.agent_id = agent_name or f"agent_{platform.node()}_{uuid.uuid4().hex[:8]}"
        self.websocket = None

    async def connect(self):
        try:
            self.websocket = await websockets.connect(self.server_url)

            registration = {
                'agent_id': self.agent_id,
                'hostname': platform.node(),
                'platform': platform.platform(),
                'cpu_count': psutil.cpu_count(),
                'memory_total': psutil.virtual_memory().total,
                'version': '1.0.0'            
            }

            await self.websocket.send(json.dumps(registration))
            response = await self.websocket.recv()
            print(f"Registration response: {response}")

            await self.listen_for_commands()

        except Exception as e:
            print(f"Connection error: {e}")

    async def listen_for_commands(self):
        try:
            async for message in self.websocket:
                try:
                    command = json.loads(message)
                    response = await self.execute_command(command)
                    await self.websocket.send(json.dumps(response))
                except Exception as e:
                    error_response = {
                        'command_id': command.get('command_id'),
                        'success': False,
                        'error': str(e)
                    }
                    await self.websocket.send(json.dumps(error_response))
        except websockets.exceptions.ConnectionClosed:
            print("Connection closed by server")
    
    async def execute_command(self, command: dict) -> dict:
        command_id = command.get('command_id')
        action = command.get('action')

        try: 
            if action == 'read_file':
                return await self.read_file_line(
                    command['file_path'],
                    command['line_number'],
                    command_id
                )
            
            elif action == 'read_full_file':
                return await self.read_full_file(
                    command['file_path'],
                    command.get('functions', []),
                    command_id
                )
            
            elif action == 'modify_file':
                return await self.modify_file_line(
                    command['file_path'],
                    command['line_number'],
                    command['new_content'],
                    command_id
                )

            elif action == 'ping':
                return {
                    'command_id': command_id,
                    'success': True,
                    'data': 'pong',
                    'timestamp': datetime.now().isoformat()
                }
            
            else: 
                return {
                    'command_id': command_id,
                    'success': False,
                    'error': f"Unknown action: {action}"
                }
            
        except Exception as e:
            return {
                'command_id': command_id,
                'success': False,
                'error': str(e)
            }
    
    async def read_file_line(self, file_path: str, line_number: int, command_id: str) -> dict:
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                lines = file.readlines()

            if line_number <= 0 or line_number > len(lines):
                raise ValueError(f"Line number {line_number} out of range")

            line_content = lines[line_number - 1].strip('\n')

            return {
                'command_id': command_id,
                'success': True,
                'data': {
                    'file_path': file_path,
                    'line_number': line_number,
                    'line_content': line_content,
                    'total_lines': len(lines)
                }
            }
        
        except FileNotFoundError:
            raise Exception(f"File not found: {file_path}")
        except Exception as e:
            raise Exception(f"Error reading file: {str(e)}")
    
    async def read_full_file(self, file_path: str, functions: list, command_id: str) -> dict:
        try:
            # Check if file exists and get file stats
            file_stats = os.stat(file_path)
            file_size = file_stats.st_size
            
            # Limit file size to avoid timeouts (5MB max)
            if file_size > 5 * 1024 * 1024:
                raise Exception(f"File too large ({file_size} bytes). Maximum 5MB allowed.")
            
            with open(file_path, 'r', encoding='utf-8') as file:
                all_lines = file.readlines()
            
            # Limit number of lines to process
            if len(all_lines) > 20000:
                raise Exception(f"File too many lines ({len(all_lines)}). Maximum 20,000 lines allowed.")
            
            # If no specific functions requested, return entire file
            if not functions:
                # Limit return size for entire file
                if len(all_lines) > 2000:
                    content = ''.join(all_lines[:2000]) + '\n... [File truncated - too large to display entirely]'
                    lines = [line.rstrip('\n') for line in all_lines[:2000]]
                else:
                    content = ''.join(all_lines)
                    lines = [line.rstrip('\n') for line in all_lines]
                
                return {
                    'command_id': command_id,
                    'success': True,
                    'data': {
                        'file_path': file_path,
                        'content': content,
                        'lines': [{'content': line, 'line_number': i + 1} for i, line in enumerate(lines)],
                        'total_lines': len(lines),
                        'file_size_bytes': file_size,
                        'encoding': 'utf-8',
                        'timestamp': datetime.now().isoformat(),
                        'extracted_functions': []
                    }
                }
            
            # Limit number of functions to extract
            if len(functions) > 10:
                functions = functions[:10]  # Only process first 10 functions
            
            # Extract specific functions
            extracted_lines = []
            extracted_functions = []
            
            for function_name in functions:
                function_lines = self._extract_function(all_lines, function_name)
                if function_lines:
                    extracted_functions.append(function_name)
                    extracted_lines.extend(function_lines)
                
                # Limit total extracted lines
                if len(extracted_lines) > 1000:
                    break
            
            # Sort lines by line number to maintain order
            extracted_lines.sort(key=lambda x: x['line_number'])
            
            # Build content string and organize lines
            content_parts = []
            lines_data = []
            
            for line_info in extracted_lines:
                line_content = line_info['content'].rstrip('\n')
                content_parts.append(line_content)
                lines_data.append({
                    'content': line_content,
                    'line_number': line_info['line_number']
                })
            
            content = '\n'.join(content_parts)
            
            return {
                'command_id': command_id,
                'success': True,
                'data': {
                    'file_path': file_path,
                    'content': content,
                    'lines': lines_data,
                    'total_lines': len(lines_data),
                    'file_size_bytes': file_size,
                    'encoding': 'utf-8',
                    'timestamp': datetime.now().isoformat(),
                    'requested_functions': functions,
                    'extracted_functions': extracted_functions,
                    'functions_not_found': [f for f in functions if f not in extracted_functions]
                }
            }
        
        except FileNotFoundError:
            raise Exception(f"File not found: {file_path}")
        except UnicodeDecodeError:
            # Try with latin-1 encoding (simplified fallback)
            try:
                with open(file_path, 'r', encoding='latin-1') as file:
                    all_lines = file.readlines()[:2000]  # Limit lines for latin-1 too
                
                content = ''.join(all_lines)
                lines = [line.rstrip('\n') for line in all_lines]
                
                return {
                    'command_id': command_id,
                    'success': True,
                    'data': {
                        'file_path': file_path,
                        'content': content,
                        'lines': [{'content': line, 'line_number': i + 1} for i, line in enumerate(lines)],
                        'total_lines': len(lines),
                        'file_size_bytes': file_size,
                        'encoding': 'latin-1',
                        'timestamp': datetime.now().isoformat(),
                        'extracted_functions': [],
                        'note': 'Fallback encoding used - function extraction disabled for safety'
                    }
                }
            except Exception as e:
                raise Exception(f"Error reading file with different encodings: {str(e)}")
        except Exception as e:
            raise Exception(f"Error reading functions from file: {str(e)}")
    
    def _extract_function(self, all_lines: list, function_name: str) -> list:
        """
        Extract a specific function from file lines.
        Fast, simple extraction focusing on Python primarily.
        """
        extracted_lines = []
        function_found = False
        indent_level = 0
        
        # Limit search to avoid timeouts
        max_lines = min(len(all_lines), 10000)
        
        for i in range(max_lines):
            line = all_lines[i]
            line_content = line.rstrip('\n')
            
            # Simple function detection - focus on most common patterns
            if not function_found:
                # Python function
                if f'def {function_name}(' in line_content or f'async def {function_name}(' in line_content:
                    function_found = True
                    indent_level = len(line_content) - len(line_content.lstrip())
                    extracted_lines.append({
                        'content': line,
                        'line_number': i + 1
                    })
                    continue
                
                # JavaScript/TypeScript function
                if (f'function {function_name}(' in line_content or 
                    f'const {function_name} =' in line_content or
                    f'let {function_name} =' in line_content):
                    function_found = True
                    extracted_lines.append({
                        'content': line,
                        'line_number': i + 1
                    })
                    # For JS, look for closing brace
                    brace_count = line_content.count('{') - line_content.count('}')
                    for j in range(i + 1, min(i + 200, max_lines)):  # Limited search
                        next_line = all_lines[j]
                        extracted_lines.append({
                            'content': next_line,
                            'line_number': j + 1
                        })
                        brace_count += next_line.count('{') - next_line.count('}')
                        if brace_count <= 0:
                            break
                    break
            else:
                # Python function continuation
                current_indent = len(line_content) - len(line_content.lstrip()) if line_content.strip() else indent_level + 1
                
                # Function ended when indent returns to original level or less
                if line_content.strip() and current_indent <= indent_level:
                    break
                    
                extracted_lines.append({
                    'content': line,
                    'line_number': i + 1
                })
                
                # Safety check
                if len(extracted_lines) > 200:  # Limit function size
                    break
        
        return extracted_lines if function_found else []
        
    async def modify_file_line(self, file_path: str, line_number: int, new_content: str, command_id: str) -> dict:
        try:
            backup_path = f"{file_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            with open(file_path, 'r', encoding='utf-8') as file:
                lines = file.readlines()

            if line_number <= 0 or line_number > len(lines):
                raise ValueError(f"Line number {line_number} out of range")

            old_content = lines[line_number - 1].strip('\n')

            with open(backup_path, 'w', encoding='utf-8') as backup:
                backup.writelines(lines)

            lines[line_number - 1] = new_content + '\n'

            with open(file_path, 'w', encoding='utf-8') as file:
                file.writelines(lines)
            
            return {
                'command_id': command_id,
                'success': True,
                'data': {
                    'file_path': file_path,
                    'line_number': line_number,
                    'old_content': old_content,
                    'new_content': new_content,
                    'backup_path': backup_path,
                    'timestamp': datetime.now().isoformat()
                }
            }

        except FileNotFoundError:
            raise Exception(f"File not found: {file_path}")
        except Exception as e:
            raise Exception(f"Error modifying file: {str(e)}")
        
async def main():
    SERVER_URL = "wss://cimut-api.onrender.com/api/agent/connect"
    AGENT_NAME = "local_dev_agent"

    agent = LocalAgent(SERVER_URL, AGENT_NAME)

    print(f"Starting agent {agent.agent_id}...")
    print(f"Connecting to {SERVER_URL}")

    while True:
        try:
            await agent.connect()
        except Exception as e:
            print(f"Connection failed: {e}")
            print("Retrying in 5 seconds...")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())
