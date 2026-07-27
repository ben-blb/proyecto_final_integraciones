#!/usr/bin/env bash

set -e

echo "Inicializando base de datos..."
python database.py

echo "Iniciando servidor MCP..."
python mcp_server.py &

echo "Esperando al servidor MCP..."
sleep 3

echo "Iniciando Streamlit..."
exec streamlit run app_streamlit.py \
  --server.address 0.0.0.0 \
  --server.port "${PORT:-8501}" \
  --server.headless true