# CIMut Agent

Agente local para o sistema CIMut que conecta via WebSocket para executar comandos remotos.

## Pré-requisitos

- Python 3.8 ou superior
- pip (gerenciador de pacotes do Python)

## Instalação

1. Clone ou baixe este repositório
2. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```

## Uso

### Executar o agente diretamente:
```bash
python local_agent.py
```

### Criar executável (opcional):
```bash
python setup.py
```

O executável será criado na pasta `dist/`.

## Funcionalidades

- Conecta automaticamente ao servidor via WebSocket
- Executa comandos de leitura de arquivos
- Executa comandos de modificação de arquivos (com backup automático)
- Reconecta automaticamente em caso de falha
- Coleta informações do sistema (hostname, plataforma, CPU, memória)

## Configuração

Por padrão, o agente conecta em `ws://localhost:8000/api/agent/connect`.
Para alterar, modifique a variável `SERVER_URL` no arquivo `local_agent.py`.
