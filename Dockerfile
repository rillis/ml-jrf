# Use uma imagem base do Python
FROM python:3.11-slim

# Defina diretório de trabalho no container
WORKDIR /home/rillis/docker/ml-jrf-new

# Copie apenas os arquivos essenciais
COPY requirements.txt ./

# Instale as dependências
RUN pip install --no-cache-dir -r requirements.txt

# Copie todo o conteúdo da pasta ml para dentro do container
COPY . .

# Exponha a porta
EXPOSE 80

ENV PYTHONUNBUFFERED=1

# Comando para executar o script
CMD ["python", "main.py"]
