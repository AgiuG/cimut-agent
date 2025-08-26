import asyncio
import websockets
import json
import uuid
import platform
import psutil
import os
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