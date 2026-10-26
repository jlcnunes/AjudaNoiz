# Imagem base ultra leve do Python baseada no Debian
FROM python:3.14-slim

# Evita que o Python escreva arquivos .pyc no disco
ENV PYTHONDONTWRITEBYTECODE=1

# Garante que os logs do console sejam exibidos imediatamente
ENV PYTHONUNBUFFERERED=1

# Define o diretório de trabalho dentro do container
WORKDIR /app

# Instala dependências do sistema necessárias para compilar pacotes (como psycopg2 para o PostgreSQL)
RUN apt-get update && apt-get install -y --no-install-recommends \
gcc \
libpq-dev \
&& rm -rf /var/lib/apt/lists/*

#Copia apenas o arquivo de requerimentos primeiro (melhora o cache de camadas do Docker)
COPY requirements.txt /app/

# Instala as dependências Python listadas no requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copia o restante do código do projeto (HTML, JS, CSS, subpastas)
COPY . /app/

# Expõe a porta padrão que o Flask vai rodar
EXPOSE 5000

# Comando para rodar a aplicação em modo de desenvolvimento
CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"]
