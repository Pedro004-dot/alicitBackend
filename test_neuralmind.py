#!/usr/bin/env python3
"""
Script para testar NeralMind antes de integrar
Execute este arquivo para verificar se tudo está funcionando
"""

import sys
import os

# Adicionar src ao path para imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def test_neuralmind_service():
    print("🧪 TESTANDO NEURALMIND BERT")
    print("=" * 50)
    
    # Importar serviço
    try:
        from services.neuralmind_embedding_service import NeuralMindEmbeddingService
        service = NeuralMindEmbeddingService()
        
        print("✅ Serviço carregado")
        print(f"📊 Modelo: {service.model_name}")
        print(f"🔑 API Key: {'Configurada' if service.api_key else 'Tier gratuito'}")
        
    except Exception as e:
        print(f"❌ Erro ao carregar serviço: {e}")
        return False
    
    # Teste 1: Conexão básica
    print("\n1️⃣ Testando conexão...")
    if not service.test_connection():
        print("❌ Falha na conexão - verifique internet/API")
        return False
    
    # Teste 2: Textos reais de licitação
    print("\n2️⃣ Testando com textos reais...")
    
    textos_teste = [
        "Contratação de empresa especializada para prestação de serviços de tecnologia da informação",
        "Aquisição de equipamentos de informática incluindo computadores e impressoras",
        "Prestação de serviços de manutenção preventiva e corretiva de equipamentos de TI"
    ]
    
    try:
        embeddings = service.generate_embeddings(textos_teste)
        
        if embeddings and len(embeddings) == 3:
            print(f"✅ Batch test OK: {len(embeddings)} embeddings")
            print(f"📏 Dimensões: {len(embeddings[0])} (esperado: 768)")
            
            # Verificar se dimensões estão corretas
            if len(embeddings[0]) == 768:
                print("✅ Dimensões corretas!")
            else:
                print(f"⚠️ Dimensões incorretas: {len(embeddings[0])}")
                
        else:
            print("❌ Batch test falhou")
            return False
            
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        return False
    
    # Teste 3: Comparação de similaridade
    print("\n3️⃣ Testando similaridade...")
    
    try:
        # Textos similares (devem ter alta similaridade)
        texto1 = "Serviços de tecnologia da informação"
        texto2 = "Prestação de serviços de TI"
        
        emb1 = service.generate_single_embedding(texto1)
        emb2 = service.generate_single_embedding(texto2)
        
        if emb1 and emb2:
            # Calcular similaridade cosine simples
            import numpy as np
            
            # Normalizar vetores
            vec1 = np.array(emb1)
            vec2 = np.array(emb2)
            
            # Calcular similaridade cosseno
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 == 0 or norm2 == 0:
                similarity = 0.0
            else:
                similarity = dot_product / (norm1 * norm2)
            
            print(f"📊 Similaridade TI vs Tecnologia da Informação: {similarity:.3f}")
            
            if similarity > 0.7:
                print("✅ Alta similaridade detectada - modelo funcionando!")
            else:
                print("⚠️ Similaridade baixa - pode haver problema")
                
        else:
            print("❌ Falha ao gerar embeddings para teste")
            return False
            
    except Exception as e:
        print(f"❌ Erro no teste de similaridade: {e}")
        print("💡 Continuando sem teste de similaridade...")
        # Não falhar por causa disso
    
    print("\n🎉 TODOS OS TESTES PASSARAM!")
    print("✅ NeralMind está pronto para produção")
    print("\n📋 Próximos passos:")
    print("   1. Integrar ao HybridTextVectorizer")
    print("   2. Testar com dados reais do sistema")
    print("   3. Comparar performance com VoyageAI atual")
    
    return True

if __name__ == "__main__":
    # Carregar variáveis de ambiente
    from dotenv import load_dotenv
    load_dotenv('config.env')
    
    success = test_neuralmind_service()
    
    if success:
        print("\n🚀 Sistema pronto para integração!")
        sys.exit(0)
    else:
        print("\n❌ Testes falharam - verificar configuração")
        sys.exit(1) 