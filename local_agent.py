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
            
            with open(file_path, 'r', encoding='utf-8') as file:
                all_lines = file.readlines()
            
            # If no specific functions requested, return entire file
            if not functions:
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
            
            # Extract specific functions
            extracted_lines = []
            extracted_functions = []
            
            for function_name in functions:
                function_lines = self._extract_function(all_lines, function_name)
                if function_lines:
                    extracted_functions.append(function_name)
                    extracted_lines.extend(function_lines)
            
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
            # Try with different encoding if UTF-8 fails
            try:
                with open(file_path, 'r', encoding='latin-1') as file:
                    all_lines = file.readlines()
                
                # Apply same logic with different encoding
                if not functions:
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
                            'extracted_functions': []
                        }
                    }
                
                # Extract specific functions with latin-1 encoding
                extracted_lines = []
                extracted_functions = []
                
                for function_name in functions:
                    function_lines = self._extract_function(all_lines, function_name)
                    if function_lines:
                        extracted_functions.append(function_name)
                        extracted_lines.extend(function_lines)
                
                extracted_lines.sort(key=lambda x: x['line_number'])
                
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
                        'encoding': 'latin-1',
                        'timestamp': datetime.now().isoformat(),
                        'requested_functions': functions,
                        'extracted_functions': extracted_functions,
                        'functions_not_found': [f for f in functions if f not in extracted_functions]
                    }
                }
            except Exception as e:
                raise Exception(f"Error reading file with different encodings: {str(e)}")
        except Exception as e:
            raise Exception(f"Error reading functions from file: {str(e)}")
    
    def _extract_function(self, all_lines: list, function_name: str) -> list:
        """
        Extract a specific function from file lines.
        Supports Python, JavaScript, Java, C#, etc.
        """
        extracted_lines = []
        function_found = False
        function_start_line = -1
        indent_level = 0
        brace_count = 0
        uses_braces = False
        
        # Common function patterns for different languages
        patterns = [
            # Python: def function_name( or async def function_name(
            rf'^\s*(async\s+)?def\s+{function_name}\s*\(',
            # JavaScript/TypeScript: function function_name( or const function_name = 
            rf'^\s*(async\s+)?(function\s+{function_name}\s*\(|const\s+{function_name}\s*=|let\s+{function_name}\s*=|var\s+{function_name}\s*=)',
            # Java/C#: public/private/protected ... function_name(
            rf'^\s*(public|private|protected|static|\w+)*\s+\w*\s*{function_name}\s*\(',
            # C/C++: return_type function_name(
            rf'^\s*\w+\s+{function_name}\s*\('
        ]
        
        for i, line in enumerate(all_lines):
            line_content = line.rstrip('\n')
            
            # Check if this line matches any function pattern
            if not function_found:
                for pattern in patterns:
                    if re.search(pattern, line_content):
                        function_found = True
                        function_start_line = i
                        # Determine the base indentation level
                        indent_level = len(line_content) - len(line_content.lstrip())
                        # Check if this language uses braces
                        uses_braces = '{' in line_content or '}' in line_content
                        brace_count = line_content.count('{') - line_content.count('}')
                        extracted_lines.append({
                            'content': line,
                            'line_number': i + 1
                        })
                        break
            else:
                # We're inside the function, continue extracting
                extracted_lines.append({
                    'content': line,
                    'line_number': i + 1
                })
                
                # Check for braces if not detected yet
                if not uses_braces and ('{' in line_content or '}' in line_content):
                    uses_braces = True
                
                # Update brace count for languages that use braces
                if uses_braces:
                    brace_count += line_content.count('{') - line_content.count('}')
                
                # Determine if function has ended
                current_indent = len(line_content) - len(line_content.lstrip()) if line_content.strip() else indent_level + 1
                
                if uses_braces:
                    # Brace-based languages: function ends when braces are balanced
                    if brace_count <= 0 and i > function_start_line:
                        break
                else:
                    # Python-style: function ends when indentation returns to original level or less
                    if line_content.strip() and current_indent <= indent_level and i > function_start_line:
                        # Remove the last line as it's not part of the function
                        extracted_lines.pop()
                        break
                
                # Safety check: if we've gone too far without finding the end, stop
                if i - function_start_line > 500:  # Reduced from 1000 for faster timeout
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
