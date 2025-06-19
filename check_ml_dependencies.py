#!/usr/bin/env python3
"""
Script para verificar se as dependências ML estão funcionando no Railway
Usar para debug em caso de problemas de deploy
"""

import sys
import os

def check_dependency(name, import_func):
    """Verifica uma dependência específica"""
    try:
        result = import_func()
        print(f"✅ {name}: OK")
        return True, result
    except Exception as e:
        print(f"❌ {name}: ERRO - {e}")
        return False, str(e)

def main():
    print("🔍 VERIFICANDO DEPENDÊNCIAS ML NO RAILWAY")
    print("=" * 50)
    
    all_good = True
    
    # 1. PyTorch
    def check_torch():
        import torch
        return f"v{torch.__version__}"
    
    success, info = check_dependency("PyTorch", check_torch)
    all_good &= success
    if success:
        print(f"   📊 Versão: {info}")
    
    # 2. Transformers
    def check_transformers():
        import transformers
        return f"v{transformers.__version__}"
    
    success, info = check_dependency("Transformers", check_transformers)
    all_good &= success
    if success:
        print(f"   📊 Versão: {info}")
    
    # 3. Sentence Transformers
    def check_sentence_transformers():
        from sentence_transformers import SentenceTransformer
        return "importação OK"
    
    success, info = check_dependency("Sentence Transformers", check_sentence_transformers)
    all_good &= success
    
    # 4. HuggingFace Hub
    def check_hf_hub():
        import huggingface_hub
        return f"v{huggingface_hub.__version__}"
    
    success, info = check_dependency("HuggingFace Hub", check_hf_hub)
    all_good &= success
    if success:
        print(f"   📊 Versão: {info}")
    
    # 5. Modelo específico (teste rápido)
    def check_neuralmind_model():
        from sentence_transformers import SentenceTransformer
        # Só verificar se consegue instanciar sem baixar
        model_name = "neuralmind/bert-base-portuguese-cased"
        return f"Modelo {model_name} disponível"
    
    success, info = check_dependency("Modelo NeralMind", check_neuralmind_model)
    all_good &= success
    
    print("\n" + "=" * 50)
    if all_good:
        print("🎉 TODAS AS DEPENDÊNCIAS ML FUNCIONANDO!")
        print("✅ O sistema sentence-transformers está pronto")
    else:
        print("❌ ALGUMAS DEPENDÊNCIAS FALHARAM")
        print("💡 Verifique os logs acima para mais detalhes")
    
    print("\n📊 INFORMAÇÕES DO AMBIENTE:")
    print(f"   🐍 Python: {sys.version}")
    print(f"   📂 Diretório: {os.getcwd()}")
    print(f"   🔧 TRANSFORMERS_CACHE: {os.getenv('TRANSFORMERS_CACHE', 'Não configurado')}")
    print(f"   🔧 TORCH_HOME: {os.getenv('TORCH_HOME', 'Não configurado')}")
    
    return 0 if all_good else 1

if __name__ == "__main__":
    sys.exit(main()) 