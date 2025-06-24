# Patch para atualizar o threshold do Ollama
import os

# Buscar no arquivo ollama_match_validator.py e atualizar
with open('src/matching/ollama_match_validator.py', 'r') as f:
    content = f.read()

# Substituir o threshold
old_line = '        self.HIGH_SCORE_THRESHOLD = 0.50  # Valida matches a partir de 50%'
new_line = '        self.HIGH_SCORE_THRESHOLD = float(os.getenv("HIGH_SCORE_THRESHOLD", "0.70"))  # Valida matches a partir de 70%'

content = content.replace(old_line, new_line)

# Salvar arquivo atualizado
with open('src/matching/ollama_match_validator.py', 'w') as f:
    f.write(content)

print("✅ Threshold do Ollama atualizado para usar variável de ambiente")
